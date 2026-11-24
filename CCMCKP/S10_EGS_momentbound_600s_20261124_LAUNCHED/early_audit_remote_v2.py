"""Independent record-only LSS audit; no solver or probability evaluator calls."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,math,pickle,statistics
import numpy as np
from fractions import Fraction
def next_float(x,t):return float(np.nextafter(x,t))
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_momentbound_600s_20261124'
assert Path.cwd().resolve()==B.resolve()
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=read(H/'PROTOCOL.json');completed=read(H/'STATE.json')
assert completed['phase']=='running' and not (H/'EARLY_INDEPENDENT_RECORD_AUDIT_V2.json').exists()
global_errors=[]
if sha(H/'PROTOCOL.json')!=read(H/'LAUNCH.json')['protocol_sha256']:global_errors.append('protocol_sha')
for name,digest in P['source_and_binary_pins'].items():
    if sha(H/name)!=digest:global_errors.append('source:'+name)
for name,digest in P['input_pins'].items():
    if sha(B/name)!=digest:global_errors.append('input:'+name)
data={}
for c in P['cases']:
    directory=B/'benchmark'/c['instance'];g=pickle.loads((directory/'node_to_factor.pkl').read_bytes())
    if isinstance(g,dict):g=[g[k] for k in sorted(g)]
    costs=[float(v) for line in (directory/'cost.txt').read_text().splitlines() for v in line.split('#',1)[0].split()]
    mean=[];variance=[]
    for j in range(len(costs)):
        sample=np.loadtxt(str(directory/(str(j)+'_sample.txt')))
        mean.append(float(np.mean(sample)));variance.append(float(np.var(sample)))
    data[c['index']]={'groups':g,'costs':costs,'mean':mean,'variance':variance}
def selection_ok(d,s):return len(s)==len(d['groups']) and all(j in g for j,g in zip(s,d['groups']))
prior=read(H/'EARLY_INDEPENDENT_RECORD_AUDIT.json');redo={r['identity'] for r in prior['runs'] if not r['valid']}
outcomes=[read(p) for p in (H/'outcomes').glob('*.json') if p.stem in redo]
assert len(outcomes)==len(redo)==30,'only_affected_records_rechecked'
identities={(a['name'],c['index'],rep) for a in P['arms'] for c in P['cases'] for rep in range(1,31)}
if len({o['identity'] for o in outcomes})!=len(outcomes) or not {(o['arm'],o['case_index'],o['rep']) for o in outcomes}.issubset(identities):global_errors.append('early_identity_or_duplicate')
rows=[]
for o in sorted(outcomes,key=lambda x:(x['case_index'],x['arm'],x['rep'])):
    r={k:o.get(k) for k in ['identity','case_index','instance','capacity','arm','rep','seed','rc','termination_reason','process_wall_seconds','peak_rss_bytes']}
    r.update({'valid':False,'cost':None,'reported_output_cost_diagnostic':None,'LSS_probability':None,'search_seconds':None,
        'worker_wall_seconds':None,'selection':None,'final_LSS_rejected_candidates':None,'LSS_evaluations':None,
        'initialization_cost':None,'raw_final_cost':None,'ellipsoid_search_improvements':None,'errors':[]})
    root=H/'runs'/o['identity'];d=data[o['case_index']]
    try:
        assert o['seed']==960000+o['rep'],'seed_identity'
        for name,item in o['output_files'].items():
            f=root/name;assert f.stat().st_size==item['bytes'] and sha(f)==item['sha256'],'output_sha:'+name
        if (root/'S10_search.run.json').exists():r['search_seconds']=read(root/'S10_search.run.json')['elapsed']
        if o['rc']!=0:
            r['errors'].append('process_exit:'+str(o['rc']))
            if (root/'FAILED.json').exists():r['failure_detail']=read(root/'FAILED.json')
        else:
            x=read(root/'RESULT.json');meta=read(root/'S10_search.run.json');raw=read(root/'S10_search.json');trace=read(root/'ORIGINAL_LSS_DECISION_TRACE.json')
            r.update({'reported_output_cost_diagnostic':x['cost'],'LSS_probability':x['original_LSS_confidence'],
                'worker_wall_seconds':x['wall_seconds_including_LSS'],'selection':x['selection'],'LSS_evaluations':x['evaluation_times']})
            assert x['status']==raw['status']=='completed' and x['schema']=='S10_LSS_full_sample_total600_v3','status_or_schema'
            assert x['instance']==raw['instance']==o['instance'] and x['capacity']==raw['capacity']==o['capacity'],'problem_identity'
            assert x['search_seed']==raw['seed']==meta['seed']==o['seed'] and x['rep']==o['rep'],'seed_or_rep'
            assert meta['within_budget'] and meta['elapsed']<600 and meta['budget']==600,'search_clock'
            complete=read(root/'COMPLETION.json')
            assert o['wall_clock_source']=='dedicated_wait_thread_from_before_Popen','wall_clock_source'
            assert 0<o['process_wall_seconds']<=600,'actual_process_exceeded_600'
            assert complete['all_output_files_fsynced'] and complete['start_includes_process_launch'],'full_pipeline_save'
            assert complete['clock_policy']==x['clock_policy']=='launch_to_exit_total_wall','clock_policy'
            assert 0<complete['elapsed_before_completion_save']<=o['process_wall_seconds'],'completion_clock'
            assert x['total_budget_seconds']==complete['budget']==600,'total_budget'
            assert meta['elapsed']<=x['wall_seconds_including_LSS']<=complete['elapsed_before_completion_save'],'clock_order'
            assert x['LSS_finalization_seconds']>=0,'LSS_phase_clock'
            r['LSS_finalization_seconds']=x['LSS_finalization_seconds']
            r['completion_saved_seconds']=complete['elapsed_before_completion_save']
            r['LSS_incomplete_evaluations']=sum(e['stage']=='LSS_incomplete_evaluation' for e in trace)
            r['raw_best_first_found_seconds']=raw['selected']['found_seconds']
            assert not raw['config']['validation_outside_search_clock'],'outside_clock'
            assert meta['startup_until_search_seconds']>=meta['load_seconds']>0,'startup_clock'
            for event in trace:
                if 'evaluation' in event:
                    assert 0<=event['elapsed_start']<=event['elapsed_end']<=590.1,'LSS_evaluation_clock'
                if event['stage']=='LSS_incomplete_evaluation':
                    assert event['no_probability_returned'] and 'probability' not in event,'partial_probability_used'
            proof_map={tuple(p['selection']):p for p in raw['native_infeasible_proofs']}
            assert len(proof_map)==len(raw['native_infeasible_proofs']),'duplicate_native_proof'
            for sk,proof in proof_map.items():
                den=int(proof['denominator']);lo=int(proof['lower_numerator']);hi=int(proof['upper_numerator'])
                assert selection_ok(d,list(sk)) and den==500**len(d['groups']),'native_proof_identity'
                assert 0<=lo<=hi<=den and hi*100<99*den,'native_upper_not_infeasible'
                assert proof['infeasible'] and not proof['accepted'] and proof['all_original_samples'] and proof['strict_event']=='sum<T','native_proof_contract'
            r['native_infeasible_proofs']=len(proof_map)
            r['dominance_cuts']=len(raw['dominance_cuts'])
            r['nontrivial_dominance_cuts']=0
            if o['arm']=='EGS_MB_TOTAL600':
                master=next(e for e in raw['ellipsoid_history'] if e['event']=='dominance_master_initialized')
                assert not master['risk_objective'] and master['cost_primary_objective'] and master['objective_order']=='cost_then_ellipsoid_risk' and master['native_SOC'] and not master['hard_risk_capacity_constraint'],'candidate_model'
                assert master['risk_cap'] is None and master['LSS_is_only_final_acceptance'],'hard_risk_gate'
                s0=master['self_generated_start'];assert selection_ok(d,s0),'own_start'
                spec=master['necessary_mean_bound'];assert spec['method']=='Cantelli_lower_tail_necessary_global_variance_envelope' and spec['probability_target']=='99/100','moment_method'
                assert not spec['adds_sufficient_ellipsoid_final_constraint'],'changed_final_constraint'
                if 'moment_expected' not in d:
                    mu=[];vv=[]
                    for j in range(len(d['costs'])):
                        text=(B/'benchmark'/o['instance']/(str(j)+'_sample.txt')).read_text()
                        values=[Fraction(v) for line in text.splitlines() for v in line.split('#',1)[0].split()]
                        m=sum(values,Fraction(0))/len(values);v=sum((x*x for x in values),Fraction(0))/len(values)-m*m
                        assert v>=0,'negative_rational_variance';mu.append(m);vv.append(v)
                    group_v=[max(vv[j] for j in g) for g in d['groups']];vmax=sum(group_v,Fraction(0))
                    coeff=[]
                    for m in mu:
                        z=float(m)
                        if Fraction.from_float(z)>m:z=next_float(z,-math.inf)
                        assert Fraction.from_float(z)<=m;coeff.append(z)
                    d['moment_expected']={'means':mu,'variances':vv,'group_v':group_v,'vmax':vmax,'coeff':coeff}
                e=d['moment_expected'];assert [Fraction(x) for x in spec['exact_item_means']]==e['means'],'exact_means'
                assert [Fraction(x) for x in spec['exact_item_variances_ddof0']]==e['variances'],'exact_variances'
                assert [Fraction(x) for x in spec['exact_group_max_variances']]==e['group_v'] and Fraction(spec['exact_Vmax'])==e['vmax'],'Vmax_envelope'
                assert spec['mean_coefficients_rounded_down']==e['coeff'],'mean_coefficient_rounding'
                cap=Fraction(str(o['capacity']));assert Fraction(spec['capacity_exact'])==cap,'moment_capacity'
                sqrt_upper=spec['sqrt_Vmax_over99_rounded_up'];rootq=Fraction.from_float(sqrt_upper)
                assert sqrt_upper>=0 and rootq*rootq>=e['vmax']/99,'sqrt_rounding_upper'
                if sqrt_upper>0:assert Fraction.from_float(next_float(sqrt_upper,-math.inf))**2<e['vmax']/99,'unexplained_extra_sqrt_relaxation'
                rhs=spec['rhs_rounded_up'];target=cap+rootq;expected_rhs=float(target)
                if Fraction.from_float(expected_rhs)<target:expected_rhs=next_float(expected_rhs,math.inf)
                assert rhs==expected_rhs and Fraction.from_float(rhs)>=target,'rhs_rounding_upper'
                assert spec['registered_proposal_row_tolerance']==1e-6,'moment_row_tolerance'
                d['moment_rhs']=Fraction.from_float(rhs)

                init0=next(q for q in meta['phase_records'] if q['phase']=='initialization')
                assert abs(sum(d['costs'][j] for j in s0)-init0['best_after'])<1e-8,'initial_start_cost'
                if 'D_table' not in d:
                    orders=[]
                    for j in range(len(d['costs'])):
                        text=(B/'benchmark'/o['instance']/(str(j)+'_sample.txt')).read_text()
                        values=[Fraction(v) for line in text.splitlines() for v in line.split('#',1)[0].split()]
                        assert len(values)==500,'sample_count'
                        orders.append(sorted(values))
                    table={}
                    for group in d['groups']:
                        for ref in group:
                            table[ref]=[j for j in group if all(a>=b for a,b in zip(orders[j],orders[ref]))]
                    d['D_table']=table
                seen_cuts=set()
                positives=[c['selection'] for c in raw['candidate_shortlist']]
                for cut in raw['dominance_cuts']:
                    s=cut['selection'];key=tuple(s);assert key in proof_map and cut['certificate']==proof_map[key],'cut_native_proof_source'
                    expected=[d['D_table'][j] for j in s]
                    assert cut['worse_sets']==expected and cut['rhs']==len(d['groups'])-1,'cut_coefficients_or_rhs'
                    assert cut['proof_type']=='exact_empirical_FOSD_quantile_coupling','cut_proof_type'
                    signature=tuple(j for group in expected for j in group)
                    assert signature not in seen_cuts,'duplicate_cut';seen_cuts.add(signature)
                    assert 0<=cut['elapsed']<=meta['elapsed'],'cut_clock'
                    sets=[set(g) for g in expected]
                    assert all(any(j not in group for j,group in zip(safe,sets)) for safe in positives),'cut_covers_known_CDF_accepted_vector'
                    if math.prod(len(g) for g in expected)>1:r['nontrivial_dominance_cuts']+=1
                queried_selections=set()
                for q in raw['ellipsoid_history']:
                    if q.get('event')=='candidate_query' and q.get('has_candidate'):
                        sq=q['selection'];assert selection_ok(d,sq),'candidate_selection'
                        assert tuple(sq) not in queried_selections,'repeated_excluded_candidate'
                        queried_selections.add(tuple(sq))
                        for cut in raw['dominance_cuts']:
                            if cut['elapsed']<=q['elapsed']:
                                assert sum(j in group for j,group in zip(sq,cut['worse_sets']))<=len(d['groups'])-1,'candidate_violates_active_dominance_cut'

                        nq=math.sqrt(sum(d['variance'][j] for j in sq));rq=sum(d['mean'][j] for j in sq)+2.4*nq
                        assert abs(nq-q['norm'])<1e-7 and q['epigraph']+1e-6>=nq,'SOC_epigraph'
                        assert abs(rq-q['risk'])<1e-7,'SOC_actual_risk'
                        assert abs(sum(d['costs'][j] for j in sq)-q['cost'])<1e-8 and q['cost']<=q['candidate_cost_bound']+1e-6,'SOC_proposal_cost'
                        assert q['cone_converged'],'unconverged_SOC_proposal'
                        w=q['canonical_soc_witness'];assert w['exact_canonical_SOC_feasible'],'canonical_SOC_flag'
                        sd=w['selected_sd_coefficients'];assert len(sd)==len(sq),'canonical_sd_length'
                        assert all(abs(a-math.sqrt(d['variance'][j]))<1e-12 for a,j in zip(sd,sq)),'canonical_sd_coefficient'
                        v=sum((Fraction.from_float(a)**2 for a in sd),Fraction(0));ct=Fraction.from_float(w['canonical_t'])
                        assert Fraction(w['sum_squared_sd_binary_rational'])==v,'canonical_exact_squared_sum'
                        assert ct*ct>=v and Fraction(w['squared_slack_binary_rational'])==ct*ct-v,'canonical_exact_SOC_feasibility'
                        assert q['epigraph']==w['canonical_t']==q['norm'] and w['canonical_t']>=0,'canonical_t_used'
                        guard=w['discrete_proposal_guard']
                        assert guard['valid'] and guard['integral'] and guard['one_per_group'],'discrete_guard'
                        assert not guard['excluded_hit'] and guard['violating_dominance_rows']==0,'discrete_exclusions'
                        assert guard['selection']==sq and guard['cost_within_original_1e6_tolerance'] and guard['cost_bound']==q['candidate_cost_bound'],'discrete_cost_guard'
                        assert Fraction(guard['exact_cost_binary_rational'])==sum((Fraction.from_float(d['costs'][j]) for j in sq),Fraction(0)),'exact_binary_cost'
                        legacy=w['raw_solver_epigraph']+1e-6<math.hypot(*sd)
                        assert w['legacy_epigraph_guard_would_reject']==legacy,'legacy_guard_metadata'
                        assert not q['proxy_optimal'] and not q['objective_bound_available'] and q['proxy_objective_bound'] is None,'unavailable_bound_claim'
                        assert w['objective_order']=='cost_then_ellipsoid_risk' and w['higher_priority_objective_abs_tol']==w['higher_priority_objective_rel_tol']==0,'objective_hierarchy'
                        mc=w['necessary_mean_bound_check'];lhs=sum((Fraction.from_float(d['moment_expected']['coeff'][j]) for j in sq),Fraction(0));right=d['moment_rhs']
                        assert Fraction(mc['lhs_exact_binary_rational'])==lhs and Fraction(mc['rhs_exact_binary_rational'])==right and Fraction(mc['slack_exact_binary_rational'])==right-lhs,'moment_query_exact_row'
                        assert mc['row_tolerance']==1e-6 and mc['within_registered_proposal_row_tolerance'] and lhs<=right+Fraction.from_float(1e-6),'moment_query_row_tolerance'
                        assert mc['strictly_satisfies_row']==(lhs<=right),'moment_query_strict_flag'
                        if q.get('raw_certificate_accepted'):assert lhs<=right,'CDF_accepted_but_violates_necessary_condition'


            else:assert not raw['dominance_cuts'],'baseline_used_candidate_cut'
            assert meta['local_phases']=='none' and meta['backend']=='gurobi','backend'
            assert x['acceptance_evaluator']=='LSS' and x['acceptance_threshold']==.99 and x['final_lss_enforced'],'LSS_contract'
            assert not x['real_probability_reporting'] and 'recorded_real_probability' not in x,'unexpected_realP'
            assert x['lss_sample_index_min']==0 and x['lss_sample_index_max']==499,'sampling_endpoint'
            assert raw['config']['sampling_population']=='all_L_samples' and not raw['config']['real_probability_reporting'],'raw_sampling_contract'
            assert raw['config']['no_cross_run_solutions'],'start_isolation'
            for name,digest in meta['input_sha256'].items():assert digest==P['input_pins']['benchmark/'+o['instance']+'/'+name],'worker_input_sha'
            expected_flow='frontier_mitm' if o['arm']=='S10_TOTAL600' else 'ellipsoid_momentbound'
            assert meta['search_flow']==x['search_flow']==raw['search_flow']==expected_flow,'arm_flow'
            if expected_flow=='ellipsoid_momentbound':assert x['ellipsoid_gamma']==2.4 and not raw['config']['ellipsoid_is_final_constraint'],'gamma'
            latest={};final={};evaluations=[]
            for event in trace:
                if 'evaluation' in event:
                    assert 0<=event['probability']<=1,'bad_logged_probability'
                    key=tuple(event['selection']);latest[key]=event;evaluations.append(event['evaluation'])
                if event['stage']=='LSS_final_acceptance':final[tuple(event['selection'])]=event
            assert evaluations==list(range(1,x['evaluation_times']+1)),'missing_evaluation_trace'
            for key,event in final.items():
                assert event['source_evaluation']==latest[key]['evaluation'] and event['probability']==latest[key]['probability'],'stale_final_probability'
                assert event['accepted']==(event['probability']>=.99),'wrong_final_filter'
            variants=x['original_output_variants'];assert len(variants)==3,'variant_coverage'
            for v in variants:
                s=v['selection'];key=tuple(s)
                assert selection_ok(d,s) and abs(sum(d['costs'][j] for j in s)-v['cost'])<=1e-8,'selection_or_cost'
                assert v['probability']>=.99 and v['probability']==latest[key]['probability'] and final[key]['accepted'],'last_LSS_acceptance'
                assert 'real_probability' not in v,'realP_variant'
                if expected_flow=='ellipsoid_momentbound':
                    assert sum((Fraction.from_float(d['moment_expected']['coeff'][j]) for j in s),Fraction(0))<=d['moment_rhs'],'final_CDF_pool_necessary_moment_consistency'

            assert variants[0]['selection']==x['selection'] and variants[0]['cost']==x['cost'] and variants[0]['probability']==x['original_LSS_confidence'],'main_variant'
            csvs=list((root/'result/Localsearch').glob('*_[012].csv'));assert len(csvs)==3,'CSV_coverage'
            for f in csvs:
                v=variants[int(f.stem.rsplit('_',1)[1])]
                with f.open() as stream:
                    reader=csv.DictReader(stream);fields=reader.fieldnames;values=list(reader)
                assert len(fields)==6 and all('Real' not in name for name in fields) and len(values)==1,'CSV_format'
                y=values[0];assert float(y['Cost'])==v['cost'] and float(y['Confidence Level'])==v['probability'] and json.loads(y['Solution'])==v['selection'],'CSV_data'
            candidates=[c for c in raw['candidate_shortlist'] if c['selection']==x['selection']]
            assert candidates,'final_solution_not_in_own_shortlist'
            first=min(c['found_seconds'] for c in candidates)
            assert 0<=first<=meta['elapsed'],'final_discovery_clock'
            r['final_solution_first_found_seconds']=first
            r['final_solution_last_LSS_evaluation_end_seconds']=latest[tuple(x['selection'])]['elapsed_end']
            r['canonical_candidates_checked']=sum(e.get('has_candidate',False) for e in raw.get('ellipsoid_history',[]) if e.get('event')=='candidate_query') if expected_flow=='ellipsoid_momentbound' else 0
            r['legacy_epigraph_guard_would_reject_count']=sum(e.get('canonical_soc_witness',{}).get('legacy_epigraph_guard_would_reject',False) for e in raw.get('ellipsoid_history',[]) if e.get('event')=='candidate_query' and e.get('has_candidate')) if expected_flow=='ellipsoid_momentbound' else 0
            init=next(p for p in meta['phase_records'] if p['phase']=='initialization')
            improvements=sum(q.get('incumbent_improved',False) for q in raw.get('ellipsoid_history',[]) if q.get('event')=='candidate_query')
            r.update({'valid':not global_errors,'cost':x['cost'],'final_LSS_rejected_candidates':sum(not e['accepted'] for e in final.values()),
                'initialization_cost':init['best_after'],'raw_final_cost':raw['selected']['cost'],'ellipsoid_search_improvements':improvements if expected_flow=='ellipsoid_momentbound' else None})
    except Exception as error:r['errors'].append(type(error).__name__+':'+str(error));r['valid']=False
    rows.append(r)
report={'schema':'MB_corrected_record_only_audit_affected30','not_a_performance_conclusion':True,'global_errors':global_errors,'rechecked':len(rows),'valid':sum(r['valid'] for r in rows),'all_actual_clock_under600':all(r['process_wall_seconds']<=600 for r in rows),'new_probability_evaluations':0,'protocol_sha256':sha(H/'PROTOCOL.json'),'runs':rows}
(H/'EARLY_INDEPENDENT_RECORD_AUDIT_V2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='runs'},ensure_ascii=False),flush=True)
if any(not r['valid'] for r in rows):print(json.dumps([{'identity':r['identity'],'errors':r['errors']} for r in rows if not r['valid']]))

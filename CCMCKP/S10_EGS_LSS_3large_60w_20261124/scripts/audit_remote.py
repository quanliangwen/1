"""Independent record-only LSS audit; no solver or probability evaluator calls."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,math,pickle,statistics
import numpy as np
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_lss_3large_60w_20261124'
assert Path.cwd().resolve()==B.resolve()
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=read(H/'PROTOCOL.json');completed=read(H/'COMPLETED.json')
assert completed['phase']=='completed' and completed['terminal']==180 and completed['pending']==0
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
    data[c['index']]={'groups':g,'costs':costs}
def selection_ok(d,s):return len(s)==len(d['groups']) and all(j in g for j,g in zip(s,d['groups']))
outcomes=[read(p) for p in (H/'outcomes').glob('*.json')]
identities={(a['name'],c['index'],rep) for a in P['arms'] for c in P['cases'] for rep in range(1,31)}
if len(outcomes)!=180 or {(o['arm'],o['case_index'],o['rep']) for o in outcomes}!=identities:global_errors.append('coverage_or_duplicates')
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
            assert x['status']==raw['status']=='completed' and x['schema']=='S10_LSS_full_sample_v2','status_or_schema'
            assert x['instance']==raw['instance']==o['instance'] and x['capacity']==raw['capacity']==o['capacity'],'problem_identity'
            assert x['search_seed']==raw['seed']==meta['seed']==o['seed'] and x['rep']==o['rep'],'seed_or_rep'
            assert meta['within_budget'] and meta['elapsed']<=600 and meta['budget']==600,'search_clock'
            assert meta['local_phases']=='none' and meta['backend']=='gurobi','backend'
            assert x['acceptance_evaluator']=='LSS' and x['acceptance_threshold']==.99 and x['final_lss_enforced'],'LSS_contract'
            assert not x['real_probability_reporting'] and 'recorded_real_probability' not in x,'unexpected_realP'
            assert x['lss_sample_index_min']==0 and x['lss_sample_index_max']==499,'sampling_endpoint'
            assert raw['config']['sampling_population']=='all_L_samples' and not raw['config']['real_probability_reporting'],'raw_sampling_contract'
            assert raw['config']['no_cross_run_solutions'],'start_isolation'
            for name,digest in meta['input_sha256'].items():assert digest==P['input_pins']['benchmark/'+o['instance']+'/'+name],'worker_input_sha'
            expected_flow='frontier_mitm' if o['arm']=='S10_LSS_FIXED' else 'ellipsoid_oa'
            assert meta['search_flow']==x['search_flow']==raw['search_flow']==expected_flow,'arm_flow'
            if expected_flow=='ellipsoid_oa':assert x['ellipsoid_gamma']==2.4 and not raw['config']['ellipsoid_is_final_constraint'],'gamma'
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
            assert variants[0]['selection']==x['selection'] and variants[0]['cost']==x['cost'] and variants[0]['probability']==x['original_LSS_confidence'],'main_variant'
            csvs=list((root/'result/Localsearch').glob('*_[012].csv'));assert len(csvs)==3,'CSV_coverage'
            for f in csvs:
                v=variants[int(f.stem.rsplit('_',1)[1])]
                with f.open() as stream:
                    reader=csv.DictReader(stream);fields=reader.fieldnames;values=list(reader)
                assert len(fields)==6 and all('Real' not in name for name in fields) and len(values)==1,'CSV_format'
                y=values[0];assert float(y['Cost'])==v['cost'] and float(y['Confidence Level'])==v['probability'] and json.loads(y['Solution'])==v['selection'],'CSV_data'
            init=next(p for p in meta['phase_records'] if p['phase']=='initialization')
            improvements=sum(q.get('incumbent_improved',False) for q in raw.get('ellipsoid_history',[]) if q.get('event')=='candidate_query')
            r.update({'valid':not global_errors,'cost':x['cost'],'final_LSS_rejected_candidates':sum(not e['accepted'] for e in final.values()),
                'initialization_cost':init['best_after'],'raw_final_cost':raw['selected']['cost'],'ellipsoid_search_improvements':improvements if expected_flow=='ellipsoid_oa' else None})
    except Exception as error:r['errors'].append(type(error).__name__+':'+str(error));r['valid']=False
    rows.append(r)
summaries=[]
for c in P['cases']:
    for arm in P['arms']:
        x=[r for r in rows if r['case_index']==c['index'] and r['arm']==arm['name']];v=[r for r in x if r['valid']]
        ok=len(v)==len(x)==30 and not global_errors;costs=[r['cost'] for r in v];times=[r['process_wall_seconds'] for r in x]
        searches=[r['search_seconds'] for r in x if r['search_seconds'] is not None]
        summaries.append({'case_index':c['index'],'instance':c['instance'],'capacity':c['tmax'],'arm':arm['name'],'registered':30,'valid':len(v),'failures':30-len(v),
            'best':min(costs) if costs else None,'avg':statistics.mean(costs) if ok else None,'std':statistics.stdev(costs) if ok else None,
            'valid_only_avg_diagnostic':statistics.mean(costs) if costs else None,
            'runtime_mean_seconds':statistics.mean(times) if times else None,'runtime_std_seconds':statistics.stdev(times) if len(times)>1 else None,
            'search_mean_seconds':statistics.mean(searches) if len(searches)==30 else None,'search_std_seconds':statistics.stdev(searches) if len(searches)==30 else None,
            'LSS_min':min(r['LSS_probability'] for r in v) if v else None,'LSS_mean':statistics.mean(r['LSS_probability'] for r in v) if v else None,
            'final_LSS_rejected_candidates':sum(r['final_LSS_rejected_candidates'] or 0 for r in x),
            'ellipsoid_search_improvements':sum(r['ellipsoid_search_improvements'] or 0 for r in x) if arm['flow']=='ellipsoid_oa' else None})
def flip(a,b,seed):
    diff=np.array(a)-np.array(b);diff=diff[diff!=0]
    if not len(diff):return 1.
    observed=abs(float(diff.sum()));tol=1e-12*max(1.,observed)
    if len(diff)<=20:
        s=np.array([0.])
        for d in diff:s=np.concatenate([s+d,s-d])
        return float(np.count_nonzero(np.abs(s)>=observed-tol))/len(s)
    rng=np.random.default_rng(seed);count=0;left=99999
    while left:
        n=min(5000,left);count+=np.count_nonzero(np.abs((2*rng.integers(0,2,size=(n,len(diff)))-1)@diff)>=observed-tol);left-=n
    return float(count+1)/100000
def mcnemar(a,b):
    n1=sum(x and not y for x,y in zip(a,b));n2=sum(y and not x for x,y in zip(a,b));n=n1+n2
    return min(1.,2*sum(math.comb(n,k) for k in range(min(n1,n2)+1))/2**n) if n else 1.
comparisons=[]
for c in P['cases']:
    a=sorted([r for r in rows if r['case_index']==c['index'] and r['arm']=='EGS_LSS_FIXED_2p4'],key=lambda r:r['rep'])
    b=sorted([r for r in rows if r['case_index']==c['index'] and r['arm']=='S10_LSS_FIXED'],key=lambda r:r['rep'])
    complete=len(a)==len(b)==30 and all(r['valid'] for r in a+b)
    ma=statistics.mean(r['cost'] for r in a) if complete else None;mb=statistics.mean(r['cost'] for r in b) if complete else None
    comparisons.append({'case_index':c['index'],'complete_pairs':complete,'mean_difference':ma-mb if complete else None,
        'relative_mean_difference':ma/mb-1 if complete else None,'direction':('优' if ma<mb-1e-8 else '劣' if ma>mb+1e-8 else '平') if complete else '不可评',
        'cost_p_raw':flip([r['cost'] for r in a],[r['cost'] for r in b],20261124+c['index']) if complete else None,
        'validity_p_raw':mcnemar([r['valid'] for r in a],[r['valid'] for r in b])})
for k,target in [('cost_p_raw','cost_p_holm3'),('validity_p_raw','validity_p_holm3')]:
    order=sorted(range(3),key=lambda i:comparisons[i][k] if comparisons[i][k] is not None else 1);prev=0
    for rank,i in enumerate(order):
        value=comparisons[i][k];adj=min(1.,max(prev,(3-rank)*(value if value is not None else 1.)));prev=adj;comparisons[i][target]=adj if value is not None else None
report={'schema':'S10_EGS_LSS_fixed_180_record_audit_v1','protocol_sha256':sha(H/'PROTOCOL.json'),'global_errors':global_errors,
    'terminal':len(rows),'valid':sum(r['valid'] for r in rows),'variants_checked':sum(r['valid'] for r in rows)*3,
    'sole_probability_acceptance':'last LSS >= 0.99','new_probability_evaluations':0,'source_commit':P['source_commit'],
    'completed':completed,'launch':read(H/'LAUNCH.json'),'case_summaries':summaries,'comparisons':comparisons,'runs':rows}
(H/'INDEPENDENT_AUDIT_STATISTICS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='runs'},ensure_ascii=False),flush=True)

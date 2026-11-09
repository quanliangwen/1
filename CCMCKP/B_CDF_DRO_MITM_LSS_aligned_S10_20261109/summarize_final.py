import pathlib,json,gzip,hashlib,statistics,math,datetime
H=pathlib.Path(__file__).parent;D=H/'formal30';V=H/'validation';C=H/'final_certificates'
if not all((p/'FINISHED').exists() for p in [D,V,C]):raise RuntimeError('Wait for all search, LSS and independent certificates')
reg=json.load(open(H/'REGISTRATION.json'));cases=reg['cases'];baseline=json.load(open(H/'WORKBOOK_REFERENCE.json',encoding='utf8'))['rows'];s9=json.load(open(H/'PREVIOUS_S9_SUMMARY.json'));s9map={r['index']:r for r in s9['rows']}
raw_registry=json.load(open(H/'RAW_REFERENCE.json'))
old_raw={r['index']:r for r in json.load(open(H/'OLD_BEST_RAW_AUDIT.json'))['rows']}
bybaseline={(r['instance'],float(r['tmax'])):r for r in baseline};calls={p.stem:json.load(open(p)) for p in (V/'calls').glob('*.json')};certs={p.stem:json.load(open(p)) for p in C.glob('*.json')}
rows=[];errors=[];overruns=[];run_detail=[];all_inputs=set();used_calls=set();all_meta=[]
for c in cases:
 b=bybaseline[c['instance'],float(c['tmax'])];runs=[]
 for rep in range(1,31):
  name=f"S10_{c['index']:02d}_r{rep:02d}.json.gz";out=D/name;post=V/(name+'.postselection.json');term=pathlib.Path(str(out)+'.terminal.json');r=dict(index=c['index'],instance=c['instance'],tmax=c['tmax'],rep=rep,seed=960000+rep,accepted=False)
  try:
   terminal=json.load(open(term));p=json.load(open(post));data=json.loads(gzip.decompress(out.read_bytes()));meta=json.load(open(str(out)+'.run.json'));all_meta.append(meta)
   if terminal['exit']!=0 or data['status']!='completed':raise RuntimeError('Search failed/incomplete')
   if meta['source_sha256']!=reg['source_sha256']:raise RuntimeError('Source identity mismatch')
   if meta['seed']!=960000+rep or data['seed']!=960000+rep or p['seed']!=960000+rep:raise RuntimeError('Seed mismatch')
   if p['input_search_sha256']!=hashlib.sha256(out.read_bytes()).hexdigest():raise RuntimeError('Postselection source hash mismatch')
   if data['config']['tail_use']!='removed_entirely' or data['config']['raw_threshold']!='.99':raise RuntimeError('Wrong constraints')
   if not p['accepted']:raise RuntimeError('No LSS-qualified member: '+str(p.get('error')))
   selected=p['selected'];s=selected['selection'];key=selected['LSS_key'];used_calls.add(key)
   if not any(x['selection']==s and abs(x['cost']-selected['cost'])<1e-8 for x in data['candidate_shortlist']):raise RuntimeError('Selected member not from independent search')
   if calls[key]['selection']!=s or calls[key]['seed']!=832273 or calls[key]['draws']!=10000000 or calls[key]['real_probability']<.985:raise RuntimeError('LSS identity/failure')
   cert=certs[key]['certificate'];n=int(cert['lower_numerator']);den=int(cert['denominator'])
   if 100*n<99*den or certs[key]['selection']!=s:raise RuntimeError('Independent raw certificate failure')
   if not p['tested'][-1]['passed'] or any(x['passed'] for x in p['tested'][:-1]):raise RuntimeError('Postselection order/predicate changed')
   if p['tested']!=sorted(p['tested'],key=lambda x:(x['cost'],x['selection'])):raise RuntimeError('Postselection not cost ordered')
   r.update(accepted=True,cost=selected['cost'],selection=s,elapsed=meta['elapsed'],within_total_budget=meta['within_budget'],found_seconds=selected['found_seconds'],real_probability=calls[key]['real_probability'],lower=cert['lower'],raw_best_cost=p['raw_best_cost'],retained_pool_count=data['raw_certified_pool_count'],shortlist_count=len(data['candidate_shortlist']),LSS_candidates_tested=len(p['tested']),LSS_rejected_candidates=len(p['tested'])-1,LSS_logical_seconds=p['logical_MC_seconds'],postselection_actual_seconds=p['elapsed'],standalone_pipeline_seconds=meta['elapsed']+p['logical_MC_seconds'],LSS_key=key,search_source_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),raw_constraint_certificate_method=selected['certificate']['method'],enumeration_complete=data['exhaustive']['complete'] if data['exhaustive'] else None)
   r.update(small_joint_MC_optimality=bool(data['exhaustive'] and data['exhaustive']['complete'] and data['exhaustive']['ambiguous']==0 and len(data['candidate_shortlist'])==data['raw_certified_pool_count']))
   for path,sha in meta['input_sha256'].items():
    full_path='/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance']+'/'+path
    if raw_registry[full_path]!=sha:raise RuntimeError('Per-run original input identity mismatch '+full_path)
    all_inputs.add((c['instance'],path,sha))
   if any(path.endswith('_dist.txt') for path in meta['opened_task_paths']):raise RuntimeError('True metadata entered search')
   if not meta['within_budget']:overruns.append(dict(index=c['index'],rep=rep,elapsed=meta['elapsed'],found_seconds=selected['found_seconds']))
  except Exception as ex:
   r['error']=str(ex);errors.append(dict(index=c['index'],rep=rep,error=str(ex)))
  runs.append(r);run_detail.append(r)
 valid=[r for r in runs if r['accepted']];full=len(valid)==30;costs=[r['cost'] for r in valid];old=s9map[c['index']]
 rows.append(dict(index=c['index'],instance=c['instance'],tmax=c['tmax'],old_best=b['cdf_old_best'],old_avg=b['cdf_old_avg'],old_std=b['cdf_old_std'],old_CDF_Best_real_probability=old['old_CDF_Best_real_probability'],old_CDF_Best_LSS_passed=old['old_CDF_Best_real_probability']>=.985,S9_avg=old['new_avg'],accepted_runs=len(valid),attempts=30,new_best=min(costs) if full else None,new_avg=statistics.mean(costs) if full else None,new_std=statistics.pstdev(costs) if full else None,conditional_valid_avg=statistics.mean(costs) if costs else None,target_met=full and statistics.mean(costs)<=b['cdf_old_best']+1e-8,probability_min=min(r['real_probability'] for r in valid) if valid else None,mean_elapsed=statistics.mean(r['elapsed'] for r in valid) if full else None,mean_LSS_logical_seconds=statistics.mean(r['LSS_logical_seconds'] for r in valid) if full else None,mean_standalone_pipeline_seconds=statistics.mean(r['standalone_pipeline_seconds'] for r in valid) if full else None,total_budget_overruns=sum(not r['within_total_budget'] for r in valid),runs=runs))
 rows[-1].update(old_Best_raw99_passed=old_raw[c['index']]['raw99_passed'],old_Best_raw99_refuted=old_raw[c['index']]['raw99_refuted'],old_Best_raw_probability_lower=old_raw[c['index']]['last_certificate']['lower'],old_Best_raw_probability_upper=old_raw[c['index']]['last_certificate']['upper'],old_Best_both_constraints_passed=old_raw[c['index']]['raw99_passed'] and old['old_CDF_Best_real_probability']>=.985)
 rows[-1]['small_joint_MC_optimality']=full and all(r.get('small_joint_MC_optimality',False) for r in valid)
summary=dict(schema='S10_frozen40x30_raw_DRO_LSS_postselection_final',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),required_runs=1200,terminal_records=len(list(D.glob('*.terminal.json'))),accepted_runs=sum(r['accepted'] for r in run_detail),errors=errors,all30accepted_cases=sum(r['accepted_runs']==30 for r in rows),average_at_or_below_old_best_cases=sum(r['target_met'] for r in rows),S9_improved_cases=sum(r['new_avg'] is not None and r['new_avg']<r['S9_avg']-1e-8 for r in rows),S9_tied_cases=sum(r['new_avg'] is not None and abs(r['new_avg']-r['S9_avg'])<=1e-8 for r in rows),S9_worse_cases=sum(r['new_avg'] is not None and r['new_avg']>r['S9_avg']+1e-8 for r in rows),zero_std_cases=sum(r['new_std'] is not None and r['new_std']<=1e-10 for r in rows),minimum_real_probability=min((r['real_probability'] for r in run_detail if r['accepted']),default=None),unique_MC_calls=len(calls),unique_selected_MC_keys=len(used_calls),independent_raw_certificates=len(certs),actual_unique_MC_seconds=sum(r['seconds'] for r in calls.values()),total_logical_MC_seconds=sum(r.get('LSS_logical_seconds',0) for r in run_detail),total_reject_mapping_count=sum(r.get('LSS_rejected_candidates',0) for r in run_detail),search_seed_range=[960001,960030],source_sha256=reg['source_sha256'],nominal_CL=.99,final_MC_seed=832273,final_MC_draws=10000000,final_MC_event='sum<=T',final_acceptance='point estimate>=.985; original full LSS source',postselection_disclosure=reg['external_role'],time_accounting=reg['time_accounting'],old_best_LSS_accepted_cases=sum(r['old_CDF_Best_LSS_passed'] for r in rows),total_budget_overruns=overruns,total_budget_overrun_count=len(overruns),max_peak_rss_kib=max((m['peak_rss_kib'] for m in all_meta),default=0),rows=rows)
summary.update(old_Best_both_constraints_passed_cases=sum(r['old_Best_both_constraints_passed'] for r in rows),target_met_among_old_Best_both_passed_cases=sum(r['old_Best_both_constraints_passed'] and r['target_met'] for r in rows))
(H/'FINAL_SUMMARY.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
(H/'RUN_DETAILS.json').write_text(json.dumps(run_detail,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in summary.items() if k not in ['rows','source_sha256','errors','total_budget_overruns']},indent=2))

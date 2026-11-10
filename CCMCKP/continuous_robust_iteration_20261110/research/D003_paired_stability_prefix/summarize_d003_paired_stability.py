"""Three paired DEVELOPMENT seeds only after all six qualified prefixes audited."""
from pathlib import Path
import json,statistics
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;D=H/'research/D003_paired_stability_prefix';S=H/'stability/I015_gain_case39';out=D/'DEVELOPMENT_3SEED_STATISTICS.json'
if out.exists():raise RuntimeError('No complete paired statistic overwrite')
a=json.load(open(D/'INDEPENDENT_FINAL_AUDIT.json'));reg=json.load(open(D/'REGISTRATION.json'));sreg=json.load(open(S/'REGISTRATION.json'));raw=json.load(open(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'))
if not a['passed'] or a['result_sha256']!=sha(D/'RESULT.json') or a['registration_sha256']!=sha(D/'REGISTRATION.json') or not raw['passed'] or len(a['pools'])!=6:raise RuntimeError('Complete actual six-prefix independent audit required')
summaries={};pairs=[];expected={label+'_seed'+str(seed) for label in sreg['sources'] for seed in sreg['seeds']}
if set(a['pools'])!=expected:raise RuntimeError('All6 namespaces required; no successful subset statistics')
for label in sreg['sources']:
 rows=[]
 for seed in sreg['seeds']:
  key=label+'_seed'+str(seed);v=a['pools'][key];info=reg['pools'][key]
  if v['source_seed']!=seed or v['original_native_point']<.985 or not a['selected_raw_recounts'][key]['passed']:raise RuntimeError('Each actual run must jointly qualify')
  rows.append(dict(seed=seed,cost=v['cost'],original_native_point=v['original_native_point'],search_seconds=info['search_seconds'],logical_original_MC_seconds=v['logical_original_MC_seconds'],prefix_calls=v['prefix_calls'],cheaper_rejected=v['cheaper_rejected'],selected_key=v['selected_key']))
 costs=[r['cost'] for r in rows];best=min(costs);avg=statistics.mean(costs);summaries[label]=dict(runs=3,Best=best,Avg=avg,Std_population=statistics.pstdev(costs),Avg_minus_own_Best=avg-best,Avg_gap_percent_to_own_Best=(avg/best-1)*100,mean_search_seconds=statistics.mean(r['search_seconds'] for r in rows),mean_logical_original_MC_seconds=statistics.mean(r['logical_original_MC_seconds'] for r in rows),minimum_LSS_point=min(r['original_native_point'] for r in rows),source_sha256=sreg['sources'][label]['source_sha256'],rows=rows)
for seed in sreg['seeds']:
 control=next(r for r in summaries['I002_control']['rows'] if r['seed']==seed);hybrid=next(r for r in summaries['I015_hybrid']['rows'] if r['seed']==seed);pairs.append(dict(seed=seed,I002_cost=control['cost'],I015_cost=hybrid['cost'],control_minus_hybrid_cost=control['cost']-hybrid['cost'],additional_search_seconds=hybrid['search_seconds']-control['search_seconds']))
result=dict(scope='case39three preregistered fresh matched DEVELOPMENT search seeds, all6jointly qualified frozen-pool minimum cost prefixes; not30-runformalAvg, statistical significance/global optimum/independent probability repetitions',summaries=summaries,paired_rows=pairs,mean_paired_cost_improvement=statistics.mean(r['control_minus_hybrid_cost'] for r in pairs),improved_pairs=sum(r['control_minus_hybrid_cost']>1e-9 for r in pairs),tied_pairs=sum(abs(r['control_minus_hybrid_cost'])<=1e-9 for r in pairs),worse_pairs=sum(r['control_minus_hybrid_cost']<-1e-9 for r in pairs),D003_new_physical_MC_calls=a['physical_new_MC_attempts'],D003_new_physical_MC_seconds=a['physical_new_original_MC_seconds'],D003_speculative_extra_MC_seconds=a['speculative_extra_MC_seconds'],fixed_LSS_seed=832273,fixed_LSS_draws=10000000,independent_prefix_audit_sha256=sha(D/'INDEPENDENT_FINAL_AUDIT.json'),search_raw_audit_sha256=sha(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'))
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='summaries'}));print(json.dumps({k:{n:v[n] for n in ['Best','Avg','Std_population','Avg_minus_own_Best']} for k,v in summaries.items()}))

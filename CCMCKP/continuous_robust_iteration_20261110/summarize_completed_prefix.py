"""Only all-audited qualified cost prefixes; n3 dev or per-case n1, never mixedAvg."""
from pathlib import Path
import argparse,json,statistics
from isolated_original_lss import sha
from register_completed_pool_prefix import PROFILES
H=Path(__file__).resolve().parent
def summarize(profile):
 cfg=PROFILES[profile];D=H/cfg['study'];S=H/cfg['cohort'];out=D/'DEVELOPMENT_COMPARISON.json'
 if out.exists():raise RuntimeError('No complete development summary overwrite')
 a=json.load(open(D/'INDEPENDENT_FINAL_AUDIT.json'));r=json.load(open(D/'REGISTRATION.json'));c=json.load(open(S/'REGISTRATION.json'));raw=json.load(open(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'));frozen=json.load(open(H/'formal/F001_I002_40x30/FINAL_AUDIT_STATS.json'));formal={x['index']:x for x in frozen['summary']}
 if not a['passed'] or a['result_sha256']!=sha(D/'RESULT.json') or a['registration_sha256']!=sha(D/'REGISTRATION.json') or not raw['passed'] or len(a['pools'])!=cfg['required'] or set(a['pools'])!=set(r['pools']):raise RuntimeError('Actual whole complete independent prefix/raw audit required')
 rows=[]
 for key,info in r['pools'].items():
  v=a['pools'][key];selected=a['selected_raw_recounts'][key]
  if v['source_seed']!=info['seed'] or v['original_native_point']<.985 or not selected['passed'] or 100*int(selected['numerator'])<99*int(selected['denominator']):raise RuntimeError('Every original registered attempt must jointly qualify')
  rows.append(dict(pool_key=key,label=info['label'],index=info['index'],instance=info['instance'],capacity=info['capacity'],seed=info['seed'],cost=v['cost'],original_native_point=v['original_native_point'],independent_raw_lower=selected['lower'],search_seconds=info['search_seconds'],logical_original_MC_seconds=v['logical_original_MC_seconds'],prefix_calls=v['prefix_calls'],cheaper_rejected=v['cheaper_rejected'],selected_key=v['selected_key']))
 paired=[];summaries={}
 if profile=='P016':
  if len(c['seeds'])!=3 or {row['index'] for row in rows}!={39}:raise RuntimeError('Exactly3 matched seeds of one case required for development means')
  for label in c['sources']:
   values=sorted((v for v in rows if v['label']==label),key=lambda v:v['seed'])
   if len(values)!=3 or [v['seed'] for v in values]!=sorted(c['seeds']):raise RuntimeError('No success-subset Avg')
   costs=[v['cost'] for v in values];best=min(costs);avg=statistics.mean(costs)
   summaries[label]=dict(runs=3,Best=best,Avg=avg,Std_population=statistics.pstdev(costs),Avg_minus_own_Best=avg-best,Avg_minus_historical_Best=avg-formal[39]['old_best'],mean_search_seconds=statistics.mean(v['search_seconds'] for v in values),mean_logical_original_MC_seconds=statistics.mean(v['logical_original_MC_seconds'] for v in values),minimum_LSS_point=min(v['original_native_point'] for v in values),source_sha256=c['sources'][label]['source_sha256'],rows=values)
  for seed in c['seeds']:
   parent=next(v for v in rows if v['label']=='I015_parent' and v['seed']==seed);new=next(v for v in rows if v['label']=='I016_pair_cover' and v['seed']==seed);paired.append(dict(index=39,seed=seed,parent_cost=parent['cost'],new_cost=new['cost'],parent_minus_new=parent['cost']-new['cost'],additional_search_seconds=new['search_seconds']-parent['search_seconds']))
 else:
  if len(c['cases'])!=4 or len(rows)!=8:raise RuntimeError('All4cases x2methods required')
  for case in c['cases']:
   values=[v for v in rows if v['index']==case['index']]
   if len(values)!=2 or {v['label'] for v in values}!=set(c['sources']) or any(v['seed']!=case['seed'] for v in values):raise RuntimeError('Incomplete case pair; no per-case result')
   parent=next(v for v in values if v['label']=='I015_parent');new=next(v for v in values if v['label']=='I016_pair_cover');paired.append(dict(index=case['index'],instance=case['instance'],capacity=case['capacity'],seed=case['seed'],samples_per_method=1,parent_cost=parent['cost'],new_cost=new['cost'],parent_minus_new=parent['cost']-new['cost'],additional_search_seconds=new['search_seconds']-parent['search_seconds'],historical_Best=formal[case['index']]['old_best'],prior_formal_I002_Avg=formal[case['index']]['avg'],per_case_Avg=None,per_case_Std=None))
 result=dict(scope=cfg['scope']+'; all original registered runs jointly qualified and all cheaper pool members actually rejected; no global optimum or independent probability replications',summaries=summaries,paired_rows=paired,all_original_attempts_qualified=len(rows),rows=rows,improved_pairs=sum(v['parent_minus_new']>1e-9 for v in paired),tied_pairs=sum(abs(v['parent_minus_new'])<=1e-9 for v in paired),worse_pairs=sum(v['parent_minus_new']<-1e-9 for v in paired),mean_paired_cost_improvement=statistics.mean(v['parent_minus_new'] for v in paired) if profile=='P016' else None,cross_case_cost_Avg_not_computed=profile=='B016',new_physical_original_MC_calls=a['physical_new_MC_attempts'],new_physical_original_MC_seconds=a['physical_new_original_MC_seconds'],speculative_extra_MC_seconds=a['speculative_extra_MC_seconds'],fixed_LSS_seed=832273,fixed_LSS_draws=10000000,independent_prefix_audit_sha256=sha(D/'INDEPENDENT_FINAL_AUDIT.json'),cohort_raw_audit_sha256=sha(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'))
 with out.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ['rows','summaries']}));print(json.dumps({k:{n:v[n] for n in ['Best','Avg','Std_population','Avg_minus_own_Best']} for k,v in summaries.items()}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cohort',choices=sorted(PROFILES),required=True);summarize(p.parse_args().cohort)

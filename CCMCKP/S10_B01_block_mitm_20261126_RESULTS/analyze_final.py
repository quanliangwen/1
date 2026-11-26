from pathlib import Path
from collections import Counter
import json,statistics
R=Path(__file__).resolve().parent;E=R/'evidence';a=json.loads((E/'formal/FINAL_INDEPENDENT_AUDIT.json').read_text())
assert a['global_errors']==[] and a['terminal']==a['independent_valid']==270
summary=[]
for index in [19,35,39]:
 g={x['arm']:x for x in a['groups'] if x['case_index']==index};A=g['A_S10_ORIGINAL'];C=g['C_B01_ZERO']
 line={'case_index':index,'S10_avg':A['official_avg'],'B01_avg':C['official_avg'],'avg_diff':C['official_avg']-A['official_avg'],'S10_std':A['official_std'],'B01_std':C['official_std'],'S10_mean_whole':A['whole_mean'],'B01_mean_whole':C['whole_mean'],'observed_runtime_reduction_fraction':1-C['whole_mean']/A['whole_mean']}
 line['cost_holm9_p']=next(c['cost_p_holm9'] for c in a['comparisons'] if c['case_index']==index and c['candidate']=='C_B01_ZERO' and c['reference']=='A_S10_ORIGINAL')
 summary.append(line)
distribution={}
for arm in ['A_S10_ORIGINAL','B_S10_ZERO','C_B01_ZERO']:
 rows=[r for r in a['rows'] if r['case_index']==39 and r['arm']==arm]
 distribution[arm]={'final_cost_frequencies':dict(Counter(str(r['cost']) for r in rows)),'above_raw_best_runs':sum(r['final_cost_above_raw_best'] for r in rows),'mean_increment_conditional_fallback':statistics.mean(r['final_cost_minus_raw_best'] for r in rows if r['final_cost_above_raw_best'])}
 pool=[]
 for r in rows:
  raw=json.loads((E/'formal/runs'/r['identity']/'S10_search.json').read_text())
  costs=sorted(set(c['cost'] for c in raw['candidate_shortlist'] if raw['selected']['cost']-1e-8<=c['cost']<=322.63304961409597+1e-8))
  pool.append(costs)
 distribution[arm]['lowest_interval_pool_cost_sets']=list({tuple(row) for row in pool})
report={'summary':summary,'case39_pool_and_fallback_diagnosis':distribution,'conclusion':'runtime improved descriptively; no avg improvement vs original S10; case39 observed sample std increased; do not expand40 or claim new DRO contribution'}
(R/'FINAL_COMPARISON_AND_DIAGNOSIS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))

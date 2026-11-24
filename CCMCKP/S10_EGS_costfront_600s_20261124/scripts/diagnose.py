from pathlib import Path
from collections import Counter
import json, statistics
R=Path(__file__).resolve().parent
O=Path('E:/codex/S10_EGS_LSS_3large_60w_20261124/evidence')
A=json.loads((O/'INDEPENDENT_AUDIT_STATISTICS.json').read_text())
out=[]
for c in [19,35,39]:
 for arm in ['S10_LSS_FIXED','EGS_LSS_FIXED_2p4']:
  rows=[r for r in A['runs'] if r['case_index']==c and r['arm']==arm]
  hist=[];tracecounts=[];findtimes=[];pools=[];init=[];cert=[];search=[];wall=[]
  for r in rows:
   D=O/'runs'/r['identity']; raw=json.loads((D/'S10_search.json').read_text())
   tr=json.loads((D/'ORIGINAL_LSS_DECISION_TRACE.json').read_text())
   h=[x for x in raw['ellipsoid_history'] if x.get('event')=='candidate_query'];hist+=h
   tracecounts.append(sum('evaluation' in x for x in tr));pools.append(raw['raw_certified_pool_count'])
   cert.append(raw['certificate_seconds']);search.append(r['search_seconds']);wall.append(r['process_wall_seconds'])
   init.append(r['initialization_cost']);findtimes.append(raw['selected']['found_seconds'])
  q=[x for x in hist if x.get('has_candidate')]
  out.append(dict(case=c,arm=arm,runs=len(rows),search_mean=statistics.mean(search),wall_mean=statistics.mean(wall),
   nonsearch_wall_mean=statistics.mean(w-s for w,s in zip(wall,search)),LSS_calls_mean=statistics.mean(tracecounts),
   raw_pool_mean=statistics.mean(pools),raw_certificate_seconds_mean=statistics.mean(cert),
   final_raw_best_first_found_mean=statistics.mean(findtimes),initial_costs=dict(Counter(init)),
   queries=len(hist),candidate_queries=len(q),no_candidate_queries=len(hist)-len(q),
   queries_solver_seconds=sum(x.get('seconds',0) for x in hist),
   native_check_seconds=sum(x.get('shared_check_seconds',0) for x in hist),
   accepted_raw_candidates=sum(x.get('raw_certificate_accepted',False) for x in hist),
   incumbent_improvements=sum(x.get('incumbent_improved',False) for x in hist),
   proxy_optimal_queries=sum(x.get('proxy_optimal',False) for x in hist),
   cone_converged_queries=sum(x.get('cone_converged',False) for x in hist)))
(R/'PREVIOUS_RUN_DIAGNOSIS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))

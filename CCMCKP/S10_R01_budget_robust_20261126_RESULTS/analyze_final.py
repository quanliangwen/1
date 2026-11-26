from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,statistics
R=Path(__file__).resolve().parent;E=R/'evidence';read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
a=read(E/'formal/FINAL_INDEPENDENT_AUDIT.json');structure=read(E/'STRUCTURE_DIAGNOSTIC.json')
assert a['terminal']==270 and a['global_errors']==[]
rows=[]
for r in a['rows']:
 r=dict(r);F=E/'formal/runs'/r['identity'];raw=read(F/'S10_search.json');meta=read(F/'S10_search.run.json')
 r['search_seconds']=meta['elapsed']
 r['shortlist_count']=len(raw['candidate_shortlist']);r['raw_pool_count']=raw['raw_certified_pool_count']
 r['transport_exclusions_verified']=r.get('transport_exclusions_verified',0)
 initial=next((q for q in raw['events'] if q.get('event')=='raw_certified_incumbent'),None)
 r['self_first_accepted_cost']=initial['cost'] if initial else None
 r['budget_proofs_verified']=r.get('budget_proofs_verified',{'proofs':0,'qualified':0,'rejected':0,'subproblems':0})
 r['budget_statistics']=raw['budget_RO_statistics']
 r['active_certificate_calls']=raw['search_certificate_calls'];r['active_certificate_seconds']=raw['search_certificate_seconds']
 if r['valid'] and r['arm']=='C_R01_BUDGET_RO':
  q=next(q for q in raw['budget_RO_proposals'] if q['selection']==r['selection'] and q['robust_feasible'] and q['fixed_theta_feasible'])
  r.update(final_budget_gamma=q['gamma'],final_budget_theta=q['theta'],final_budget_worst_load=float(Fraction(q['budget_worst_sum'])))
 rows.append(r)
summaries=[]
for g in a['groups']:
 rr=[r for r in rows if r['case_index']==g['case_index'] and r['arm']==g['arm']];vv=[r for r in rr if r['valid']]
 best=min((r['cost'] for r in vv),default=None);hits=[r for r in vv if r['cost']==best]
 summaries.append(dict(g,valid_whole_mean=statistics.mean(r['process_wall_seconds'] for r in vv) if vv else None,whole_max=max(r['process_wall_seconds'] for r in rr),whole_std=statistics.stdev(r['process_wall_seconds'] for r in rr),first_found_mean=statistics.mean(r['first_found_seconds'] for r in vv) if len(vv)==30 else None,best_hits=len(hits),best_conditional_found_mean=statistics.mean(r['first_found_seconds'] for r in hits) if hits else None,valid_search_mean=statistics.mean(r['search_seconds'] for r in vv) if vv else None,valid_LSS_mean=statistics.mean(r['LSS_seconds'] for r in vv) if vv else None))
counts=Counter(r.get('failure_class','unclassified') for r in rows if not r['valid'])
primary=[c for c in a['comparisons'] if c['candidate']=='C_R01_BUDGET_RO']
complete=[c for c in primary if c['complete30']];better=sum(c['avg_diff']<0 for c in complete);worse=sum(c['avg_diff']>0 for c in complete)
sigbetter=sum(c['avg_diff']<0 and c['cost_p_holm9']<.05 for c in complete);sigworse=sum(c['avg_diff']>0 and c['cost_p_holm9']<.05 for c in complete)
headline=f"独立有效{a['independent_valid']}/270；R01存在不足30次有效的算例，官方成本均值留空。完整配对比较中{better}项均值较优、{worse}项较劣，Holm9显著优{sigbetter}项、显著劣{sigworse}项。"
diag={'headline':headline,'rows':rows,'groups':summaries,'comparisons':a['comparisons'],'failure_counts':dict(counts),'structural_model_diagnostic':structure,'max_whole_seconds':max(r['process_wall_seconds'] for r in rows),'all_under600':all(r['process_wall_seconds']<=600 for r in rows),'no_probability_resampling':True,'no_retries':True,'no_automatic_full40':True,'first_failed_excel_row':next((i+5 for i,r in enumerate(rows) if not r['valid']),5)}
(R/'FINAL_COMPARISON_AND_DIAGNOSIS.json').write_text(json.dumps(diag,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'headline':headline,'groups':summaries,'failures':dict(counts),'max_whole_seconds':diag['max_whole_seconds']},ensure_ascii=False))

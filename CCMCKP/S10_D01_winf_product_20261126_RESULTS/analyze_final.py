from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,statistics
R=Path(__file__).resolve().parent;E=R/'evidence';a=json.loads((E/'formal/FINAL_INDEPENDENT_AUDIT.json').read_text())
assert a['global_errors']==[] and a['terminal']==270
summary=[];frequencies={};block_events={};model_rejection={}
for r in a['rows']:
 raw=json.loads((E/'formal/runs'/r['identity']/'S10_search.json').read_text())
 block_events[r['identity']]=sum(e.get('event')=='raw_certified_incumbent' and e.get('source','').startswith(('B01_','C01_insurance_block','D01_DRO_block')) for e in raw['events'])
for case in [19,35,39]:
 groups={g['arm']:g for g in a['groups'] if g['case_index']==case}
 first=next(r for r in a['rows'] if r['case_index']==case and r['arm']=='A_B01_ORIGINAL' and r['rep']==1)
 rawA=json.loads((E/'formal/runs'/first['identity']/'S10_search.json').read_text());target=rawA['selected']['selection'];proof=None
 for cr in (r for r in a['rows'] if r['case_index']==case and r['arm']=='C_D01_WINF_PRODUCT'):
  rawC=json.loads((E/'formal/runs'/cr['identity']/'S10_search.json').read_text())
  for q in rawC['native_infeasible_proofs']:
   if q['selection']==target:proof={'identity':cr['identity'],'certificate':q};break
  if proof:break
 model_rejection[case]={'nominal_model_best_cost':rawA['selected']['cost'],'nominal_selection':target,'existing_DRO_infeasible_certificate':proof}
 for candidate,reference in [('B_COVERAGE_NOMINAL','A_B01_ORIGINAL'),('C_D01_WINF_PRODUCT','A_B01_ORIGINAL'),('C_D01_WINF_PRODUCT','B_COVERAGE_NOMINAL')]:
  c,b=groups[candidate],groups[reference]
  comp=next(q for q in a['comparisons'] if q['case_index']==case and q['candidate']==candidate and q['reference']==reference)
  complete=c['official_avg'] is not None and b['official_avg'] is not None
  summary.append({'case_index':case,'candidate':candidate,'reference':reference,'candidate_avg':c['official_avg'],'reference_avg':b['official_avg'],'candidate_std':c['official_std'],'reference_std':b['official_std'],'avg_diff':comp['avg_diff'],'relative_avg_change':c['official_avg']/b['official_avg']-1 if complete else None,'cost_holm9_p':comp['cost_p_holm9'],'candidate_whole_mean':c['whole_mean'],'reference_whole_mean':b['whole_mean'],'relative_whole_change':c['whole_mean']/b['whole_mean']-1,'complete30':complete})
 for arm,g in groups.items():
  rr=[r for r in a['rows'] if r['case_index']==case and r['arm']==arm and r['valid']]
  frequencies[str(case)+'|'+arm]={'final_cost_frequencies':dict(Counter(str(r['cost']) for r in rr)),'raw_best_cost_frequencies':dict(Counter(str(r['raw_final_cost']) for r in rr)),'final_LSS_fallback_runs':sum(r['final_cost_above_raw_best'] for r in rr),'mean_fallback_cost_increment':statistics.mean(r['final_cost_minus_raw_best'] for r in rr) if rr else None,'mean_raw_pool_count':statistics.mean(r['raw_pool_count'] for r in rr) if rr else None,'mean_LSS_seconds':statistics.mean(r['LSS_seconds'] for r in rr) if rr else None,'post_initialization_improved_runs':sum(r['post_init_improved'] for r in rr),'selected_transport_shift_mean':float(statistics.mean(Fraction(r['selected_transport_shift']) for r in rr)) if rr and arm=='C_D01_WINF_PRODUCT' else None}
primary=[x for x in summary if x['candidate']=='C_D01_WINF_PRODUCT' and x['reference']=='B_COVERAGE_NOMINAL']
complete=all(x['complete30'] for x in primary)
better=sum(x['avg_diff'] is not None and x['avg_diff']<0 for x in primary);equal=sum(x['avg_diff']==0 for x in primary);worse=sum(x['avg_diff'] is not None and x['avg_diff']>0 for x in primary)
sigbetter=sum(x['avg_diff'] is not None and x['avg_diff']<0 and x['cost_holm9_p']<.05 for x in primary);sigworse=sum(x['avg_diff'] is not None and x['avg_diff']>0 and x['cost_holm9_p']<.05 for x in primary)
headline=(f'DRO对相同名义框架：{better}优{equal}平{worse}劣，Holm9显著优{sigbetter}例、显著劣{sigworse}例。' if complete else '部分组不足30个独立有效结果，不能给完整成本/波动结论。')
headline+='本轮没有自动扩展40例。'
report={'headline':headline,'summary':summary,'primary_DRO_comparison':{'complete_all3':complete,'better_equal_worse':[better,equal,worse],'holm9_significant_better_worse':[sigbetter,sigworse],'mean_equal_case_relative_avg_change':statistics.mean(x['relative_avg_change'] for x in primary) if complete else None},'cost_distributions_and_pool_diagnostics':frequencies,'nominal_best_vs_existing_DRO_rejections':model_rejection,'block_events_by_identity':block_events,'block_counter_note':'Derived report count recognizes B01_, C01_insurance_block and D01_DRO_block. Legacy independent audit diagnostic counter recognizes B01_ only; validity, cost, clocks and model certificates unaffected. Immutable audit retained.','max_actual_whole_seconds':max(r['process_wall_seconds'] for r in a['rows']),'no_extra_probability_sampling':True,'no_automatic_full40':True}
(R/'FINAL_COMPARISON_AND_DIAGNOSIS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'headline':headline,'primary':report['primary_DRO_comparison'],'summary':summary},ensure_ascii=False))

from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,statistics
R=Path(__file__).resolve().parent;E=R/'evidence';a=json.loads((E/'formal/FINAL_INDEPENDENT_AUDIT.json').read_text())
assert a['global_errors']==[] and a['terminal']==270
summary=[];frequencies={};block_events={}
for r in a['rows']:
 raw=json.loads((E/'formal/runs'/r['identity']/'S10_search.json').read_text())
 block_events[r['identity']]=sum(e.get('event')=='raw_certified_incumbent' and e.get('source','').startswith(('B01_','C01_insurance_block','D01_DRO_block')) for e in raw['events'])
for case in [19,35,39]:
 groups={g['arm']:g for g in a['groups'] if g['case_index']==case}
 for candidate,reference in [('B_D01_WINF','A_B01_ORIGINAL'),('C_D02_TRANSPORT','A_B01_ORIGINAL'),('C_D02_TRANSPORT','B_D01_WINF')]:
  c,b=groups[candidate],groups[reference]
  comp=next(q for q in a['comparisons'] if q['case_index']==case and q['candidate']==candidate and q['reference']==reference)
  complete=c['official_avg'] is not None and b['official_avg'] is not None
  summary.append({'case_index':case,'candidate':candidate,'reference':reference,'candidate_avg':c['official_avg'],'reference_avg':b['official_avg'],'candidate_std':c['official_std'],'reference_std':b['official_std'],'avg_diff':comp['avg_diff'],'relative_avg_change':c['official_avg']/b['official_avg']-1 if complete else None,'cost_holm9_p':comp['cost_p_holm9'],'candidate_whole_mean':c['whole_mean'],'reference_whole_mean':b['whole_mean'],'relative_whole_change':c['whole_mean']/b['whole_mean']-1,'complete30':complete})
 for arm,g in groups.items():
  rr=[r for r in a['rows'] if r['case_index']==case and r['arm']==arm and r['valid']]
  frequencies[str(case)+'|'+arm]={'final_cost_frequencies':dict(Counter(str(r['cost']) for r in rr)),'raw_best_cost_frequencies':dict(Counter(str(r['raw_final_cost']) for r in rr)),'final_LSS_fallback_runs':sum(r['final_cost_above_raw_best'] for r in rr),'mean_fallback_cost_increment':statistics.mean(r['final_cost_minus_raw_best'] for r in rr) if rr else None,'mean_raw_pool_count':statistics.mean(r['raw_pool_count'] for r in rr) if rr else None,'mean_LSS_seconds':statistics.mean(r['LSS_seconds'] for r in rr) if rr else None,'post_initialization_improved_runs':sum(r['post_init_improved'] for r in rr),'selected_transport_shift_mean':float(statistics.mean(Fraction(r['selected_transport_shift']) for r in rr)) if rr and arm!='A_B01_ORIGINAL' else None}
primary=[x for x in summary if x['candidate']=='C_D02_TRANSPORT' and x['reference']=='B_D01_WINF']
complete=all(x['complete30'] for x in primary)
better=sum(x['avg_diff'] is not None and x['avg_diff']<0 for x in primary);equal=sum(x['avg_diff']==0 for x in primary);worse=sum(x['avg_diff'] is not None and x['avg_diff']>0 for x in primary)
sigbetter=sum(x['avg_diff'] is not None and x['avg_diff']<0 and x['cost_holm9_p']<.05 for x in primary);sigworse=sum(x['avg_diff'] is not None and x['avg_diff']>0 and x['cost_holm9_p']<.05 for x in primary)
headline=(f'D02对同模型D01：{better}优{equal}平{worse}劣，Holm9显著优{sigbetter}例、显著劣{sigworse}例。' if complete else '部分组不足30个独立有效结果，不能给完整成本/波动结论。')
headline+='本轮没有自动扩展40例。'
report={'headline':headline,'summary':summary,'primary_transport_comparison':{'complete_all3':complete,'better_equal_worse':[better,equal,worse],'holm9_significant_better_worse':[sigbetter,sigworse],'mean_equal_case_relative_avg_change':statistics.mean(x['relative_avg_change'] for x in primary) if complete else None},'cost_distributions_and_pool_diagnostics':frequencies,'block_events_by_identity':block_events,'block_counter_note':'Both independent audit and derived report count actual incumbent events with B01_, C01_insurance_block and D01_DRO_block prefixes.','max_actual_whole_seconds':max(r['process_wall_seconds'] for r in a['rows']),'no_extra_probability_sampling':True,'no_automatic_full40':True}
mechanism=[]
for case in [19,35,39]:
 for arm in ['A_B01_ORIGINAL','B_D01_WINF','C_D02_TRANSPORT']:
  rr=[r for r in a['rows'] if r['case_index']==case and r['arm']==arm and r['valid']]
  complete=len(rr)==30
  mechanism.append({'case_index':case,'arm':arm,'complete30':complete,'active_certificate_calls_mean':statistics.mean(r['active_certificate_calls'] for r in rr) if complete else None,'active_certificate_seconds_mean':statistics.mean(r['active_certificate_seconds'] for r in rr) if complete else None,'transport_exclusions_mean':statistics.mean(r['transport_exclusions_verified'] for r in rr) if complete else None,'transport_preparation_mean':statistics.mean((r['transport_statistics'] or {}).get('preparation_seconds',0) for r in rr) if complete else None,'transport_query_add_mean':statistics.mean((r['transport_statistics'] or {}).get('probe_seconds',0)+(r['transport_statistics'] or {}).get('add_seconds',0) for r in rr) if complete else None})
report['mechanism_summary']=mechanism
report['all_transport_exclusions_verified']=a['independent_transport_exclusions_verified']
performance=[]
for case in [19,35,39]:
 b=next(g for g in a['groups'] if g['case_index']==case and g['arm']=='B_D01_WINF')
 c=next(g for g in a['groups'] if g['case_index']==case and g['arm']=='C_D02_TRANSPORT')
 bm=next(g for g in mechanism if g['case_index']==case and g['arm']=='B_D01_WINF')
 cm=next(g for g in mechanism if g['case_index']==case and g['arm']=='C_D02_TRANSPORT')
 byarm={arm:sorted([r for r in a['rows'] if r['case_index']==case and r['arm']==arm],key=lambda r:r['rep']) for arm in ['B_D01_WINF','C_D02_TRANSPORT']}
 pairs=list(zip(byarm['B_D01_WINF'],byarm['C_D02_TRANSPORT']));assert all(x['seed']==y['seed'] for x,y in pairs)
 block_counts={};block_gains={}
 for arm,rr in byarm.items():
  counts=[];gains=[]
  for r in rr:
   raw=json.loads((E/'formal/runs'/r['identity']/'S10_search.json').read_text());counts.append(len(raw['block_history']));gains.append(block_events[r['identity']])
  block_counts[arm]=statistics.mean(counts);block_gains[arm]=sum(gains)
 performance.append({'case_index':case,'whole_mean_relative_change_C_vs_B':c['whole_mean']/b['whole_mean']-1,'active_CDF_call_relative_change':cm['active_certificate_calls_mean']/bm['active_certificate_calls_mean']-1,'active_CDF_seconds_saved':bm['active_certificate_seconds_mean']-cm['active_certificate_seconds_mean'],'transport_added_seconds':cm['transport_preparation_mean']+cm['transport_query_add_mean'],'search_mean_B':statistics.mean(r['search_seconds'] for r in byarm['B_D01_WINF']),'search_mean_C':statistics.mean(r['search_seconds'] for r in byarm['C_D02_TRANSPORT']),'LSS_mean_B':b['mean_LSS_seconds'],'LSS_mean_C':c['mean_LSS_seconds'],'same_final_selection_pairs':sum(x['selection']==y['selection'] for x,y in pairs),'same_final_cost_pairs':sum(x['cost']==y['cost'] for x,y in pairs),'block_history_mean':block_counts,'block_incumbent_events':block_gains})
report['performance_interpretation']=performance
report['same_model_90_run_mean_wall_relative_change']=statistics.mean(x['candidate_whole_mean'] for x in primary)/statistics.mean(x['reference_whole_mean'] for x in primary)-1
report['timing_limits']='Descriptive elapsed-time comparisons at the matched concurrent server load; no runtime significance test or universal speedup claim.'
(R/'FINAL_COMPARISON_AND_DIAGNOSIS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'headline':headline,'primary':report['primary_transport_comparison'],'summary':summary},ensure_ascii=False))

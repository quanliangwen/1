from pathlib import Path
import json,statistics,hashlib
R=Path(__file__).resolve().parent;E=R/'evidence'
A=json.loads((E/'INDEPENDENT_AUDIT_STATISTICS.json').read_text())
assert A['terminal']==180 and not A['global_errors'] and A['new_probability_evaluations']==0
parent=json.loads((Path('E:/codex/S10_EGS_costpriority_600s_20261124')/'CUMULATIVE_EXPLORATORY_TESTS.json').read_text())
tests=[{k:v for k,v in t.items() if not k.startswith('cumulative_holm')} for t in parent['tests']]
for name,report in [('MB',Path('E:/codex/S10_EGS_momentbound_600s_20261124/evidence/INDEPENDENT_AUDIT_STATISTICS.json')),('CORE',E/'INDEPENDENT_AUDIT_STATISTICS.json')]:
 a=json.loads(report.read_text());assert not a['global_errors']
 for c in a['comparisons']:tests.append({'trial':name,'case':c['case_index'],'raw_p':c['cost_p_raw']})
assert len(tests)==18
previous=0
for rank,i in enumerate(sorted(range(18),key=lambda i:tests[i]['raw_p'] if tests[i]['raw_p'] is not None else 1)):
 p=tests[i]['raw_p'];v=min(1.,max(previous,(18-rank)*(p if p is not None else 1.)));previous=v
 tests[i]['cumulative_holm18']=v if p is not None else None
(R/'CUMULATIVE_EXPLORATORY_TESTS.json').write_text(json.dumps({'scope':'exploratory adaptive revisions, not confirmatory validation','family_size':18,'incomplete_old_DC_tests_reserved_at_1':True,'tests':tests},ensure_ascii=False,indent=2),encoding='utf-8')
diagnostics=[]
for g in A['case_summaries']:
 if g['arm']=='S10_TOTAL600':continue
 records=[]
 for r in A['runs']:
  if r['arm']!=g['arm'] or r['case_index']!=g['case_index']:continue
  raw=json.loads((E/'runs'/r['identity']/'S10_search.json').read_text());queries=[q for q in raw['ellipsoid_history'] if q.get('event')=='candidate_query']
  cores=[c for c in raw['dominance_cuts'] if 'core_groups' in c]
  records.append({'identity':r['identity'],'valid':r['valid'],'queries':len(queries),'candidate_queries':sum(q.get('has_candidate',False) for q in queries),
    'model_query_seconds':sum(q.get('seconds',0) for q in queries),'original_candidate_check_seconds':sum(q.get('shared_check_seconds',0) for q in queries),
    'core_work_seconds':max((q.get('core_total_seconds',0) for q in queries),default=0),'core_cuts':len(cores),'core_sizes':[len(c['core_groups']) for c in cores],
    'raw_CDF_accepted_queries':sum(q.get('raw_certificate_accepted',False) for q in queries),'main_search_improvements':sum(q.get('incumbent_improved',False) for q in queries),
    'whole_wall_seconds':r['process_wall_seconds'],'final_cost':r['cost'],'initialization_cost':r.get('initialization_cost')})
 sizes=[n for r in records for n in r['core_sizes']]
 diagnostics.append({'case_index':g['case_index'],'instance':g['instance'],'runs':len(records),'valid':g['valid'],
   'query_count_total':sum(r['queries'] for r in records),'core_cuts_total':len(sizes),'core_size_min':min(sizes) if sizes else None,
   'core_size_mean':statistics.mean(sizes) if sizes else None,'core_size_max':max(sizes) if sizes else None,
   'model_query_mean_seconds':statistics.mean(r['model_query_seconds'] for r in records),
   'candidate_check_mean_seconds':statistics.mean(r['original_candidate_check_seconds'] for r in records),
   'core_work_mean_seconds':statistics.mean(r['core_work_seconds'] for r in records),
   'raw_CDF_accepted_queries':sum(r['raw_CDF_accepted_queries'] for r in records),
   'main_search_improvements':sum(r['main_search_improvements'] for r in records),
   'runs_with_main_search_improvement':sum(r['main_search_improvements']>0 for r in records),'records':records})
data={'scope':'read-only deterministic accounting from all90 candidate runs, no new solver or probability evaluations','diagnostics':diagnostics}
(R/'CORE_TERMINAL_DIAGNOSIS.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
summary={k:v for k,v in A.items() if k not in ['runs','case_summaries']}
summary['case_summaries']=[{k:v for k,v in g.items() if k!='core_sizes'} for g in A['case_summaries']]
summary['max_actual_seconds']=max(r['process_wall_seconds'] for r in A['runs'])
(R/'RESULT_SUMMARY_COMPACT.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'summary':summary,'diagnostics':[{k:v for k,v in d.items() if k!='records'} for d in diagnostics]},ensure_ascii=False))

from pathlib import Path
import json,statistics,hashlib,csv
R=Path(__file__).resolve().parent
P=R.parent
O=P.parent
D=R/'delivery';D.mkdir(exist_ok=True)
data=json.loads((P/'statistics.json').read_text(encoding='utf-8'))
rows=[];checks=[]
for r in data['rows']:
 root=O/'evidence/full40/runs'/r['identity']
 raw=json.loads((root/'S10_search.json').read_text(encoding='utf-8'))
 result=json.loads((root/'RESULT.json').read_text(encoding='utf-8'))
 outcome=json.loads((O/'evidence/full40/OUTCOMES.json').read_text(encoding='utf-8')) if False else None
 same=[q for q in raw['candidate_shortlist'] if q['selection']==r['selected']]
 assert same and result['selection']==r['selected'] and result['cost']==r['cost']
 first=min(q['found_seconds'] for q in same)
 assert first==r['first_output_candidate_found_seconds'] and 0<=first<=r['whole_seconds']
 # The parent pool guard prevents a certified selection from being overwritten.
 # Check all native calls of the returned selection and same-cost alternatives.
 calls=[q for q in raw['r07_native_calls'] if q['selection']==r['selected'] and q['state']=='accepted']
 assert len(calls)<=1
 if calls: assert calls[0]['start']<=first<=calls[0]['finish']
 trace=json.loads((root/'ORIGINAL_LSS_DECISION_TRACE.json').read_text(encoding='utf-8'))
 accepted=[q for q in trace if q.get('probability',0)>=.99 and q.get('selection')==r['selected'] and 'evaluation' in q]
 assert accepted
 lss=min(q['elapsed_end'] for q in accepted)
 assert first<=lss<=r['whole_seconds']
 # Cost ties across distinct selections must not silently use a later selection.
 alternatives=[q for q in raw['candidate_shortlist'] if q['cost']==same[0]['cost'] and q['selection']!=r['selected']]
 assert not alternatives, ('equal-cost distinct selection requires review',r['identity'])
 g=next(g for g in data['groups'] if g['case_index']==r['case_index'])
 rows.append({**r,'best_hit':int(r['cost']==g['best']),'first_best_found_seconds':first,'first_output_LSS_accept_seconds':lss})
 checks.append({'identity':r['identity'],'selection_matches':True,'timestamp_matches_audit':True,'distinct_equal_cost_selections':len(alternatives)})
groups=[]
for g in data['groups']:
 rr=[r for r in rows if r['case_index']==g['case_index']]
 hit=[r for r in rr if r['best_hit']]
 assert len(hit)==g['best_hit_count'] and hit
 groups.append({**g,'best_hit_first_mean_seconds':statistics.mean(r['first_best_found_seconds'] for r in hit),'best_hit_first_min_seconds':min(r['first_best_found_seconds'] for r in hit),'best_hit_first_max_seconds':max(r['first_best_found_seconds'] for r in hit),'best_hit_LSS_first_mean_seconds':statistics.mean(r['first_output_LSS_accept_seconds'] for r in hit)})
data.update(rows=rows,groups=groups,time_definition={'best':'minimum unrounded final LSS-accepted cost among the registered 30 runs','hit':'final cost exactly equals case Best, without decimal display rounding','time':'first certification/acceptance of returned solution in the internal CDF pool, measured from process launch; final original LSS acceptance subsequently verified','mean':'arithmetic mean over Best-hit runs only','not_included':'non-hit runs are excluded, not assigned zero or 600; time is not complete process duration or first final-LSS acceptance','population_optimum_claim':False})
(R/'statistics.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
compact={'definition':data['time_definition'],'groups':groups,'rows':[{k:r[k] for k in ['case_index','instance_label','capacity','rep','seed','cost','whole_seconds','best_hit','first_best_found_seconds','first_output_LSS_accept_seconds','identity']} for r in rows]}
(D/'R07_首次达到Best时间_统计明细.json').write_text(json.dumps(compact,ensure_ascii=False,indent=2),encoding='utf-8')
with (D/'R07_40例首次达到Best时间.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=['case_index','instance_label','capacity','best','avg','sample_std','best_hit_count','best_hit_first_mean_seconds','whole_mean_seconds']
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(groups)
(R/'TIMESTAMP_QA.json').write_text(json.dumps({'status':'PASS','checked_runs':len(checks),'groups':40,'raw_certification_timestamp_and_original_LSS_checked':True,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','runs':len(rows),'groups':len(groups),'examples':[{k:g[k] for k in ['case_index','best_hit_count','best_hit_first_mean_seconds','whole_mean_seconds']} for g in groups if g['case_index'] in [11,35,38,39]]},ensure_ascii=False))

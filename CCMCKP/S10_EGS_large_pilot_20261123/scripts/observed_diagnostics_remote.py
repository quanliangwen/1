"""Preserve reported outputs even when the independent final-LSS gate fails.
No solver calls, probability resampling, validity changes, or cost imputation.
"""
from pathlib import Path
import hashlib,json,statistics
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_large_pilot_20261123'
assert Path.cwd().resolve()==B.resolve()
A=json.loads((H/'INDEPENDENT_AUDIT_STATISTICS.json').read_text())
assert A['terminal']==270 and not A['global_errors']
rows=[]
for r in A['runs']:
    root=H/'runs'/r['identity']
    result=json.loads((root/'RESULT.json').read_text());raw=json.loads((root/'S10_search.json').read_text());meta=json.loads((root/'S10_search.run.json').read_text())
    init=next(p for p in meta['phase_records'] if p['phase']=='initialization')
    source=[c for c in raw['candidate_shortlist'] if c['selection']==result['selection']]
    assert len(source)==1
    below=result['original_LSS_confidence']<.99
    assert (not r['valid'])==below,'Investigate a failure beyond final LSS instead of relabelling it'
    qs=[q for q in raw.get('ellipsoid_history',[]) if q.get('event')=='candidate_query']
    rows.append({'identity':r['identity'],'case_index':r['case_index'],'arm':r['arm'],'rep':r['rep'],
        'reported_output_cost':result['cost'],'reported_final_lss_probability':result['original_LSS_confidence'],
        'reported_real_probability':result['recorded_real_probability'],'observed_search_seconds':meta['elapsed'],
        'observed_final_selection_first_raw_accept_seconds':source[0]['found_seconds'],
        'observed_initialization_best_cost':init['best_after'],'observed_initialization_seconds':init['elapsed'],
        'observed_raw_final_best_cost':raw['selected']['cost'],'observed_selection':result['selection'],
        'observed_egs_queries':len(qs),'observed_egs_new_acceptances':sum(q.get('raw_certificate_accepted',False) for q in qs),
        'observed_egs_improvements':sum(q.get('incumbent_improved',False) for q in qs),
        'reported_final_lss_below99':below,
        'diagnosis':'final_original_LSS_probability_below_0.99' if below else ''})
groups=[]
for s in A['case_summaries']:
    x=[r for r in rows if r['case_index']==s['case_index'] and r['arm']==s['arm']]
    groups.append({'case_index':s['case_index'],'arm':s['arm'],'registered':len(x),
        'reported_lss_below99_count':sum(r['reported_final_lss_below99'] for r in x),
        'all_reported_realP_ge99_count':sum(r['reported_real_probability']>=.99 for r in x),
        'all_mean_reported_realP':statistics.mean(r['reported_real_probability'] for r in x),
        'all_observed_mean_initialization_cost':statistics.mean(r['observed_initialization_best_cost'] for r in x),
        'all_observed_mean_raw_final_cost':statistics.mean(r['observed_raw_final_best_cost'] for r in x),
        'all_observed_mean_search_seconds':statistics.mean(r['observed_search_seconds'] for r in x),
        'all_observed_mean_initialization_seconds':statistics.mean(r['observed_initialization_seconds'] for r in x),
        'all_observed_egs_new_acceptances':sum(r['observed_egs_new_acceptances'] for r in x),
        'all_observed_egs_improvements':sum(r['observed_egs_improvements'] for r in x)})
report={'role':'observed diagnostic values only; independent validity and official cost statistics unchanged',
    'independent_audit_sha256':hashlib.sha256((H/'INDEPENDENT_AUDIT_STATISTICS.json').read_bytes()).hexdigest(),
    'runs':rows,'groups':groups}
(H/'OBSERVED_OUTPUT_DIAGNOSTICS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'groups':groups},ensure_ascii=False))

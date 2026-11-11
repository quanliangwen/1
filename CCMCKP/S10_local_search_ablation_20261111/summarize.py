"""Verify paired observations against original evidence, then aggregate them."""
from pathlib import Path
from collections import Counter
from statistics import mean, pstdev
import csv
import gzip
import hashlib
import json

T = Path(__file__).resolve().parent
B = T/'bundle'
D = T/'received'
reg = json.loads((B/'REGISTRATION.json').read_text())
bench = json.loads((B/'BENCHMARK_MANIFEST.json').read_text())
dispatch = json.loads((D/'TERMINAL.json').read_text())
cases = {c['index']: c for c in reg['cases']}
results = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def verify_trial(entry):
    key = (entry['arm'], entry['case'], entry['rep'])
    arm, case, rep = key
    p = D/'runs'/arm/f'case_{case:02}'/f'rep_{rep:02}'
    if not entry['completed']:
        failure = read_json(p/'FAILED.json') if (p/'FAILED.json').is_file() else None
        return dict(arm=arm, case_index=case, rep=rep, status='failed',
                    exit_code=entry['exit_code'], failure=failure)
    r = read_json(p/'RESULT.json')
    assert (r['arm'], r['case_index'], r['rep']) == key
    assert r['search_seed'] == reg['search_seeds'][rep-1]
    assert r['instance'] == cases[case]['instance'] and r['capacity'] == cases[case]['tmax']
    assert r['registration_sha256'] == sha(B/'REGISTRATION.json')
    assert r['S10_source_sha256'] == reg['S10_source_sha256']
    assert r['original_LSS_output_tail_AST_sha256'] == reg['original_LSS_output_tail_AST_sha256']
    assert r['extra_real_probability_hard_filter'] is False
    for e in r['evidence']:
        evidence = D/e['path']
        assert sha(evidence) == e['sha256'] and evidence.stat().st_size == e['bytes']
    with next((p/'result/Localsearch').glob('*_0.csv')).open(newline='') as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1 and int(rows[0]['Times']) == rep-1
    assert float(rows[0]['Cost']) == r['cost'] and json.loads(rows[0]['Solution']) == r['selection']
    meta = read_json(p/'S10_search.json.gz.run.json')
    assert meta['backend'] == reg['arms'][arm]['backend']
    assert meta['local_phases'] == reg['arms'][arm]['phases']
    assert meta['within_budget'] and meta['elapsed'] <= reg['search_seconds']
    for filename, digest in meta['input_sha256'].items():
        assert bench[r['instance']][filename] == digest
    assert not any(v.endswith('_dist.txt') for v in meta['opened_task_paths'])
    raw = json.loads(gzip.decompress((p/'S10_search.json.gz').read_bytes()))
    assert raw['selected']['cost'] == r['raw_best_cost']
    chosen = next(c for c in raw['candidate_shortlist'] if c['selection'] == r['selection'])
    cert = chosen['certificate']
    assert cert['accepted'] and 100*int(cert['lower_numerator']) >= 99*int(cert['denominator'])
    for phase in r['phase_records']:
        if phase['phase'] in ('local_pre','local_post'):
            assert phase['enabled'] == (r['local_phases'] in ('both',phase['phase'][6:]))
            if not phase['enabled']:
                assert phase['best_before'] == phase['best_after'] and phase['candidates_added'] == 0
    r['chosen_candidate_source'] = chosen['source']
    r['raw_pool_count'] = raw['raw_certified_pool_count']
    r['mip_calls'] = raw['models']
    r['mip_seconds'] = raw['model_seconds']
    return r


for entry in dispatch:
    key = (entry['arm'],entry['case'],entry['rep'])
    assert key not in results
    results[key] = verify_trial(entry)
assert set(results) == {(a,c,r) for a in reg['arms'] for c in cases for r in reg['repetitions']}

aggregates = []
for case, spec in cases.items():
    for arm in reg['arms']:
        r = [results[arm,case,rep] for rep in reg['repetitions']]
        ok = [x for x in r if x['status']=='completed']
        all_complete = len(ok) == len(r)
        phases = [p for x in ok for p in x['phase_records']]
        improvements = Counter(p['phase'] for p in phases if p['best_before'] is not None and
                               p['best_after'] is not None and p['best_after'] < p['best_before']-1e-8)
        aggregates.append(dict(case_index=case,instance=spec['instance'],capacity=spec['tmax'],arm=arm,
            completed=len(ok),registered=len(r),
            lss_avg=mean(x['cost'] for x in ok) if all_complete else None,
            lss_best=min(x['cost'] for x in ok) if all_complete else None,
            lss_std=pstdev(x['cost'] for x in ok) if all_complete else None,
            raw_avg=mean(x['raw_best_cost'] for x in ok) if all_complete else None,
            raw_best=min(x['raw_best_cost'] for x in ok) if all_complete else None,
            search_seconds=mean(x['S10_worker_search_seconds'] for x in ok) if all_complete else None,
            lss_running_time=mean(x['original_mainflow_search_seconds'] for x in ok) if all_complete else None,
            local_pre_improvements=improvements['local_pre'],local_post_improvements=improvements['local_post'],
            mitm_improving_stages=improvements['MITM'],
            local_post_executions=sum(p['phase']=='local_post' and p.get('enabled') for p in phases),
            mitm_stages_per_run=mean(sum(p['phase']=='MITM' for p in x['phase_records']) for x in ok) if ok else None,
            local_seconds=mean(sum(p['elapsed'] for p in x['phase_records'] if p['phase'].startswith('local_')) for x in ok) if ok else None,
            mip_seconds=mean(x['mip_seconds'] for x in ok) if ok else None,
            chosen_sources=dict(Counter(x['chosen_candidate_source'] for x in ok))))

contrasts = []
for candidate, control in [('H_BOTH','H_NONE'),('H_PRE','H_NONE'),('H_POST','H_NONE'),
                           ('H_BOTH','H_PRE'),('H_BOTH','H_POST'),('G_BOTH','G_NONE'),
                           ('G_BOTH','H_BOTH'),('G_NONE','H_NONE')]:
    paired = []
    for case in cases:
        for rep in reg['repetitions']:
            x,y = results[candidate,case,rep], results[control,case,rep]
            if x['status']==y['status']=='completed':
                paired.append(dict(case_index=case,rep=rep,seed=x['search_seed'],
                    lss_difference=x['cost']-y['cost'],raw_difference=x['raw_best_cost']-y['raw_best_cost'],
                    lss_relative_pct=100*(x['cost']-y['cost'])/y['cost'],
                    raw_relative_pct=100*(x['raw_best_cost']-y['raw_best_cost'])/y['raw_best_cost'],
                    search_time_difference=x['S10_worker_search_seconds']-y['S10_worker_search_seconds']))
    def counts(field):
        return {direction:sum(predicate(x[field]) for x in paired) for direction,predicate in
                [('lower',lambda v:v < -1e-8),('tie',lambda v:abs(v)<=1e-8),('higher',lambda v:v>1e-8)]}
    contrasts.append(dict(candidate=candidate,control=control,completed_pairs=len(paired),
        lss=counts('lss_difference'),raw=counts('raw_difference'),paired=paired))

summary = dict(registered=len(results),completed=sum(r['status']=='completed' for r in results.values()),
               paired_seeds=reg['search_seeds'],case_count=len(cases),arms=reg['arms'],
               aggregates=aggregates,contrasts=contrasts,all_available_evidence_verified=True)
(T/'ABLATION_SUMMARY.json').write_text(json.dumps(summary,indent=2))
(T/'TRIAL_RESULTS.json').write_text(json.dumps([results[k] for k in sorted(results)],indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in ('aggregates','contrasts')}))

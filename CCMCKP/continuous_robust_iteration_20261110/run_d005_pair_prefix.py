"""Four private original-native subprocesses, exact frozen-pool cost prefixes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import json, gzip, time
from isolated_original_lss import IsolatedOriginalLSS, sha, identity_key
from isolated_prefix_engine import describe, next_batch, account

H = Path(__file__).resolve().parent
D = H / 'research/D005_I016_pair_prefix'
reg = json.load(open(D / 'REGISTRATION.json'))
out = D / 'RESULT.json'
if out.exists() or (D / 'FINISHED').exists() or any((D / 'receipts').iterdir()):
    raise RuntimeError('Full-prefix study may already have run; do not repeat')

def identities():
    for name, digest in reg['source_sha256'].items():
        if sha(H / name) != digest:
            raise RuntimeError('Registered prefix/native source changed')
    for name, digest in reg['input_sha256'].items():
        if sha(H / name) != digest:
            raise RuntimeError('Frozen prefix/certificate/catalogue input changed')

identities()
catalogue = json.load(open(D / 'CATALOGUE.json'))
native = IsolatedOriginalLSS(H, D / 'receipts', catalogue)
outcomes = {}
for key, row in catalogue.items():
    value = json.load(open(H / row['path']))
    identity = {k: value[k] for k in ['instance', 'capacity', 'selection', 'seed', 'draws', 'event']}
    if identity_key(identity) != key:
        raise RuntimeError('Pinned catalogue identity changed')
    outcomes[key] = native.read_catalogue(key, identity)
pools = {}
for name, info in reg['pools'].items():
    data = json.loads(gzip.decompress((H / info['result_file']).read_bytes()))
    pool = []
    for row in data['candidate_shortlist']:
        identity = dict(instance=data['instance'], capacity=float(data['capacity']),
                        selection=row['selection'], seed=832273, draws=10000000, event='sum<=T')
        pool.append(dict(key=identity_key(identity), selection=row['selection'], cost=row['cost'], identity=identity))
    pools[name] = pool
started = time.monotonic()
new = {}
batches = []
controller_error = None
try:
    with ThreadPoolExecutor(max_workers=reg['workers']) as executor:
        while True:
            identities()
            batch = next_batch(pools, outcomes, reg['workers'])
            if not batch:
                break
            begin = time.monotonic()
            batch_number = len(batches) + 1
            (D / 'STATE.json').write_text(json.dumps(dict(stage='private_original_native_batch',
                batch=batch_number, tasks=[dict(key=r['key'], cost=r['cost']) for r in batch], time=time.time()), indent=2))
            futures = {executor.submit(native.evaluate_new, task, reg['watchdog_per_call']): task for task in batch}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                except Exception as exception:
                    result = dict(key=task['key'], passed=False, probability=None, seconds=0.,
                                  origin='private_attempt_setup_error', new_attempt=False,
                                  attempt_wall=0., receipt_path=None, receipt_sha256=None, error=str(exception))
                outcomes[task['key']] = result
                new[task['key']] = result
                with (D / 'ATTEMPTS.jsonl').open('a') as stream:
                    stream.write(json.dumps(dict(batch=batch_number, cost=task['cost'], **result)) + '\n')
            batches.append(dict(batch=batch_number, keys=[r['key'] for r in batch], wall=time.monotonic() - begin))
            progress = account(pools, outcomes, [k for k, r in new.items() if r['new_attempt']])
            (D / 'PROGRESS.json').write_text(json.dumps(dict(batch=batch_number,
                actual_wall=time.monotonic() - started, accounting=progress,
                private_new_receipts=len([r for r in new.values() if not r['error']]),
                errors=[dict(key=k, error=r['error']) for k, r in new.items() if r['error']]), indent=2))
            print(json.dumps(dict(batch=batch_number, wall=batches[-1]['wall'],
                new_attempts=len(new), pools={name: dict(complete=describe(pool, outcomes)['prefix_complete'],
                known_upper_cost=(describe(pool, outcomes)['known_feasible_upper'] or {}).get('cost')) for name, pool in pools.items()})), flush=True)
except Exception as exception:
    controller_error = str(exception)

accounting = account(pools, outcomes, [k for k, r in new.items() if r['new_attempt']])
required = set().union(*(set(r['required_keys']) for r in accounting['pools'].values()))
result = dict(scope=reg['scope'], registration_sha256=sha(D / 'REGISTRATION.json'),
              controller_error=controller_error, accounting=accounting, batches=batches,
              required_outcomes={key: outcomes[key] for key in sorted(required) if key in outcomes},
              private_new_outcomes=new, physical_new_original_MC_seconds=sum(r['seconds'] for r in new.values()),
              private_attempt_wall_sum=sum(r['attempt_wall'] for r in new.values()),
              actual_wall=time.monotonic() - started, all_new_outputs_private=True,
              no_optimizer_feedback=True, no30runstatistics=True)
result['private_log_keys'] = sorted(p.stem for p in (D / 'receipts').glob('*.log'))
result['private_receipt_keys'] = sorted(p.stem for p in (D / 'receipts').glob('*.json'))
result['unrecorded_private_attempt_keys'] = sorted(set(result['private_log_keys']) - set(new))
result['physical_attempt_logs'] = len(result['private_log_keys'])
with out.open('x') as stream:
    json.dump(result, stream, indent=2)
(D / 'FINISHED').write_text('all scheduled attempts terminal; inspect prefix completeness and failures\n')
(D / 'STATE.json').write_text(json.dumps(dict(stage='finished' if not controller_error else 'finished_with_controller_error',
    time=time.time(), all_prefixes_complete=accounting['all_prefixes_complete']), indent=2))
print(json.dumps(dict(controller_error=controller_error, all_prefixes_complete=accounting['all_prefixes_complete'],
    new_attempts=accounting['physical_new_attempts'], MC_seconds=result['physical_new_original_MC_seconds'], wall=result['actual_wall'])), flush=True)

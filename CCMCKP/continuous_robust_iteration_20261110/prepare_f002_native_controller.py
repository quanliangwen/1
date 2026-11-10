"""Clone completed prefix controller and isolation snapshot, no new MC or search."""
from pathlib import Path
import json,hashlib,ast
H=Path(__file__).resolve().parent;A=H/'artifact';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();reg=json.load(open(A/'research/D005_I016_pair_prefix/REGISTRATION.json'));post=json.load(open(A/'research/D005_I016_pair_prefix/POSTPROCESS_REGISTRATION.json'))
old=H/'run_d005_pair_prefix.py'
if sha(old)!=reg['source_sha256'][old.name]:raise RuntimeError('Previously completed generic controller changed')
text=old.read_text(encoding='utf8');text=text.replace("D005_I016_pair_prefix","F002_I016_formal_native")
needle="out = D / 'RESULT.json'"
assert text.count(needle)==1
text=text.replace(needle,needle+"\nif reg['search_attempts'] != 1200 or len(reg['pools']) + len(reg['excluded_attempts']) != 1200:\n    raise RuntimeError('All original1200 search attempts must remain in the formal ledger')")
needle="new_attempts=len(new), pools={name: dict(complete=describe(pool, outcomes)['prefix_complete'],\n                known_upper_cost=(describe(pool, outcomes)['known_feasible_upper'] or {}).get('cost')) for name, pool in pools.items()}))"
assert text.count(needle)==1
text=text.replace(needle,"new_attempts=len(new), native_pools=len(pools), complete_pools=sum(describe(pool, outcomes)['prefix_complete'] for pool in pools.values()), excluded_search_attempts=len(reg['excluded_attempts'])))")
needle="result['private_log_keys'] ="
assert text.count(needle)==1
text=text.replace(needle,"result.update(original_registered_search_attempts=1200, excluded_search_attempts=len(reg['excluded_attempts']), native_pool_count=len(pools), formal_statistics_pending_independent_audit=True)\n"+needle)
dest=H/'run_f002_native.py'
if dest.exists():raise RuntimeError('Never overwrite prepared formal controller')
ast.parse(text);dest.write_text(text,encoding='utf8')
old=H/'snapshot_d005_isolation.py'
if sha(old)!=post['drivers'][old.name]:raise RuntimeError('Previously independently exercised isolation source changed')
text=old.read_text(encoding='utf8').replace('D005_I016_pair_prefix','F002_I016_formal_native').replace('D005','F002')
dest=H/'snapshot_f002_native_isolation.py'
if dest.exists():raise RuntimeError('Never overwrite formal isolation driver')
ast.parse(text);dest.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,actual_native_registered=False,new_MC_calls=0,controller_policy='same completed four-worker batch/identity dedup/error handling, formal1200ledger accounting plus compact logs',controller_sha256=sha(H/'run_f002_native.py'),isolation_sha256=sha(dest))))

"""Posthoc value diagnostic only: no new proposals, source changes or native MC."""
from pathlib import Path
import json,gzip,hashlib
H=Path(__file__).resolve().parent;D=H/'research/third_group_repair_balanced_replay';out=D/'VALUE_DIAGNOSTIC.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No completed diagnostic overwrite')
a=json.load(open(D/'INDEPENDENT_REPLAY_AUDIT.json'));r=json.loads(gzip.decompress((D/'REPLAY_RESULT.json.gz').read_bytes()));old=json.load(open(H/'research/D004_I016_full_prefix/INDEPENDENT_FINAL_AUDIT.json'));prior=old['pools']['I016']['cost']
if not a['passed'] or a['result_sha256']!=sha(D/'REPLAY_RESULT.json.gz') or not old['passed']:raise RuntimeError('Actual independent own raw replay and original frozen-pool prefix proof required')
rows=sorted(r['accepted'],key=lambda x:(x['cost'],x['selection']));cheaper=[x for x in rows if x['cost']<prior-1e-9]
v=dict(scope=__doc__+'; compare133new raw-qualified members with independently known old frozen-pool joint minimum; no native qualification/cold/Avg claim',raw_members=len(rows),new_raw_cheapest=rows[0]['cost'] if rows else None,previous_own_pool_joint_minimum=prior,new_raw_members_below_previous_joint_minimum=len(cheaper),new_raw_members_at_or_above_previous_joint_minimum=len(rows)-len(cheaper),minimum_raw_lower=min((x['certificate']['lower'] for x in rows),default=None),cheaper_rows=[dict(selection=x['selection'],cost=x['cost'],raw_lower=x['certificate']['lower']) for x in cheaper],all_other_raw_rows_retained=True,new_MC_calls=0,result_sha256=sha(D/'REPLAY_RESULT.json.gz'),independent_replay_audit_sha256=sha(D/'INDEPENDENT_REPLAY_AUDIT.json'))
with out.open('x') as f:json.dump(v,f,indent=2)
print(json.dumps({k:x for k,x in v.items() if k!='cheaper_rows'}))

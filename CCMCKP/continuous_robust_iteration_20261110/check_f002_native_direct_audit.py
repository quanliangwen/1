"""Run new independent audit on actual completed6+8 development pools only."""
from pathlib import Path
import json,time,subprocess
from f002_native_direct_audit import audit,sha
H=Path(__file__).resolve().parent;D=H/'research/F002_native_audit_preflight';D.mkdir(exist_ok=True);out=D/'ACTUAL_COMPLETED_FIXTURE_CHECK.json'
if out.exists():raise RuntimeError('No completed-fixture preflight overwrite')
calls=[];old=subprocess.run
def forbidden(*a,**kw):calls.append(True);raise RuntimeError('No subprocess allowed in independent audit preflight')
subprocess.run=forbidden;rows=[]
try:
 for study,expected in [('D005_I016_pair_prefix',6),('D006_I016_breadth_prefix',8)]:
  actual=audit(H,'research/'+study);prior=json.load(open(H/'research'/study/'INDEPENDENT_FINAL_AUDIT.json'))
  if not actual['passed'] or not actual['integrity_passed'] or len(actual['pools'])!=expected or actual['physical_new_MC_attempts']!=prior['physical_new_MC_attempts'] or abs(actual['physical_new_original_MC_seconds']-prior['physical_new_original_MC_seconds'])>1e-8 or actual['speculative_extra_MC_keys']!=prior['speculative_extra_MC_keys']:raise RuntimeError('Completed actual native accounting mismatch')
  for key,v in actual['pools'].items():
   oldstate=prior['pools'][key]
   if any(v[n]!=oldstate[n] for n in ['cost','original_native_point','selected_key','prefix_calls','cheaper_rejected','source_seed','logical_original_MC_seconds']):raise RuntimeError('Completed actual original prefix differs')
  rows.append(dict(study=study,pools=expected,physical_new_MC_attempts=actual['physical_new_MC_attempts'],seconds=actual['seconds'],actual_result_sha256=actual['result_sha256'],prior_independent_audit_sha256=sha(H/'research'/study/'INDEPENDENT_FINAL_AUDIT.json'),all_selected_original_raw_recounted=True))
finally:subprocess.run=old
if calls:raise RuntimeError('Native subprocess called during preflight')
r=dict(passed=True,time=time.time(),scope=__doc__+'; complete14success-prefix/89physical fixture branches; NOT full1200 formal namespace or native-error branches',source_sha256=sha(H/'f002_native_direct_audit.py'),subprocess_calls=len(calls),new_MC_calls=0,formal_all1200_audit_claimed=False,rows=rows)
with out.open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))

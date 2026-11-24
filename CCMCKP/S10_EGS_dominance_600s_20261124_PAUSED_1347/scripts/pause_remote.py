from pathlib import Path
from datetime import datetime,timezone
import json,os,signal,time,hashlib
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_dominance_600s_20261124';assert Path.cwd()==B
read=lambda p:json.loads(p.read_text())
def cmd(pid):
 try:return [a for a in Path('/proc/%s/cmdline'%pid).read_bytes().split(b'\0') if a]
 except OSError:return []
def workers():
 out=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  args=cmd(int(p.name))
  if str(H/'bin/ccmckp_s10').encode() in args and any(a.startswith(str(H/'runs').encode()+b'/') for a in args):
   out.append({'pid':int(p.name),'pgid':os.getpgid(int(p.name)),'args':[a.decode(errors='replace') for a in args]})
 return out
start=datetime.now(timezone.utc).isoformat();before=read(H/'STATE.json')
pid=read(H/'LAUNCH.json')['pid'];controller_args=cmd(pid);signals=[]
if str(H/'controller.py').encode() in controller_args:
 os.kill(pid,signal.SIGTERM);signals.append({'pid':pid,'signal':'SIGTERM','target':'verified_current_controller'})
end=time.monotonic()+18
while time.monotonic()<end:
 if not workers() and str(H/'controller.py').encode() not in cmd(pid):break
 time.sleep(.25)
remaining=workers()
for w in remaining:
 assert w['pgid']==w['pid'],w
 os.killpg(w['pid'],signal.SIGKILL);signals.append({'pid':w['pid'],'signal':'SIGKILL','target':'verified_residual_worker_group'})
if remaining:time.sleep(.5)
after=read(H/'STATE.json');residual=workers();controller_live=str(H/'controller.py').encode() in cmd(pid)
P=read(H/'PROTOCOL.json');outcomes=[read(p) for p in (H/'outcomes').glob('*.json')]
registered={(a['name'],c['index'],r) for a in P['arms'] for c in P['cases'] for r in range(1,31)}
dispatched=[json.loads(s) for s in (H/'DISPATCH.jsonl').read_text().splitlines() if s]
dispatched_ids={x['identity'] for x in dispatched}
pending=['%s_i%02d_r%02d'%(a,i,r) for a,i,r in sorted(registered) if '%s_i%02d_r%02d'%(a,i,r) not in dispatched_ids]
data={'status':'PAUSED','requested_utc':start,'verified_utc':datetime.now(timezone.utc).isoformat(),
 'controller_pid':pid,'controller_live':controller_live,'remaining_workers':residual,'signals':signals,
 'state_before':before,'state_after':after,'terminal_records':len(outcomes),'never_started_count':len(pending),
 'never_started_identities':pending,'user_interrupted_identities':[o['identity'] for o in outcomes if o.get('termination_reason')=='requested_stop'],
 'prior_natural_nonzero_records':[{'identity':o['identity'],'rc':o['rc'],'reason':o.get('termination_reason')} for o in outcomes if o['rc']!=0 and o.get('termination_reason')!='requested_stop'],
 'no_restarts_or_retries':True,'do_not_treat_user_interruption_as_algorithm_failure':True,
 'protocol_sha256':hashlib.sha256((H/'PROTOCOL.json').read_bytes()).hexdigest()}
assert not residual and not controller_live,data
(H/'USER_PAUSE_RECEIPT.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
print(json.dumps(data,ensure_ascii=False),flush=True)

"""One P145 A-star final-output original Map02 RED/BLUE pilot, original scientific runner and resource gate."""
from pathlib import Path
import importlib.util,json,fcntl,os,time,traceback,hashlib
R=Path('/home/junhao/quan/parallel_test_solver/match');H=R/'solver_study/framework_screen_20261016/best87_independent_20261025';F=Path(__file__).resolve().parent
original=H/'P41_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py'
spec=importlib.util.spec_from_file_location('original_frozen_runner',original);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
b.F=F;b.D=json.loads((F/'PREDECLARATION.json').read_text());b.NAMES=b.D['selection'];b.BLUE=b.D['blue_binding'];b.WBLUE=Path(b.BLUE['blue_workspace'])
b.STATE.update(phase=F.name,completed=[],decisions=[],max_native_rounds=2,automatic_five=False)
original_state=b.state
def state(status,**kw):original_state('RUNNING_SINGLE_MAP_DIAGNOSTIC'if status=='RUNNING_FIVE_MAPS'else status,**kw)
b.state=state
def summarize():b.save(F/'RESULT.json',dict(b.STATE,automatic_five=False,ranking_promoted=False,scope='One originalMap02 pair, never a five-map mean.'))
b.summarize=summarize
def first_review(G):
 start=time.monotonic();p=G/'CLIENT_FIRST_RAW_REVIEW.json'
 while not p.exists():
  if b.stop_requested():raise RuntimeError('Human stop during first Windows review')
  if time.monotonic()-start>7200:raise TimeoutError('First Windows byte review not received; no retry')
  state('AWAIT_FIRST_WINDOWS_REVIEW',group=G.name);time.sleep(5)
 proof=json.loads(p.read_text());raw=json.loads((G/'RAW_ARCHIVE_RECEIPT.json').read_text())
 assert proof['status']=='PASS'and proof['archive_sha256']==raw['sha256']
def mechanism(item):
 import numpy as np,cv2
 G=F/(item['version']+'_'+item['cohort']);matrix=json.loads((G/'RESULT.json').read_text());row=matrix['jobs']['Map02']['rounds'][0]
 result=Path(json.loads((G/'LAUNCH.json').read_text())['result']);events=[]
 for line in(result/'Map02_red/console.log').read_text(errors='replace').splitlines():
  if '[FREE_SUPPORT_OUTPUT] 'in line:events.append(json.loads(line.split('[FREE_SUPPORT_OUTPUT] ',1)[1]))
 red=json.loads((result/'Map02_red/summary.json').read_text())['rounds'][0]
 binary=(cv2.imread(str(result/'Map02_red/round1_red_submitted.png'),cv2.IMREAD_UNCHANGED)>0).astype(np.uint8)
 digest=hashlib.sha256(binary.tobytes()).hexdigest()
 selected=[e for e in events if e['sha256']==digest and e['shape']==list(binary.shape)and e['dtype']=='uint8']
 active=[e for e in selected if e['audit'].get('status')=='COMPLETE_FREE_DIRECTION_REFERENCE'and e['audit'].get('erased_pixels',0)>0 and e['audit'].get('parent_preserved')and e['audit'].get('raw_positive_preserved')and e['audit'].get('seconds',999)<=.5]
 p=row['phase'];gate=b.D['small_test_gate']
 checks=dict(actual_active_completion_on_submitted_image=bool(active),submitted_image_bound=bool(selected),
  all10=row['placed']==row['expected']==10,no_RED_hit=not red['max_walltime_reached'],no_BLUE_hit=not row['blue']['max_walltime_reached'],
  map_at_least96=p['score_map']>=gate['minimum_map'],wall_at_least80=p['score_wall']>=gate['minimum_wall'],
  time100=p['score_time']==100,full_at_least75=row['full_score']>=gate['minimum_full'])
 out=dict(version=item['version'],map='Map02',score=row['full_score'],phase=p,placed=row['placed'],expected=row['expected'],
  red_wall_hit=red['max_walltime_reached'],blue_wall_hit=row['blue']['max_walltime_reached'],rule_event_count=len(active),
  all_audit_events=events,selected_audit_events=selected,mechanism_and_score_checks=checks,pass_gate=all(checks.values()),
  image_sha256=digest,automatic_five=False,red_walltime=row['red_walltime'],red_steps=row['red_steps'],
  scope='One original-condition unseeded pilot, actual completion evidence and submitted score only; no original-grid counterfactual/PJ01 control rerun/five mean or ranking promotion.')
 b.save(G/'MECHANISM_REVIEW.json',out);return out

def main():
 lease=(F/'coordinator.lock').open('a+');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert not(F/'RUN_ONCE.json').exists();b.save(F/'RUN_ONCE.json',dict(utc=b.utc(),pid=os.getpid(),starttime_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],driver_sha256=b.sha(__file__),predeclaration_sha256=b.sha(F/'PREDECLARATION.json')))
 b.STATE['started_utc']=b.utc();b.validate_frozen();summarize()
 try:
  for item in b.D['schedule']:
   if b.stop_requested():state('STOPPED_BEFORE_NEXT_GROUP');summarize();return
   if not b.run_cohort(item):state('STOPPED_BEFORE_NATIVE_START');summarize();return
   G=F/(item['version']+'_'+item['cohort']);first_review(G);b.STATE['decisions'].append(mechanism(item));summarize()
  state('COMPLETE_FINITE_STAGED_CAMPAIGN',current=None);summarize()
 except Exception:
  b.save(F/'FIRST_ERROR.json',dict(utc=b.utc(),traceback=traceback.format_exc(),first_native_failure=b.STATE['first_native_failure'],no_retry=True));state('STOPPED_FIRST_ERROR_NO_RETRY');summarize();raise
if __name__=='__main__':main()

"""One requested P48 A* all-five RED/BLUE group, original scientific runner and resource gate."""
from pathlib import Path
import importlib.util,json,fcntl,os,time,traceback,hashlib
R=Path('/home/junhao/quan/parallel_test_solver/match');H=R/'solver_study/framework_screen_20261016/best87_independent_20261025';F=Path(__file__).resolve().parent
original=H/'P41_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py'
spec=importlib.util.spec_from_file_location('original_frozen_runner',original);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
b.F=F;b.D=json.loads((F/'PREDECLARATION.json').read_text());b.NAMES=b.D['selection'];b.BLUE=b.D['blue_binding'];b.WBLUE=Path(b.BLUE['blue_workspace'])
b.STATE.update(phase=F.name,completed=[],decisions=[],max_native_rounds=10,automatic_five=False)
original_state=b.state
def state(status,**kw):original_state(status,**kw)
b.state=state
def summarize():b.save(F/'RESULT.json',dict(b.STATE,automatic_five=False,ranking_promoted=False,scope='One requested coverage-guarded corner placement group; no control rerun, retry, further iteration or promotion.'))
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
 import numpy as np,cv2,statistics
 G=F/(item['version']+'_'+item['cohort']);matrix=json.loads((G/'RESULT.json').read_text())
 result=Path(json.loads((G/'LAUNCH.json').read_text())['result']);rows=[]
 for name in b.D['maps']:
  row=matrix['jobs'][name]['rounds'][0];events=[]
  for line in(result/(name+'_red')/'console.log').read_text(errors='replace').splitlines():
   if '[FRESH_OPPORTUNITY] 'in line:events.append(json.loads(line.split('[FRESH_OPPORTUNITY] ',1)[1]))
  red=json.loads((result/(name+'_red')/'summary.json').read_text())['rounds'][0]
  actual=[e for e in events if e['kind']=='ACTUAL_LOCAL_MODEL_REFRESH']
  binary=(cv2.imread(str(result/(name+'_red')/'round1_red_submitted.png'),cv2.IMREAD_UNCHANGED)>0).astype(np.uint8)
  digest=hashlib.sha256(binary.tobytes()).hexdigest()
  bound=any(e['kind']=='SUBMIT_IMAGE'and e['sha256']==digest and e['shape']==list(binary.shape)and e['dtype']=='uint8'for e in events)
  clusters=[];commits=[];plan_chain=[]
  for line in(result/(name+'_red')/'console.log').read_text(errors='replace').splitlines():
   if '[CORNER_CLUSTER] 'in line:clusters.append(json.loads(line.split('[CORNER_CLUSTER] ',1)[1]))
   if '[CORNER_COMMIT] 'in line:commits.append(json.loads(line.split('[CORNER_COMMIT] ',1)[1]))
   if '[CORNER_PLAN_CHAIN] 'in line:plan_chain.append(json.loads(line.split('[CORNER_PLAN_CHAIN] ',1)[1]))
  actual_bombs=json.loads((result/(name+'_red')/'round1_bombs.json').read_text())['bombs']
  accepted=[e for e in clusters if e.get('accepted')]
  concentration=[]
  for e in accepted:
   anchor=np.asarray(e['anchor'],float);radius=float(e['radius'])
   distances=[float(np.linalg.norm(np.array([p['x'],p['y']])-anchor))for p in actual_bombs]
   concentration.append(dict(corner=e['corner'],anchor=e['anchor'],radius=radius,actual_strict=sum(d<=radius for d in distances),actual_with12=sum(d<=radius+12 for d in distances)))
  rows.append(dict(map=name,full=row['full_score'],phase=row['phase'],placed=row['placed'],expected=row['expected'],red_steps=row['red_steps'],red_walltime=row['red_walltime'],
   red_wallhit=red['max_walltime_reached'],blue_wallhit=row['blue']['max_walltime_reached'],blue_public=row['blue'],layout_contribution=row['layout_contribution'],cluster_calls=len(clusters),cluster_accepted=len(accepted),cluster_commits=len(commits),cluster_model_audits=clusters,issued_plan_chain=plan_chain,concentration=concentration,max_actual_cluster=max((e['actual_strict']for e in concentration),default=0),max_actual_cluster_with12=max((e['actual_with12']for e in concentration),default=0),actual_model_refreshes=len(actual),submitted_image_bound=bound,astar_calls=sum(e.get('astar_stats',{}).get('calls',0)for e in events if e['kind']=='SUBMIT_IMAGE'),astar_expanded=sum(e.get('astar_stats',{}).get('expanded',0)for e in events if e['kind']=='SUBMIT_IMAGE'),
   recorded_refreshes_fresh=all(e['age_before']>=120 and e['age_after']==0 and e['stamp_after']==e['step']for e in actual),own_audit_events=events))
 valid=all(not r['red_wallhit']and not r['blue_wallhit']for r in rows)
 integrity=all(r['submitted_image_bound']and r['recorded_refreshes_fresh']and r['astar_calls']>0 for r in rows)
 mean=statistics.mean(r['full']for r in rows);placed=sum(r['placed']for r in rows)
 out=dict(status='REVIEWED_COMPLETE_FIVE'if valid and integrity else'FIVE_WITH_FAILURE_OR_AUDIT_LIMITATION',rows=rows,mean=mean,placed=placed,expected=50,evaluation_valid=valid,
  audit_integrity=integrity,completion_complete=placed==50,promising=valid and integrity and placed==50 and mean>=80 and mean>b.D['retained_P48_mean'],
  automatic_B=False,ranking_promoted=False,independent_random_observation=True)
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

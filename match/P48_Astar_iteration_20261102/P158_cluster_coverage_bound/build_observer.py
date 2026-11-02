from pathlib import Path
import hashlib,json
F=Path(__file__).resolve().parent;P=F.parent/'P157_inner_corner_free_quadrants';F.mkdir(exist_ok=True)
original=(P/'check_sdk_inner.py').read_text()
insertion='''
# Observation only: capture actual local frame arrays at the first 10-slot call.
# Do not invoke geometry/value helpers an extra time or mutate their caches.
import swarm_rescue.solutions.team_coverage_lns as supplier_module
raw_corner=supplier_module.corner_cluster_layout
model_snapshots=[]
def capture_profile(frame,event,arg):
 if event!='return' or frame.f_code is not raw_corner.__code__ or model_snapshots:return
 local=frame.f_locals
 if local.get('total')!=10 or 'ranked'not in local:return
 export={}
 for name in ['allowed','walkable','values','residual','xx','yy']:
  if name in local:export[name]=np.asarray(local[name]).tolist()
 export.update(baseline=float(local['baseline']),baseline_points=[np.asarray(p).tolist()for p in local['baseline_points']],radius=float(local['radius']),cell=float(local['pm'].CELL),initial_total=local['state']['initial_total'],target_total=local['target_total'],step=int(local['memory'].step),owner=int(local['memory'].identifier),corners=[dict(rank=float(x[0]),pivot=[x[1],x[2]],anchor=np.asarray(x[3]).tolist(),region=np.asarray(x[4]).tolist())for x in local['ranked']])
 model_snapshots.append(export)
def capture_corner(*args,**kwargs):
 if model_snapshots:return raw_corner(*args,**kwargs)
 previous=sys.getprofile();sys.setprofile(capture_profile)
 try:return raw_corner(*args,**kwargs)
 finally:sys.setprofile(previous)
supplier_module.corner_cluster_layout=capture_corner
'''
needle='from swarm_rescue.solutions.my_drone_eval import MyDroneEval as Original\n'
assert original.count(needle)==1
new=original.replace(needle,needle+insertion)
needle=" dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\\n');print("
assert new.count(needle)==1
new=new.replace(needle," out['model_snapshots']=model_snapshots\n"+needle)
(F/'check_sdk_observer.py').write_text(new,encoding='utf-8')
pre=json.loads((P/'PREDECLARATION_FIRST.json').read_text());pre.update(SDK_arms=['P157'],purpose='Read-only model snapshot; require all output rows identity with retained P157, no new performance qualification',SDK_script_sha256=hashlib.sha256((F/'check_sdk_observer.py').read_bytes()).hexdigest(),expected_result=str(P/'P157_SDK_FIRST.json'),expected_result_sha256=hashlib.sha256((P/'P157_SDK_FIRST.json').read_bytes()).hexdigest(),source_workspace_stage='P157_inner_corner_free_quadrants_20261102',candidate_source_changed=False,automatic_five=False,automatic_native=False)
(F/'PREDECLARATION_FIRST.json').write_text(json.dumps(pre,indent=2)+'\n')
runner=(P/'run_small.py').read_text().replace('P157_inner_corner_free_quadrants_20261102','P158_cluster_coverage_bound_20261102')
start=runner.index(" subprocess.run(['scp'");end=runner.index(" src=Path(",start)
runner=runner[:start]+''' subprocess.run(['scp','-q',str(F/'check_sdk_observer.py'),'junhao@10.112.162.60:'+D+'/'],check=True,timeout=45)
 keep('WORKSPACE_BINDING_FIRST',remote("from pathlib import Path\\nimport shutil\\ns=Path("+repr(R+"/solver_study/framework_screen_20261016/best87_independent_20261025/P157_inner_corner_free_quadrants_20261102/WORKSPACE_READY.json")+")\\nd=Path("+repr(D+"/WORKSPACE_READY.json")+")\\nassert not d.exists()\\nshutil.copyfile(s,d)\\n"))
''' +runner[end:]
runner=runner.replace("F/'check_sdk_inner.py'","F/'check_sdk_observer.py'").replace("D+'/check_sdk_inner.py'","D+'/check_sdk_observer.py'")
start=runner.index(" a=read(F.parent/");end=runner.index("if __name__=='__main__':",start)
runner=runner[:start]+''' expected=read(Path(pre['expected_result']));observed=read(F/'P157_SDK_FIRST.json')
 checks=dict(rows_identical=expected['rows']==observed['rows'],scores_identical=expected['scores']==observed['scores'],actual_bombs_identical=expected['actual_bombs']==observed['actual_bombs'],source_identical=expected['source_sha256']==observed['source_sha256'],SDK_identical=expected['SDK_sha256']==observed['SDK_sha256'],submission_identical=expected['submitted']==observed['submitted'],first_actual_model_captured=len(observed.get('model_snapshots',[]))==1)
 result=dict(status='PASS_READONLY_OBSERVATION_IDENTITY'if all(checks.values())else'STOP_READONLY_IDENTITY_MISMATCH',checks=checks,physics_steps=observed['physics_steps'],new_native_rounds=0,new_performance_score=False,snapshots=observed.get('model_snapshots',[]))
 save('RESULT_FIRST.json',result);save('STATUS.json',dict(status=result['status'],utc=utc()),False)
 print(json.dumps(dict(status=result['status'],checks=checks)))
''' +runner[end:]
(F/'run_observer.py').write_text(runner,encoding='utf-8')
print('Read-only observer and finite runner prepared; no controller source changed')

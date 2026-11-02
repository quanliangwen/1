from pathlib import Path
import ast
import datetime
import hashlib
import json
import os
import subprocess
import time
import traceback

F=Path(__file__).resolve().parent
R='/home/junhao/quan/parallel_test_solver/match'
D=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P149_Astar_ready_waiting_20261102'
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60']
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def write(name,data,first=True):
    p=F/name
    if first:assert not p.exists(),p
    p.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())

def remote(code):
    return subprocess.run(SSH+[R+'/.venv/bin/python','-'],input=code.encode(),capture_output=True,timeout=60)

def keep(name,result):
    dest=F/(name+'.capture.txt')
    assert not dest.exists()
    dest.write_bytes(result.stdout+result.stderr)
    print(result.stdout.decode(errors='replace')[-900:],flush=True)
    if result.returncode:raise RuntimeError('First error preserved: '+name)

def main():
    assert not(F/'STARTED_FIRST.json').exists()
    pre=load(F/'PREDECLARATION_FIRST.json')
    assert load(F/'MECHANISM_PREFLIGHT_FIRST.json')['status']=='PASS_NO_EXACT_HISTORICAL_SOURCE_MATCH'
    binding=load(F/'LAUNCH_BINDING_FIRST.json')
    assert all(hashlib.sha256((F/name).read_bytes()).hexdigest()==expected for name,expected in binding['script_sha256'].items())
    assert hashlib.sha256((F/'check_sdk_ready_waiting.py').read_bytes()).hexdigest()==pre['code_sha256']
    guard=Path('E:/codex/UAV_rules_astar_restart_20261030/R154_scoped_serial_guard_20261101/check_scoped_serial.py').read_text()
    keep('SERIAL_FIRST',remote(guard))
    write('STARTED_FIRST.json',dict(utc=utc(),pid=os.getpid(),maximum_hours=14,native_rounds=0))
    keep('MKDIR_FIRST',remote('from pathlib import Path\np=Path('+repr(D)+')\nassert not p.exists()\np.mkdir()\n'))
    for p in [F/'check_sdk_ready_waiting.py',F/'BASE_WORKSPACE.json',F/'candidate_project',F/'CANDIDATE_MANIFEST_FIRST.json',F/'prepare_workspace.py',F/'PREDECLARATION_FIRST.json',Path('E:/codex/UAV_rules_astar_restart_20261030/run_sdk_captured.py')]:
        subprocess.run(['scp','-q','-r',str(p),'junhao@10.112.162.60:'+D+'/'],check=True,timeout=45)
    keep('WORKSPACE_FIRST',subprocess.run(SSH+[R+'/.venv/bin/python',D+'/prepare_workspace.py'],capture_output=True,timeout=120))
    src=Path('E:/codex/PJ01_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py').read_text()
    funcs='\n'.join(ast.get_source_segment(src,n) for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name in ['cpu_sample','resource'])
    resource_code='from pathlib import Path\nimport os,time,shutil,json,datetime\nR=Path('+repr(R)+')\nD=json.loads((R/"solver_study/framework_screen_20261016/best87_independent_20261025/P37_phase_five_comparison_20261101/PREDECLARATION.json").read_text())\ndef utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()\n'+funcs+'\nprint(json.dumps(resource()))\n'
    deadline=time.monotonic()+14*3600
    consecutive=[]
    i=0
    while time.monotonic()<deadline:
        if(F/'STOP_REQUESTED').exists():raise RuntimeError('Human stop')
        i+=1
        response=remote(resource_code)
        keep('CAPACITY_'+str(i)+'_FIRST',response)
        row=json.loads(response.stdout)
        consecutive=consecutive+[row] if row['clean'] else []
        write('STATUS.json',dict(utc=utc(),status='WAITING_ORIGINAL_CAPACITY',resource=row),False)
        if len(consecutive)>=2:break
        time.sleep(60)
    else:raise TimeoutError('Finite 14h original capacity wait')
    write('RESOURCE_TWO_SAMPLE_FIRST.json',consecutive)
    parent=Path(pre['parent_result'])
    assert hashlib.sha256(parent.read_bytes()).hexdigest()==pre['parent_result_sha256']
    assert hashlib.sha256((F/'CANDIDATE_MANIFEST_FIRST.json').read_bytes()).hexdigest()==pre['manifest_sha256']
    if(F/'STOP_REQUESTED').exists():raise RuntimeError('Human stop before joint waiting rule')
    label='READY_WAITING_FIRST'
    keep(label+'_SERIAL',remote(guard))
    write('STATUS.json',dict(utc=utc(),status='RUNNING_ASTARA_JOINT_WAITING_AUTHOR_SDK',native_rounds=0),False)
    cmd=SSH+[R+'/.venv/bin/python',D+'/run_sdk_captured.py',D+'/check_sdk_ready_waiting.py',label,'P149','cross_sdk','1000','.05','OFF']
    keep(label,subprocess.run(cmd,capture_output=True,timeout=900))
    subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+label+'.json',str(F/(label+'.json'))],check=True,timeout=45)
    a=load(parent);b=load(F/(label+'.json'))
    original=a['coverage_evaluation'];candidate=b['coverage_evaluation']
    routes=[e for e in b['waiting_events']if e['kind']=='ROUTE_ACCEPTED']
    arrivals=[e for e in b['waiting_events']if e['kind']=='ARRIVED']
    first=min((e['step']for e in routes),default=len(a['rows'])+1)
    health_a=[min(r['health'][i]for r in a['rows'])for i in range(5)]
    health_b=[min(r['health'][i]for r in b['rows'])for i in range(5)]
    physical=[]
    for e in arrivals:
        window=[r for r in b['rows']if e['epoch']<=r['step']<=e['epoch']+72 and r['inventory'][e['owner']]==0]
        best=min((sum((r['positions'][e['owner']][k]-e['target'][k])**2 for k in range(2))**.5 for r in window),default=float('inf'))
        physical.append(dict(owner=e['owner'],step=e['step'],epoch=e['epoch'],target=e['target'],minimum_public_physical_error=best))
    owners={e['owner']for e in physical if e['minimum_public_physical_error']<=20.}
    submit_credit_a=a['submission_records'][0]['breakdown']['credit']if a['submission_records']else None
    submit_credit_b=b['submission_records'][0]['breakdown']['credit']if b['submission_records']else None
    checks=dict(original_nonhealth_sdk_checks=all(v for k,v in b['checks'].items()if k!='health_unchanged'),
                no_added_damage=all(x>=y for x,y in zip(health_b,health_a)),
                identical_prefix_before_first_waiting_route=b['rows'][:first-1]==a['rows'][:first-1],
                two_empty_owners_really_arrived=len(owners)>=2,
                all10=candidate['actual_bomb_count']==10 and b['rows'][-1]['inventory']==[0]*5,
                actual_submitted_map_nonregress=candidate['actual_submitted_map']is not None and candidate['actual_submitted_map']>=original['actual_submitted_map'],
                actual_surface_credit_nonregress=submit_credit_b is not None and submit_credit_b>=submit_credit_a,
                mean5_raw_map_nonregress=sum(e['score']for e in b['map_results'])>=sum(e['score']for e in a['map_results']),
                time_nonregress=candidate['score_time']>=original['score_time'],
                controllable_subtotal_gain=candidate['controllable_subtotal']is not None and candidate['controllable_subtotal']>=original['controllable_subtotal']+.25)
    result=dict(status='PASS_ASTARA_JOINT_WAITING_AUTHOR_MECHANISM'if all(checks.values())else'STOP_FIRST_JOINT_WAITING_MECHANISM_GATE',
                checks=checks,physics_steps=b['physics_steps'],parent_steps=a['physics_steps'],
                baseline=original,candidate=candidate,parent_health_min=health_a,candidate_health_min=health_b,
                waiting_events=b['waiting_events'],physical_arrival_review=physical,waiting_owners_actually_arrived=sorted(owners),
                first_waiting_route_step=first if routes else None,raw_rows_identical=a['rows']==b['rows'],
                parent_raw5_maps=a['map_results'],candidate_raw5_maps=b['map_results'],
                sdk_loop_wall_seconds=b['wall_seconds'],native_rounds=0,automatic_native=False,automatic_five=False,
                limits=['One authored scenario, not official Map02 inventory-loss reproduction or a five-map mean.',
                        'Terminal joint graph check is not collision/consensus safety proof.',
                        'Known parent collision is not repaired or silently reclassified as health-safe.'])
    write('RESULT_FIRST.json',result)
    write('STATUS.json',dict(utc=utc(),status=result['status'],native_rounds=0),False)
    print(json.dumps(dict(status=result['status'],checks=checks,physics_steps=b['physics_steps'],score=candidate,native_rounds=0),ensure_ascii=False),flush=True)

if __name__=='__main__':
    try:main()
    except Exception:
        write('FIRST_ERROR.json',dict(utc=utc(),traceback=traceback.format_exc(),no_automatic_retry=True))
        write('STATUS.json',dict(utc=utc(),status='STOP_FIRST_DIAGNOSTIC_ERROR'),False)
        raise

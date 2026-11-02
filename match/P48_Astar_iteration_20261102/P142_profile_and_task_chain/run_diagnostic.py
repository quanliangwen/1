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
D=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P142_Astar_profile_and_task_chain_20261102'
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
    assert hashlib.sha256((F/'check_sdk_astar_profile.py').read_bytes()).hexdigest()==pre['code_sha256']
    guard=Path('E:/codex/UAV_rules_astar_restart_20261030/R154_scoped_serial_guard_20261101/check_scoped_serial.py').read_text()
    keep('SERIAL_FIRST',remote(guard))
    write('STARTED_FIRST.json',dict(utc=utc(),pid=os.getpid(),maximum_hours=14,native_rounds=0))
    keep('MKDIR_FIRST',remote('from pathlib import Path\np=Path('+repr(D)+')\nassert not p.exists()\np.mkdir()\n'))
    for p in [F/'check_sdk_astar_profile.py',F/'WORKSPACE_READY.json',F/'PREDECLARATION_FIRST.json',Path('E:/codex/UAV_rules_astar_restart_20261030/run_sdk_captured.py')]:
        subprocess.run(['scp','-q',str(p),'junhao@10.112.162.60:'+D+'/'],check=True,timeout=45)
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
    arms=[]
    for mode in ['OFF','ON']:
        if(F/'STOP_REQUESTED').exists():raise RuntimeError('Human stop before arm')
        label='BASELINE_FIRST' if mode=='OFF' else 'PROFILE_FIRST'
        keep(label+'_SERIAL',remote(guard))
        write('STATUS.json',dict(utc=utc(),status='RUNNING_AUTHORED_SDK_DIAGNOSTIC',current=label,native_rounds=0),False)
        cmd=SSH+[R+'/.venv/bin/python',D+'/run_sdk_captured.py',D+'/check_sdk_astar_profile.py',label,'P48_ASTAR','cross_sdk','800','.05',mode]
        keep(label,subprocess.run(cmd,capture_output=True,timeout=900))
        subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+label+'.json',str(F/(label+'.json'))],check=True,timeout=45)
        arm=load(F/(label+'.json'))
        arms.append(arm)
        if not all(arm['checks'].values()):
            write('RESULT_FIRST.json',dict(status='STOP_FIRST_ORIGINAL_SDK_CHECK',mode=mode,checks=arm['checks'],native_rounds=0,automatic_retry=False))
            write('STATUS.json',dict(utc=utc(),status='STOP_FIRST_ORIGINAL_SDK_CHECK'),False)
            return
    a,b=arms
    checks=dict(original_checks=all(a['checks'].values())and all(b['checks'].values()),
                frame_rows_identical=a['rows']==b['rows'],
                maps_identical=a['map_results']==b['map_results'],
                submission_identity=[(e['owner'],e['step'],e['output_sha256'])for e in a['submission_records']]==[(e['owner'],e['step'],e['output_sha256'])for e in b['submission_records']],
                task_chain_identical=a['route_details']==b['route_details'],
                gate_chain_identical=a['gate_events']==b['gate_events'],
                profile_available=bool(b['profile_rows']))
    profile=b['profile_rows']
    solution=[r for r in profile if '/swarm_rescue/solutions/' in r['file']]
    result=dict(status='PASS_READ_ONLY_PROFILE_IDENTITY'if all(checks.values())else'STOP_FIRST_OBSERVER_MISMATCH',checks=checks,
                physics_steps=a['physics_steps'],baseline_wall_seconds=a['wall_seconds'],profile_wall_seconds=b['wall_seconds'],
                baseline_coverage=a['coverage_evaluation'],top_exclusive_solution_functions=solution[:25],
                top_inclusive_solution_functions=sorted(solution,key=lambda r:r['cumulative_seconds'],reverse=True)[:25],
                task_events=len(b['route_details']),profile_is_instrumented_not_production_timing=True,
                native_rounds=0,automatic_native=False,automatic_five=False,
                limitation='Authored arena only; no official Map04 reproduction. Nested inclusive timings must not be summed.')
    write('RESULT_FIRST.json',result)
    write('STATUS.json',dict(utc=utc(),status=result['status'],native_rounds=0),False)
    print(json.dumps(dict(status=result['status'],checks=checks,steps=result['physics_steps'],top=solution[:5])),flush=True)

if __name__=='__main__':
    try:main()
    except Exception:
        write('FIRST_ERROR.json',dict(utc=utc(),traceback=traceback.format_exc(),no_automatic_retry=True))
        write('STATUS.json',dict(utc=utc(),status='STOP_FIRST_DIAGNOSTIC_ERROR'),False)
        raise

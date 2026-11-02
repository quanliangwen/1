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
D=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P145_Astar_final_output_rule_20261102'
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
    assert hashlib.sha256((F/'check_sdk_output_rule.py').read_bytes()).hexdigest()==pre['code_sha256']
    guard=Path('E:/codex/UAV_rules_astar_restart_20261030/R154_scoped_serial_guard_20261101/check_scoped_serial.py').read_text()
    keep('SERIAL_FIRST',remote(guard))
    write('STARTED_FIRST.json',dict(utc=utc(),pid=os.getpid(),maximum_hours=14,native_rounds=0))
    keep('MKDIR_FIRST',remote('from pathlib import Path\np=Path('+repr(D)+')\nassert not p.exists()\np.mkdir()\n'))
    for p in [F/'check_sdk_output_rule.py',F/'BASE_WORKSPACE.json',F/'candidate_project',F/'CANDIDATE_MANIFEST_FIRST.json',F/'prepare_workspace.py',F/'PREDECLARATION_FIRST.json',Path('E:/codex/UAV_rules_astar_restart_20261030/run_sdk_captured.py')]:
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
    if(F/'STOP_REQUESTED').exists():raise RuntimeError('Human stop before output rule')
    label='CROSS_OUTPUT_FIRST'
    keep(label+'_SERIAL',remote(guard))
    write('STATUS.json',dict(utc=utc(),status='RUNNING_ASTARA_SINGLE_OUTPUT_RULE',native_rounds=0),False)
    cmd=SSH+[R+'/.venv/bin/python',D+'/run_sdk_captured.py',D+'/check_sdk_output_rule.py',label,'P145','cross_sdk','800','.05','OFF']
    keep(label,subprocess.run(cmd,capture_output=True,timeout=900))
    subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+label+'.json',str(F/(label+'.json'))],check=True,timeout=45)
    a=load(parent);b=load(F/(label+'.json'))
    original=a['coverage_evaluation'];candidate=b['coverage_evaluation']
    actual=b['submission_records'][0] if b['submission_records'] else None
    audit={} if actual is None else actual['diagnostics']
    checks=dict(frame_rows_identical=a['rows']==b['rows'],
                original_checks_identical=a['checks']==b['checks'],
                all10=candidate['actual_bomb_count']==10 and b['rows'][-1]['inventory']==[0]*5,
                no_added_health_damage=all(x['health']==y['health']for x,y in zip(a['rows'],b['rows']))and len(a['rows'])==len(b['rows']),
                finite_sdk_callback_loop=all(v for k,v in b['checks'].items()if k!='health_unchanged'),
                raw_maps_identical=a['map_results']==b['map_results'],
                original_submission_inputs_identical=[(e['owner'],e['step'],e['original_sha256'])for e in a['submission_records']]==[(e['owner'],e['step'],e['original_sha256'])for e in b['submission_records']],
                task_chain_identical=a['route_details']==b['route_details'],
                gate_chain_identical=a['gate_events']==b['gate_events'],
                actual_map_gain=candidate['actual_submitted_map'] is not None and candidate['actual_submitted_map']>=original['actual_submitted_map']+.25,
                all_five_maps_nonregress=all(new['score']>=old['score']for old,new in zip(a['map_results'],b['filtered_map_results'])),
                all_five_surface_credit_nonregress=all(new['breakdown']['credit']>=old['breakdown']['credit']for old,new in zip(a['map_results'],b['filtered_map_results'])),
                actual_complete=bool(audit.get('status')=='COMPLETE_FREE_DIRECTION_REFERENCE'),
                actual_erase=bool(audit.get('erased_pixels',0)>0),
                actual_protected=bool(audit.get('parent_preserved')and audit.get('raw_positive_preserved')),
                bounded_output=bool(audit.get('seconds',float('inf'))<=.5),
                physical_placement_unchanged=original['final_bomb_positions']==candidate['final_bomb_positions'],
                wall_time_unchanged=original['score_wall']==candidate['score_wall']and original['score_time']==candidate['score_time'])
    result=dict(status='PASS_ASTARA_FINAL_OUTPUT_MECHANISM'if all(checks.values())else'STOP_FIRST_ASTARA_OUTPUT_RULE_GATE',
                checks=checks,physics_steps=b['physics_steps'],parent_health_failure_preserved=True,
                baseline=original,candidate=candidate,actual_audit=audit,
                five_map_comparison=[dict(owner=old['owner'],parent_map=old['score'],filtered_map=new['score'],parent_credit=old['breakdown']['credit'],filtered_credit=new['breakdown']['credit'],erased=new['audit'].get('erased_pixels'),status=new['audit'].get('status'))for old,new in zip(a['map_results'],b['filtered_map_results'])],
                native_rounds=0,automatic_native=False,automatic_five=False,loop_wall_seconds=b['wall_seconds'],
                qualification='Output mechanism only: preserved parent collision is not repaired or reclassified as safe. No full-red performance claim.')
    write('RESULT_FIRST.json',result)
    write('STATUS.json',dict(utc=utc(),status=result['status'],native_rounds=0),False)
    print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':
    try:main()
    except Exception:
        write('FIRST_ERROR.json',dict(utc=utc(),traceback=traceback.format_exc(),no_automatic_retry=True))
        write('STATUS.json',dict(utc=utc(),status='STOP_FIRST_DIAGNOSTIC_ERROR'),False)
        raise

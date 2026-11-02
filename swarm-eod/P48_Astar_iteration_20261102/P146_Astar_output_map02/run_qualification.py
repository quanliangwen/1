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
D=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P146_Astar_output_map02_20261102'
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60']
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def write(name,data,first=True):
    p=F/name
    if first:assert not p.exists(),p
    p.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())

def remote(code):
    return subprocess.run(SSH+[R+'/.venv/bin/python','-'],input=code.encode(),capture_output=True,timeout=90)

def keep(name,response):
    p=F/(name+'.capture.txt')
    assert not p.exists()
    p.write_bytes(response.stdout+response.stderr)
    print(response.stdout.decode(errors='replace')[-1400:],flush=True)
    if response.returncode:raise RuntimeError('First qualification error preserved: '+name)

def fetch(name):
    p=F/name
    p.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+name,str(p)],check=True,timeout=60)

def main():
    assert not(F/'QUALIFICATION_STARTED_FIRST.json').exists()
    binding=load(F/'LAUNCH_BINDING_FIRST.json')
    assert all(hashlib.sha256((F/n).read_bytes()).hexdigest()==h for n,h in binding['files'].items())
    guard=(F/'check_scoped_serial.py').read_text()
    keep('SERIAL_FIRST',remote(guard))
    write('QUALIFICATION_STARTED_FIRST.json',dict(utc=utc(),pid=os.getpid(),maximum_hours=14,native_rounds_limit=2,official_release=False))
    keep('MKDIR_FIRST',remote('from pathlib import Path\np=Path('+repr(D)+')\nassert not p.exists()\np.mkdir()\n'))
    for p in [F/'versions',F/'BASE_WORKSPACE.json',F/'INTERNAL_ZIP_BINDING_LOCAL_FIRST.json',F/'SMALL_TEST_EVIDENCE.json',F/'TEST_PROTOCOL.json',
              F/'prepare_zip_workspace.py',F/'check_sdk_actual_zip_entry.py',F/'declare_native.py',F/'run_offline.py',F/'launch_campaign.py',F/'check_scoped_serial.py',
              Path('E:/codex/UAV_rules_astar_restart_20261030/run_sdk_captured.py')]:
        subprocess.run(['scp','-q','-r',str(p),'junhao@10.112.162.60:'+D+'/'],check=True,timeout=90)
    keep('WORKSPACE_FIRST',subprocess.run(SSH+[R+'/.venv/bin/python',D+'/prepare_zip_workspace.py'],capture_output=True,timeout=120))
    fetch('WORKSPACE_READY.json')
    fetch('INTERNAL_ZIP_BINDING.json')
    src=Path('E:/codex/PJ01_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py').read_text()
    methods='\n'.join(ast.get_source_segment(src,n)for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name in ['cpu_sample','resource'])
    code='from pathlib import Path\nimport os,time,shutil,json,datetime\nR=Path('+repr(R)+')\nD=json.loads((R/"solver_study/framework_screen_20261016/best87_independent_20261025/P37_phase_five_comparison_20261101/PREDECLARATION.json").read_text())\ndef utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()\n'+methods+'\nprint(json.dumps(resource()))\n'
    deadline=time.monotonic()+14*3600
    consecutive=[]
    i=0
    while time.monotonic()<deadline:
        if(F/'STOP_REQUESTED').exists():raise RuntimeError('Human stop')
        i+=1
        response=remote(code)
        keep('CAPACITY_'+str(i)+'_FIRST',response)
        row=json.loads(response.stdout)
        consecutive=consecutive+[row]if row['clean']else[]
        write('QUALIFICATION_STATUS.json',dict(utc=utc(),status='WAITING_ORIGINAL_CAPACITY',resource=row),False)
        if len(consecutive)>=2:break
        time.sleep(60)
    else:raise TimeoutError('Finite14h original capacity wait')
    write('RESOURCE_TWO_SAMPLE_FIRST.json',consecutive)
    keep('BEFORE_ENTRY_SERIAL_FIRST',remote(guard))
    write('QUALIFICATION_STATUS.json',dict(utc=utc(),status='CHECKING_ACTUAL_ZIP_ABI_SDK_AND_SETTER'),False)
    keep('ENTRY_ACTUAL_ZIP_FIRST',subprocess.run(SSH+[R+'/.venv/bin/python',D+'/run_sdk_captured.py',D+'/check_sdk_actual_zip_entry.py','ENTRY_ACTUAL_ZIP_FIRST','P145Zip'],capture_output=True,timeout=180))
    fetch('ENTRY_ACTUAL_ZIP_FIRST.json')
    assert load(F/'ENTRY_ACTUAL_ZIP_FIRST.json')['status']=='PASS_SERVER_RESEARCH_ENTRY_NOT_OFFICIAL_RELEASE'
    if(F/'STOP_REQUESTED').exists():raise RuntimeError('Human stop before native declaration')
    keep('FROZEN_PREFLIGHT_FIRST',subprocess.run(SSH+[R+'/.venv/bin/python',D+'/declare_native.py'],capture_output=True,timeout=90))
    fetch('PREDECLARATION.json')
    fetch('versions/P145/QUALIFICATION.json')
    keep('BEFORE_NATIVE_SERIAL_FIRST',remote(guard))
    subprocess.run([os.sys.executable,'-X','utf8',str(F/'start_local_collector.py')],check=True,timeout=30)
    keep('NATIVE_LAUNCH_FIRST',subprocess.run(SSH+[R+'/.venv/bin/python',D+'/launch_campaign.py'],capture_output=True,timeout=60))
    fetch('LAUNCH.json')
    write('QUALIFICATION_STATUS.json',dict(utc=utc(),status='QUALIFIED_AND_SINGLE_MAP02_COORDINATOR_STARTED',max_native_rounds=2,automatic_five=False),False)

if __name__=='__main__':
    try:main()
    except Exception:
        write('QUALIFICATION_FIRST_ERROR.json',dict(utc=utc(),traceback=traceback.format_exc(),no_automatic_retry=True))
        write('QUALIFICATION_STATUS.json',dict(utc=utc(),status='STOP_FIRST_QUALIFICATION_ERROR'),False)
        raise

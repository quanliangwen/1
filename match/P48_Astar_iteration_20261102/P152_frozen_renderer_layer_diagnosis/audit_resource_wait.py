"""One fresh resource/process audit of the existing waiting handle; no new SDK."""
from pathlib import Path
import ast,datetime,hashlib,json,subprocess
F=Path(__file__).resolve().parent
assert not(F/'RESOURCE_BLOCK_AUDIT_FIRST.json').exists()
R='/home/junhao/quan/parallel_test_solver/match'
src=Path('E:/codex/PJ01_environment_restore_20261101/P35_continuation_after_parent_repair/run_offline.py').read_text()
funcs='\n'.join(ast.get_source_segment(src,n)for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name in['cpu_sample','resource'])
code='from pathlib import Path\nimport os,time,shutil,json,datetime\nR=Path('+repr(R)+')\nD=json.loads((R/"solver_study/framework_screen_20261016/best87_independent_20261025/P37_phase_five_comparison_20261101/PREDECLARATION.json").read_text())\ndef utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()\n'+funcs+'\nprint(json.dumps(resource()))\n'
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60',R+'/.venv/bin/python','-'],input=code.encode(),capture_output=True,timeout=30)
(F/'BLOCK_RESOURCE_SAMPLE_FIRST.capture.txt').write_bytes(p.stdout+p.stderr);p.check_returncode();now=json.loads(p.stdout)
ps='Get-CimInstance Win32_Process -Filter "ProcessId=114360" | ForEach-Object { [ordered]@{pid=$_.ProcessId;startUTC=$_.CreationDate.ToUniversalTime().ToString("o");command=$_.CommandLine} | ConvertTo-Json -Compress }'
q=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,check=True)
assert q.stdout.strip(),'Handle missing: re-evaluate terminal state instead of blocked audit'
live=json.loads(q.stdout)
assert live['command'].endswith('P152_frozen_renderer_layer_diagnosis/run_diagnostic.py')
assert live['startUTC'].startswith('2026-11-02T02:56:49.377766')
status=json.loads((F/'STATUS.json').read_text())
assert status['status']=='WAITING_ORIGINAL_CAPACITY'and not now['clean']
assert not(F/'RESOURCE_TWO_SAMPLE_FIRST.json').exists()and not(F/'RENDERER_LAYERS_FIRST_SERIAL.capture.txt').exists()
evidence=[]
for turn,pth in[(1,F.parent/'P149_ready_waiting_coordinator/CAPACITY_1_FIRST.capture.txt'),(2,F/'CAPACITY_1_FIRST.capture.txt')]:
    row=json.loads(pth.read_text());assert not row['clean']
    evidence.append(dict(goal_turn=turn,path=str(pth),sha256=hashlib.sha256(pth.read_bytes()).hexdigest(),resource=row,
                         turn_classification='PROGRESS despite resource wait; substantive code/diagnosis did not unblock the required SDK'))
evidence.append(dict(goal_turn=3,resource=now,turn_classification='VERIFIED_WAIT',live_process=live))
out=dict(status='THREE_GOAL_TURN_EXTERNAL_RESOURCE_BLOCK_CONFIRMED',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         previous_goal_turn='PROGRESS',current_goal_turn='VERIFIED_WAIT',same_blocker='Original CPU/load resource admission; changing candidate or wording does not change the blocker.',
         evidence=evidence,current_status=status,live_waiting_handle=live,
         required_next_evidence='Actual P152 frozen renderer layers from the one immutable original-SDK closure.',
         why_no_meaningful_substitute='Pure scope/protocol/semantic counterchecks already completed; further synthetic PASS results cannot identify the actual renderer precision deficit or justify a scored candidate.',
         preserved=['Existing P152 waiting runner and original two-sample gate/finite14h window','All frozen sources/results and SDK/dependencies','External unrelated compute jobs','Full original objective; not complete or user-paused'],
         sdk_frames=0,native_rounds=0,request_status='blocked',queue_cancelled=False,automation_monitor_preserved=True)
(F/'RESOURCE_BLOCK_AUDIT_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=out['status'],process=live,resource=now,queue_cancelled=False)))

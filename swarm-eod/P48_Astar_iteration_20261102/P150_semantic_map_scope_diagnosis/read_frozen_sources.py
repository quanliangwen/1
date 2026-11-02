"""Read only three frozen SDK source files; zero SDK frames/imports."""
from pathlib import Path
import hashlib,json,subprocess
F=Path(__file__).resolve().parent
base=json.loads(Path('E:/codex/P48_astar_five_20261102/WORKSPACE_READY.json').read_text())['versions']['P48_ASTAR']
names=[n for n in base['sdk_files']if n.endswith('/semantic_sensor.py')or n.endswith('/drone_semantic_sensor.py')or n.endswith('/drone_lidar.py')]
assert len(names)==3 and not(F/'SDK_SOURCE_REVIEW_FIRST.json').exists()
payload={n:base['sdk_files'][n]for n in names}
code='''from pathlib import Path
import hashlib,json
W=Path(WORKSPACE)
out={}
for n,h in FILES.items():
 data=(W/n).read_bytes()
 assert hashlib.sha256(data).hexdigest()==h
 out[n]=dict(sha256=h,text=data.decode('utf-8'))
print(json.dumps(out))
'''.replace('WORKSPACE',repr(base['workspace'])).replace('FILES',repr(payload))
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60','/home/junhao/quan/parallel_test_solver/match/.venv/bin/python','-'],input=code.encode(),capture_output=True,timeout=30)
(F/'SOURCE_READ_FIRST.capture.txt').write_bytes(p.stderr)
p.check_returncode();out=json.loads(p.stdout)
for n,v in out.items():
 assert hashlib.sha256(v['text'].encode()).hexdigest()==payload[n]
 (F/Path(n).name).write_bytes(v['text'].encode())
report=dict(status='PASS_FROZEN_PRIMARY_SOURCE_HASHES',files=payload,sdk_imports=0,sdk_frames=0,native_rounds=0,
            purpose='Read actual public sensing semantics before any proposed dynamic map mask. P149 remains the sole waiting SDK scheduler.')
(F/'SDK_SOURCE_REVIEW_FIRST.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))

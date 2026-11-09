from pathlib import Path
import json,hashlib,subprocess,time
H=Path(__file__).parent;J=H/'iterations/I012_iterated_block_mitm/engineering40';reg=J/'NATIVE_REGISTRATION.json';launch=J/'NATIVE_LAUNCH.json'
if launch.exists() or (J/'native.log').exists():raise RuntimeError('Native launch already registered; inspect PID instead')
d=json.load(open(reg))
for n,sha in d['driver_sha256'].items():
 if hashlib.sha256((H/n).read_bytes()).hexdigest()!=sha:raise RuntimeError('Native driver mismatch')
with (J/'native.log').open('x') as log:p=subprocess.Popen(['python3','-u',str(H/'validate_i012_engineering.py')],cwd=H,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
v=dict(time=time.time(),pid=p.pid,command=['python3','-u','validate_i012_engineering.py'],registration_sha256=hashlib.sha256(reg.read_bytes()).hexdigest(),wait_for=d['wait_for'],no_native_calls_until_both_dependencies_finish=True)
with launch.open('x') as f:json.dump(v,f,indent=2)
print(json.dumps(v))

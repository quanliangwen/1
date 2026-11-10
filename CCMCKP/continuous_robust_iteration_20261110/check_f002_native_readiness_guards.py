"""Actual premature-registration/final-statistics guards; no simulation attempt."""
from pathlib import Path
import subprocess,json,time
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;S=H/'formal/F002_I016_40x30';D=H/'research/F002_I016_formal_native';T=H/'research/F002_native_audit_preflight';out=T/'ACTUAL_READINESS_GUARDS.json'
if out.exists():raise RuntimeError('No actual readiness preflight overwrite')
if (S/'SEARCH_FINISHED').exists() or D.exists():raise RuntimeError('This premature-stage guard fixture is no longer applicable; inspect actual stage')
launch=json.load(open(S/'LAUNCH.json'));proc=Path('/proc')/str(launch['pid'])/'cmdline'
if not proc.exists() or b'run_f002_search.py' not in proc.read_bytes():raise RuntimeError('Same actual formal search controller not confirmed live')
rows=[]
for python,name in [('python3','register_f002_native.py'),('/home/junhao/miniconda3/bin/python','audit_f002_final.py')]:
 p=subprocess.run([python,str(H/name)],cwd=H,capture_output=True,text=True,check=True);value=json.loads(p.stdout)
 if value['ready'] or value.get('new_MC_calls',0)!=0 or value.get('final_statistics_written',False):raise RuntimeError('Premature formal native orstatistics guard failed')
 rows.append(dict(driver=name,source_sha256=sha(H/name),actual_response=value,exit=p.returncode))
if D.exists() or (S/'FINAL_AUDIT_STATS.json').exists():raise RuntimeError('Guard fixture created a forbidden native stage/final statistics')
r=dict(passed=True,time=time.time(),scope=__doc__,actual_search_controller_pid=launch['pid'],actual_search_controller_confirmed_live=True,actual_native_directory_created=False,final_statistics_created=False,new_MC_calls=0,rows=rows)
with out.open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))

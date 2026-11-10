from pathlib import Path
import json,time,hashlib
H=Path(__file__).resolve().parent;D=H/'formal/F002_I016_40x30';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();reg=json.load(open(D/'REGISTRATION.json'));r=dict(time=time.time(),registration_sha256=sha(D/'REGISTRATION.json'),source_files=len(reg['source_sha256']),goal_status='active',required=1200)
for name in ['LAUNCH.json','RAW_POSTPROCESS_LAUNCH.json']:
 if (D/name).exists():
  v=json.load(open(D/name));cmd=Path('/proc')/str(v['pid'])/'cmdline';r[name]=dict(pid=v['pid'],live=cmd.exists(),command=cmd.read_bytes().replace(b'\0',b' ').decode() if cmd.exists() else None)
for name in ['SEARCH_PROGRESS.json','SEARCH_FINISHED','RAW_AUDIT_PROGRESS.json','RAW_POSTPROCESS_TERMINAL.json']:
 if (D/name).exists():
  try:r[name]=json.load(open(D/name))
  except Exception:r[name]='currently writing'
print(json.dumps(r))

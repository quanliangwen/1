"""Finite completion publisher only: never starts/retries games or iteration."""
from pathlib import Path
import json,time,subprocess,sys,datetime,traceback,os
F=Path(__file__).resolve().parent;utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat();dest=F/'COMPLETION_PUBLISHER_RESULT.json';assert not(F/'COMPLETION_PUBLISHER_ONCE.json').exists()
(F/'COMPLETION_PUBLISHER_ONCE.json').write_text(json.dumps(dict(utc=utc(),pid=os.getpid(),finite_hours=14,starts_games=False,starts_iteration=False),indent=2)+'\n')
try:
 deadline=time.monotonic()+14*3600
 while time.monotonic()<deadline:
  if(F/'STOP_PUBLICATION_REQUESTED').exists():raise RuntimeError('Human stopped pending publication')
  if(F/'LOCAL_COLLECTOR_RESULT.json').exists():
   r=json.loads((F/'LOCAL_COLLECTOR_RESULT.json').read_text())
   if r['status']=='COMPLETE':
    p=subprocess.run([sys.executable,'-X','utf8',str(F/'finalize_and_publish.py')],capture_output=True);(F/'FINAL_PUBLICATION.log').write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,p.stdout+p.stderr
    publication=json.loads((F/'RESULT_PUBLICATION.json').read_text());dest.write_text(json.dumps(dict(status='COMPLETE_VERIFIED_GITHUB_RESULTS',utc=utc(),commit=publication['commit'],url=publication['url']),indent=2)+'\n');print(json.dumps(publication['summary']));break
   raise RuntimeError('Collector stopped; preserve scientific failure, no retry: '+r['status'])
  time.sleep(5)
 else:raise TimeoutError('Finite14h completion publisher expired; no new test')
except Exception:
 dest.write_text(json.dumps(dict(status='FIRST_COMPLETION_OR_PUBLICATION_ERROR',utc=utc(),traceback=traceback.format_exc(),starts_games=False),indent=2)+'\n');raise

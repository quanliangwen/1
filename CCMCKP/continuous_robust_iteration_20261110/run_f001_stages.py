from pathlib import Path
import subprocess,json,time
H=Path(__file__).parent;F=H/'formal/F001_I002_40x30'
for stage,name,log in [('search','run_f001_search.py','search.log'),('validation','validate_f001.py','validation.log')]:
 (F/'STAGE.json').write_text(json.dumps(dict(stage=stage,time=time.time(),goal_status='active')))
 with (F/log).open('x') as f:r=subprocess.run(['python3','-u',str(H/name)],stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:
  (F/'PIPELINE_ERROR.json').write_text(json.dumps(dict(stage=stage,exit=r.returncode,time=time.time())));raise RuntimeError('Formal pipeline error, records preserved')
(F/'STAGE.json').write_text(json.dumps(dict(stage='complete pending independent audit and Excel',time=time.time(),goal_status='active')));print('F001_SEARCH_VALIDATION_FINISHED',flush=True)

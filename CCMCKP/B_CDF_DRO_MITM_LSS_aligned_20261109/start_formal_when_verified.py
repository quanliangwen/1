import pathlib,json,time,hashlib,subprocess,gzip,os
H=pathlib.Path(__file__).resolve().parent;D=H/'frozen_development';V=H/'frozen_development_lss';expected=json.load(open(H/'FROZEN_SOURCE_SHA256.json'))
while not (V/'FINISHED').exists():time.sleep(5)
checks=[]
try:
 actual={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'frozen_candidate').glob('*.py')}
 if actual!=expected:raise RuntimeError('Frozen code changed')
 for c in json.load(open(H/'CASES.json')):
  i=c['index'];s=json.load(open(D/f'S3_{i:02d}.json.gz.run.json'));t=json.load(open(D/f'S3_{i:02d}.terminal.json'));v=json.load(open(V/f'case_{i:02d}.json'))
  if t['exit']!=0 or not s['within_budget'] or s['elapsed']>600 or s['source_sha256']!=expected or s['seed']!=955309 or not s['selected']:raise RuntimeError('Development solver integrity failure '+str(i))
  if v['selection']!=s['selected']['selection'] or v['real_probability']<.985 or v['seed']!=832273 or v['draws']!=10000000 or v['event']!='sum<=T':raise RuntimeError('Development LSS acceptance failure '+str(i))
  checks.append(dict(index=i,cost=s['selected']['cost'],real_probability=v['real_probability'],elapsed=s['elapsed'],passed=True))
 summary=dict(status='40/40 frozen-development cases passed; launch fresh formal experiment',checks=checks,source_sha256=expected)
 (H/'FROZEN_DEVELOPMENT_SUMMARY.json').write_text(json.dumps(summary,indent=2))
 for script,logname in [('formal_campaign.py','formal30_lss.log'),('formal_lss_validate.py','formal30_lss_validation.log')]:
  with open(H/logname,'xb') as log:p=subprocess.Popen(['python3','-u',str(H/script)],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
  print(json.dumps(dict(launched=script,pid=p.pid)),flush=True)
 (H/'FORMAL_LAUNCH_CONFIRMED.json').write_text(json.dumps(dict(launched=True,development_checks=40,source_sha256=expected,unix_time=time.time()),indent=2))
except Exception as e:
 (H/'FORMAL_LAUNCH_BLOCKED.json').write_text(json.dumps(dict(reason=str(e),checks_completed=len(checks)),indent=2));raise

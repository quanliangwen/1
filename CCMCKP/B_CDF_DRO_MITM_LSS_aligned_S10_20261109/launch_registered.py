import pathlib,json,time,subprocess,hashlib,os,signal
H=pathlib.Path(__file__).resolve().parent
smoke=json.load(open(H/'frozen_smoke/SUMMARY.json'))
if not smoke['all_passed']:raise RuntimeError('Frozen smoke failed')
development=[json.load(open(p)) for p in (H/'development').glob('*.terminal.json')]
if len(development)!=40 or any(r['exit']!=0 for r in development):raise RuntimeError('40 development searches incomplete')
reg=json.load(open(H/'REGISTRATION.json'))
if {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'frozen_candidate').glob('*.py')}!=reg['source_sha256']:raise RuntimeError('Frozen source changed')
post=[json.load(open(p)) for p in (H/'development_validation').glob('*.postselection.json')]
with (H/'FORMAL_LAUNCH_CONFIRMED.json').open('x') as f:json.dump(dict(time=time.time(),development_searches=40,development_qualified_at_launch=sum(r['accepted'] for r in post),development_LSS_pending=40-len(post),development_validation_continues_separately=True,frozen_smoke_passed=True,pre_registration=json.load(open(H/'PRE_REGISTRATION_REMOTE_VERIFIED.json'))['commit'],seeds=[960001,960030],launch_note='No changes to frozen solver or registered pipeline; start formal searches after correctness/resource checks while two large development LSS postselections finish'),f,indent=2)
# Stop only this task's idle launch waiter; all compute and validation continue.
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=(p/'cmdline').read_bytes().split(b'\0')
  if b'launch_when_checked.py' in args and (p/'cwd').resolve()==H:os.kill(int(p.name),signal.SIGTERM)
 except (OSError,ProcessLookupError):pass
for script,args,log in [('formal_campaign.py',[],'formal_campaign.log'),('validate_portfolio.py',['formal'],'validation.log'),('audit_final_certificates.py',[],'final_certificates.log')]:
 with open(H/log,'x') as out:subprocess.Popen(['python3','-u',str(H/script)]+args,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
print('REGISTERED_FORMAL_STARTED',flush=True)

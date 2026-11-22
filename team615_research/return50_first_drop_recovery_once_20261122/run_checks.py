from pathlib import Path
import subprocess,sys,json,platform
r=Path(__file__).resolve().parent
scripts=sys.argv[2:] or ['verify_recovery.py','verify_finish.py','verify_budget_regression.py','verify_return50.py']
results=[]
for name in scripts:
    p=subprocess.run([sys.executable,str(r/name),sys.argv[1]],capture_output=True,text=True)
    attempt=len(list(r.glob(name+'.attempt*.log')))+1
    log=name+f'.attempt{attempt}.log'
    (r/log).write_text(p.stdout+p.stderr,encoding='utf8')
    result=dict(script=name,exit_code=p.returncode,log=log)
    results.append(result)
    print(json.dumps(result),flush=True)
    print((p.stdout+p.stderr)[-2400:],flush=True)
    if p.returncode:break
(r/'CHECK_RUN.json').write_text(json.dumps(dict(interpreter=sys.executable,python=platform.python_version(),results=results,full_matches=0,physics_steps=0),indent=2)+'\n',encoding='utf8')
sys.exit(any(x['exit_code'] for x in results))

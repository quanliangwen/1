from pathlib import Path
import json,subprocess,os,datetime
F=Path(__file__).resolve().parent;R=Path('/home/junhao/quan/parallel_test_solver/match');H=F.parent
assert not(F/'LAUNCH.json').exists() and not(F/'RUN_ONCE.json').exists()
subprocess.run([str(R/'.venv/bin/python'),str(F/'check_scoped_serial.py')],check=True)
with (F/'coordinator.stdout.log').open('xb') as out,(F/'coordinator.stderr.log').open('xb') as err:
    p=subprocess.Popen([str(R/'.venv/bin/python'),'-u',str(F/'run_offline.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
start=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()[19]
receipt=dict(status='FROZEN_CORNER_FIVE_LAUNCHED',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=p.pid,starttime_ticks=start,source=str(F/'run_offline.py'),max_native_rounds=10,automatic_five=False,automation90_active=False,builtin_goal_active=False,finite_human_requested_test=True)
(F/'LAUNCH.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

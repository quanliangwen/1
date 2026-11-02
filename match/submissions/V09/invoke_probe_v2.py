from pathlib import Path
import subprocess,sys,json
F=Path(__file__).resolve().parent;label,python=sys.argv[1:];log=F/('PROBE_V2_'+label+'.log');assert not log.exists()
p=subprocess.run([python,str(F/'probe_actual_v09_v2.py'),label],capture_output=True)
log.write_bytes(p.stdout+p.stderr);print(p.stdout.decode(errors='replace')[-1700:]);print(p.stderr.decode(errors='replace')[-1700:]);raise SystemExit(p.returncode)

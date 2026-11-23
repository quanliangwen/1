from pathlib import Path
from collections import Counter
import json,os
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');assert Path.cwd().resolve()==B.resolve()
H=B/'work/egs_large_pilot_20261123'
state=json.loads((H/'STATE.json').read_text()) if (H/'STATE.json').exists() else {}
outcomes=[json.loads(p.read_text()) for p in (H/'outcomes').glob('*.json')]
groups=Counter((r['arm'],r['case_index'],r['rc']) for r in outcomes)
pid=json.loads((H/'LAUNCH_REQUEST.json').read_text())['pid']
live=Path('/proc/%s'%pid).exists()
ppid=None
if live:
    try:ppid=next(s for s in Path('/proc/%s/status'%pid).read_text().splitlines() if s.startswith('PPid:'))
    except OSError:pass
print(json.dumps({'state':state,'controller_live':live,'ppid':ppid,
    'terminal_by_arm_case_rc':[{'arm':a,'case_index':i,'rc':rc,'count':n} for (a,i,rc),n in sorted(groups.items())],
    'failed':[{k:r.get(k) for k in ['identity','rc','termination_reason']} for r in outcomes if r['rc']!=0],
    'controller_error':json.loads((H/'CONTROLLER_ERROR.json').read_text()) if (H/'CONTROLLER_ERROR.json').exists() else None},ensure_ascii=False))

from pathlib import Path
import json,statistics
R=Path(__file__).resolve().parent
A=json.loads(Path('E:/codex/S10_EGS_LSS_3large_60w_20261124/evidence/INDEPENDENT_AUDIT_STATISTICS.json').read_text())
out=[]
for c in [19,35,39]:
 for arm in ['S10_LSS_FIXED','EGS_LSS_FIXED_2p4']:
  rows=[r for r in A['runs'] if r['case_index']==c and r['arm']==arm]
  gaps=[r['cost']-r['raw_final_cost'] for r in rows]
  out.append({'case':c,'arm':arm,'raw_best_cost_min':min(r['raw_final_cost'] for r in rows),
   'raw_best_cost_max':max(r['raw_final_cost'] for r in rows),'raw_best_cost_mean':statistics.mean(r['raw_final_cost'] for r in rows),
   'final_LSS_selected_more_expensive_runs':sum(v>1e-8 for v in gaps),
   'final_minus_raw_cost_mean':statistics.mean(gaps),'final_avg':statistics.mean(r['cost'] for r in rows),
   'new_probability_evaluations':0})
(R/'PREVIOUS_LSS_SELECTION_GAP.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))

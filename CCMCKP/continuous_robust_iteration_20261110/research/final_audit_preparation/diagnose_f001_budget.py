"""Frozen-run budget allocation diagnostic; no validation or Avg estimates."""
from pathlib import Path
import json,time,collections,statistics
H=Path(__file__).parent;F=H/'formal/F001_I002_40x30';reg=json.load(open(F/'REGISTRATION.json'));cases={c['index']:c for c in json.load(open(H/'CASES.json'))};by=collections.defaultdict(list)
for p in (F/'search').glob('*.terminal.json'):
 t=json.load(open(p))
 if t['exit']!=0:continue
 m=json.load(open(str(p)[:-len('.terminal.json')]+'.run.json'))
 if m['source_sha256']!=reg['source_sha256'] or m['seed']!=t['seed']:raise RuntimeError('Frozen identity mismatch')
 e=t['extension'];model=e.get('robust_cdf_lns',{});by[t['index']].append(dict(seed=t['seed'],base=e['base_seconds'],extension=e['extension_seconds'],proposals=model.get('proposals',0),new_raw=model.get('new_certified',0),initial_pool=e['base_pool'],final_pool=e['final_pool']))
rows=[]
for i,rs in sorted(by.items()):
 c=cases[i];large=int(c['instance'].split('_')[1])>5
 rows.append(dict(index=i,instance=c['instance'],capacity=c['tmax'],observed=len(rs),extension_applicable=large,base_seconds_min=min(r['base'] for r in rs),base_seconds_median=statistics.median(r['base'] for r in rs),base_seconds_max=max(r['base'] for r in rs),base_above_420=sum(r['base']>420 for r in rs),extension_seconds_min=min(r['extension'] for r in rs),extension_seconds_median=statistics.median(r['extension'] for r in rs),extension_seconds_max=max(r['extension'] for r in rs),zero_proposals=sum(r['proposals']==0 for r in rs),no_new_raw=sum(r['new_raw']==0 for r in rs),new_raw_min=min(r['new_raw'] for r in rs),new_raw_max=max(r['new_raw'] for r in rs),runs=rs))
result=dict(time=time.time(),scope='actual frozen formal search scheduling only; no LSS evaluation, cost Avg or Std, optimization changes or feedback',observed_searches=sum(len(r) for r in by.values()),rows=rows)
(F/'BUDGET_DIAGNOSTIC.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}));print(json.dumps([{k:v for k,v in r.items() if k!='runs'} for r in rows if r['index']>=35]))

from pathlib import Path
import json,gzip,hashlib
H=Path(__file__).parent;F=H/'formal/F001_I002_40x30';reg=json.load(open(F/'REGISTRATION.json'));cases={c['index']:c for c in json.load(open(H/'CASES.json'))};rawref=json.load(open(H/'RAW_REFERENCE.json'));rows=[];errors=[]
for p in sorted((F/'search').glob('*.terminal.json')):
 t=json.load(open(p));row={k:v for k,v in t.items() if k!='extension'};file=p.with_name(p.name[:-len('.terminal.json')])
 if t['exit']!=0:errors.append(dict(index=t['index'],seed=t['seed'],error=t['exit']))
 else:
  d=json.loads(gzip.decompress(file.read_bytes()));m=json.load(open(str(file)+'.run.json'));c=cases[t['index']]
  if m['source_sha256']!=reg['source_sha256']:raise RuntimeError('Formal source changed')
  if m['seed']!=t['seed'] or d['seed']!=t['seed'] or d['instance']!=c['instance'] or d['capacity']!=c['tmax']:raise RuntimeError('Case/seed/capacity mismatch')
  for name,sha in m['input_sha256'].items():
   if rawref['/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance']+'/'+name]!=sha:raise RuntimeError('Input drift')
  if any(q.endswith('_dist.txt') or '/lss_cache/' in q or q.endswith('/BASELINE_S10.json') for q in m['opened_task_paths']):raise RuntimeError('Optimizer read validation/history')
  if d['status']!='completed':raise RuntimeError('Exit0 with unfinished output')
  for q in d['candidate_shortlist']:
   cert=q['certificate']
   if 100*int(cert['lower_numerator'])<99*int(cert['denominator']):raise RuntimeError('Candidate without raw99 certificate')
  row.update(within_budget=m['within_budget'],source_verified=True,input_verified=True,raw_pool=len(d['candidate_shortlist']))
  if not m['within_budget']:errors.append(dict(index=t['index'],seed=t['seed'],error='search_budget_exceeded'))
 rows.append(row)
posts=list((F/'validation').glob('*.post.json'));qualified=sum(json.load(open(p))['accepted'] for p in posts)
result=dict(stage=json.load(open(F/'STAGE.json'))['stage'],required=1200,search_finished=len(rows),search_source_and_input_verified=sum(r.get('source_verified',False) for r in rows),validation_finished=len(posts),qualified=qualified,errors=errors,warning='search completion is not LSS qualification; no30-run Avg until complete audit',rows=rows)
(F/'AUDIT_PROGRESS.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))

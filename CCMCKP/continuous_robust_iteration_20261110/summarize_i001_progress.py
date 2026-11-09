import pathlib,json,gzip,hashlib
H=pathlib.Path(__file__).parent;I=H/'iterations/I001_risk_portfolio';D=I/'pilot';V=I/'pilot_validation';reg=json.load(open(I/'REGISTRATION.json'))
base={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};rows=[];errors=[]
for p in sorted(D.glob('*.terminal.json')):
 d=json.load(open(p));name=p.name[:-len('.terminal.json')];row={k:v for k,v in d.items() if k!='extension'}
 if d['exit']!=0:errors.append(dict(method=d['method'],index=d['index'],stage='search',error=d['exit']))
 else:
  meta=json.load(open(D/(name+'.run.json')));data=json.loads(gzip.decompress((D/name).read_bytes()))
  if meta['source_sha256']!=reg['source_sha256']:raise RuntimeError('Pilot source mismatch')
  if any(path.endswith('_dist.txt') or '/lss_cache/' in path for path in meta['opened_task_paths']):raise RuntimeError('Optimizer read validation data')
  row.update(search_elapsed=meta['elapsed'],within_budget=meta['within_budget'],base_pool=data['extension']['base_pool'],final_pool=data['extension']['final_pool'],extension_seconds=data['extension']['extension_seconds'])
 post=V/(name+'.post.json')
 if post.exists():
  q=json.load(open(post));row.update(validation_finished=True,qualified=q['accepted'],S10_cost=base[d['index']]['new_avg'])
  if q['accepted']:
   chosen=q['selected'];source=json.loads(gzip.decompress((D/name).read_bytes()))
   if not any(c['selection']==chosen['selection'] for c in source['candidate_shortlist']):raise RuntimeError('Selected vector outside generated pool')
   n=int(chosen['certificate']['lower_numerator']);den=int(chosen['certificate']['denominator'])
   if 100*n<99*den or chosen['real_probability']<.985:raise RuntimeError('Invalid primary predicates')
   row.update(qualified_cost=chosen['cost'],real_probability=chosen['real_probability'],gain_vs_S10=base[d['index']]['new_avg']-chosen['cost'],LSS_candidates=len(q['tested']),logical_MC_seconds=q['logical_MC_seconds'])
  else:errors.append(dict(method=d['method'],index=d['index'],stage='validation',error=q.get('error','No qualified member')))
 rows.append(row)
result=dict(iteration='I001',stage='development pilot, one run per case/method; not30-run Avg',search_finished=len(rows),required=28,validation_finished=sum(r.get('validation_finished',False) for r in rows),qualified=sum(r.get('qualified',False) for r in rows),errors=errors,actual_global_cache_calls=len(list((H/'lss_cache').glob('*.json'))),baseline_calls_reused_by_identity=380,rows=rows)
(I/'PROGRESS.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
for r in rows:
 if r.get('qualified'):print(json.dumps({k:r[k] for k in ['method','index','qualified_cost','gain_vs_S10','base_pool','final_pool','search_elapsed']}))

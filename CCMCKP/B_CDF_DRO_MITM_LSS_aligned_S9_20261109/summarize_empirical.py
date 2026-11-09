import os,sys,pathlib,json,gzip,math,hashlib,collections,time
from decimal import Decimal
from fractions import Fraction
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
H=pathlib.Path(__file__).parent;sys.path[:0]=[str(H/'vendor313'),str(H/'frozen_candidate')]
import numpy as np
from flint import fmpz_poly
from instance import load_instance
D=H/'formal30_lss';reg=json.load(open(D/'REGISTRATION.json'));registry=json.load(open(H/'RAW_REFERENCE.json'));baseline=json.load(open(H/'BASELINE_REFERENCE.json'));old={r['index']:r for r in baseline['rows']};cached_file=D/'INDEPENDENT_CERTIFICATES.json';cached=json.load(open(cached_file)) if cached_file.exists() else [];cache={r['key']:r for r in cached};instances={};raw={};errors=[];rows=[];terminals=0;validtotal=0;maxrss=0

def instance(case):
 name=case['instance']
 if name not in instances:
  p=pathlib.Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/name
  instances[name]=load_instance(p)
 return instances[name]

def independent_count(inst,selection,bins,capacity):
 tn,td=Decimal(str(capacity)).as_integer_ratio();polys=[];den=1
 for j in selection:
  key=(inst.name,j)
  if key not in raw:
   text=(inst.path/f'{j}_sample.txt').read_text().split();raw[key]=[Decimal(x).as_integer_ratio() for x in text]
  values=raw[key];den*=len(values);counts=collections.Counter()
  for n,d in values:
   a=n*bins*td;b=d*tn;q=(a+b-1)//b
   if q<bins:counts[q]+=1
  coeff=[0]*(max(counts,default=-1)+1)
  for k,n in counts.items():coeff[k]=n
  polys.append(fmpz_poly(coeff))
 while len(polys)>1:polys=[(polys[k]*polys[k+1]).truncate(bins) if k+1<len(polys) else polys[k] for k in range(0,len(polys),2)]
 return int(polys[0](1)),den

for c in reg['cases']:
 i=c['index'];runs=[];failed=[];inst=None
 for rep in range(1,31):
  stem=f'LSS_{i:02d}_r{rep:02d}';term=D/(stem+'.terminal.json');side=D/(stem+'.json.gz.run.json');main=D/(stem+'.json.gz')
  if not term.exists():continue
  terminals+=1;t=json.load(open(term))
  try:
   if t['exit']!=0:raise ValueError('worker_exit:'+str(t['exit']))
   r=json.load(open(side));m=json.load(gzip.open(main,'rt'));s=r['selected'];inst=instance(c)
   if not s or not r['within_budget'] or r['elapsed']>600 or m['status']!='completed':raise ValueError('missing/invalid/time')
   if any(p.endswith('_dist.txt') for p in r['opened_task_paths']):raise ValueError('distribution metadata entered search')
   if r['seed']!=940000+rep or r['source_sha256']!=reg['source_sha256']:raise ValueError('seed/source')
   prefix=str(inst.path)+'/'
   expected={pathlib.Path(p).name:v for p,v in registry.items() if p.startswith(prefix)}
   if r['input_sha256']!=expected:raise ValueError('input hashes')
   selection=inst.validate_selection(s['selection'])
   if abs(inst.selection_cost(selection)-s['cost'])>1e-8:raise ValueError('cost')
   cert=s['certificate'];n=int(cert['lower_numerator']);den=int(cert['denominator']);bins=cert['bins']
   if cert['selection']!=list(selection) or not cert['all_original_samples'] or not cert['accepted'] or not s.get('final_exact_recomputed') or Fraction(n,den)<Fraction(cert['search_threshold']):raise ValueError('certificate predicate')
   key=json.dumps([i,list(selection),bins],separators=(',',':'))
   if key not in cache:
    start=time.monotonic();nn,dd=independent_count(inst,selection,bins,c['tmax'])
    if (nn,dd)!=(n,den) or 100*nn<99*dd:raise ValueError('independent integer recount mismatch')
    cache[key]=dict(key=key,index=i,selection=list(selection),bins=bins,numerator=str(nn),denominator=str(dd),seconds=time.monotonic()-start,method='Decimal exact ratios; unshifted integer polynomials; independent balanced product')
   elif cache[key]['numerator']!=str(n) or cache[key]['denominator']!=str(den):raise ValueError('cached exact recount mismatch')
   maxrss=max(maxrss,r.get('peak_rss_kib',0));validtotal+=1
   runs.append(dict(rep=rep,seed=r['seed'],cost=s['cost'],lower=s['probability'],numerator=str(n),denominator=str(den),bins=bins,selection=list(selection),elapsed=r['elapsed'],found_seconds=s['found_seconds'],peak_rss_kib=r.get('peak_rss_kib'),exhaustive=m.get('exhaustive')))
  except Exception as e:failed.append(rep);errors.append(dict(index=i,rep=rep,reason=str(e)))
 costs=[r['cost'] for r in runs];complete=len(runs)==30 and not failed;b=old[i]
 row=dict(**c,n=len(runs),failed=failed,complete=complete,old_best=b['best'],old_avg=b['avg'],old_std=b['std'],old_mean_found=b['mean_found'],new_best=min(costs) if costs else None,new_avg=float(np.mean(costs)) if complete else None,new_std=float(np.std(costs,ddof=1)) if complete else None,partial_avg_diagnostic=float(np.mean(costs)) if costs else None,mean_elapsed=float(np.mean([r['elapsed'] for r in runs])) if complete else None,mean_found=float(np.mean([r['found_seconds'] for r in runs])) if complete else None,runs=runs)
 if complete:row.update(gap_avg_to_own_best_pct=(row['new_avg']/row['new_best']-1)*100,best_hit_runs=sum(abs(r['cost']-row['new_best'])<=1e-8 for r in runs),target_met=row['new_avg']<=b['best']+1e-8,gap_to_old_best_pct=(row['new_avg']/b['best']-1)*100,avg_change_pct=(row['new_avg']/b['avg']-1)*100)
 rows.append(row)
summary=dict(schema='LSS_aligned_empirical_diagnostic_summary',required_runs=1200,terminal_records=terminals,valid=validtotal,errors=errors,complete_cases=sum(r['complete'] for r in rows),target_met_cases=sum(r.get('target_met',False) for r in rows),all_reported_valid_certificates_independently_recomputed=True,unique_integer_recounts=len(cache),max_peak_rss_kib=maxrss,minimum_certified_lower=min((r['lower'] for row in rows for r in row['runs']),default=None),rows=rows)
# Atomic outputs: readers must never see a partially written JSON file.
for path,data in [(cached_file,list(cache.values())),(D/'SUMMARY.json',summary)]:
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2));os.replace(tmp,path)
print(json.dumps({k:v for k,v in summary.items() if k not in ['rows','errors']}));print('ERRORS',json.dumps(errors))
for r in rows:
 if r['complete']:print(r['index'],r['new_avg'],r['new_std'],r['gap_to_old_best_pct'])

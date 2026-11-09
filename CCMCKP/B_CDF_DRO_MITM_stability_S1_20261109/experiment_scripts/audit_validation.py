import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import pathlib,json,gzip,numpy as np,time
H=pathlib.Path(__file__).parent;S=json.load(open(H/'validation/SUMMARY.json'));cache={};out=[]
for row in S['rows']:
 raw=pathlib.Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/row['instance']
 for run in row['runs']:
  key=(row['index'],tuple(run['selection']))
  if key not in cache:
   arrays=[np.loadtxt(raw/f'{j}_sample.txt') for j in run['selection']]
   if len(arrays[0])**len(arrays)>=10**7:arrays=[a[:-1] for a in arrays]
   def interval(bins):
    probs=[];alpha=16.;weights=np.exp(-alpha*np.arange(bins)/bins);back=1/weights
    for ceil in [True,False]:
     freq=np.ones(bins+1,dtype=complex)
     for a in arrays:
      ix=(np.ceil(a/row['capacity']*bins) if ceil else np.floor(a/row['capacity']*bins)).astype(int);h=np.bincount(ix[ix<bins],minlength=bins).astype(float)/len(a);freq*=np.fft.rfft(h*weights,2*bins)
     probs.append(float(np.dot(np.fft.irfft(freq,2*bins)[:bins],back)))
    return probs
   bins=65536;probs=interval(bins)
   if probs[0]-1e-7<.99<probs[1]+1e-7:bins=262144;probs=interval(bins)
   verdict='below_0.99' if probs[1]+1e-7<.99 else 'above_0.99' if probs[0]-1e-7>=.99 else 'boundary_unresolved'
   cache[key]=dict(index=row['index'],selection=run['selection'],cost=run['cost'],empirical_rounding_interval=probs,bins=bins,numerical_guard=1e-7,verdict=verdict)
  out.append(dict(index=row['index'],rep=run['rep'],native_probability=run['probability'],audit=cache[key]))
result=dict(unique_vectors=len(cache),runs=len(out),below=sum(r['audit']['verdict']=='below_0.99' for r in out),above=sum(r['audit']['verdict']=='above_0.99' for r in out),unresolved=sum(r['audit']['verdict']=='boundary_unresolved' for r in out),note='Post-run numerical audit of the native empirical product distribution; excludes last sample only for legacy MC branch; not a population confidence certificate; interval has a numerical guard, not a formal floating-point proof.',rows=out)
(H/'validation/PROBABILITY_AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}))

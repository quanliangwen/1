"""Select the cheapest independently rechecked vector observed within ONE run.
This is explicit postprocessing; its time is outside the original search clock.
"""
import os
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import argparse,pathlib,json,gzip,time,itertools
import numpy as np

class EmpiricalOracle:
    def __init__(self,instance,capacity,m):
        self.path=pathlib.Path(instance);self.T=float(capacity);self.m=m;self.samples={};self.transforms={};self.results={};self.guard=1e-7
        self.costs=np.loadtxt(self.path/'cost.txt')
    def sample(self,j):
        if j not in self.samples:
            a=np.loadtxt(self.path/f'{j}_sample.txt');self.samples[j]=a[:-1] if len(a)**self.m>=10**7 else a
        return self.samples[j]
    def bounds(self,s,bins):
        alpha=16.;weight=np.exp(-alpha*np.arange(bins)/bins);back=1/weight;values=[]
        for upward in [True,False]:
            freq=np.ones(bins+1,complex)
            for j in s:
                key=(j,bins,upward)
                f=self.transforms.get(key)
                if f is None:
                    a=self.sample(j);ix=(np.ceil(a/self.T*bins) if upward else np.floor(a/self.T*bins)).astype(int)
                    h=np.bincount(ix[ix<bins],minlength=bins).astype(float)/len(a);f=np.fft.rfft(h*weight,2*bins)
                    if bins==16384:self.transforms[key]=f
                freq*=f
            values.append(float(np.dot(np.fft.irfft(freq,2*bins)[:bins],back)))
        return max(0.,values[0]-self.guard),min(1.,values[1]+self.guard)
    def check(self,s):
        s=tuple(s)
        if s in self.results:return self.results[s]
        for bins in [16384,65536,262144,1048576]:
            lo,hi=self.bounds(s,bins)
            if lo>=.99 or hi<.99:break
        result=dict(lower=lo,upper=hi,bins=bins,accepted=lo>=.99,numerical_guard=self.guard)
        self.results[s]=result;return result

def select(record,oracle):
    started=time.monotonic();candidates={tuple(o['selection']):o for o in record['native_observations']}
    if record.get('selected'):candidates[tuple(record['selected']['selection'])]=record['selected']
    checked=[];selected=None
    for s in sorted(candidates,key=lambda s:(float(oracle.costs[list(s)].sum()),s)):
        result=oracle.check(s);checked.append(dict(selection=list(s),cost=float(oracle.costs[list(s)].sum()),**result))
        if result['accepted']:
            selected=checked[-1];break
    return dict(selected=selected,checked=checked,postprocess_seconds=time.monotonic()-started,original_selected=record['selected'],criterion='lower empirical CDF rounding bound >=0.99 after numerical guard',sample_definition='original all-L exact branch / last sample excluded for legacy MC branch',note='Postprocessing time is additional. Numerical guard is not a formal floating-point error proof or a population confidence certificate.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--record',required=True);ap.add_argument('--instance',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=pathlib.Path(a.out)
    if out.exists():raise RuntimeError('No overwrite')
    record=json.load(gzip.open(a.record,'rt'));m=len(record['selected']['selection']);oracle=EmpiricalOracle(a.instance,record['capacity'],m);result=select(record,oracle)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(selected=result['selected'],postprocess_seconds=result['postprocess_seconds'])))
if __name__=='__main__':main()

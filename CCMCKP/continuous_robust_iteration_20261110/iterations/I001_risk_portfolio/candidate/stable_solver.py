"""CDF/DRO search with independent input-only initialization and CDF local models."""
import time
import numpy as np
from mip_backend import binary_model
import engine as base

class CachedFactor(base.vendor.Factor):
    def get_index_sample(self,k):
        if not hasattr(self,'_descending'):
            self._descending=np.sort(self.samples)[::-1].copy()
            self._descending.flags.writeable=False
        return self._descending[k]
base.vendor.Factor=CachedFactor


class CachedSolver(base.Solver):
    def propose(self,w,cap,theta,pool=48,seconds=2.5):
        if self.remaining()<5:return []
        t=time.monotonic()
        ss=binary_model(self.groups,self.inst.n,w,[self.cost],[-np.inf],[cap],min(seconds,self.remaining()-3),pool)
        elapsed=time.monotonic()-t;self.models+=1;self.model_seconds+=elapsed
        self.history.append(dict(theta=theta,cost_cap=cap,backend='scipy_HiGHS',pool_count=len(ss),solver_seconds=elapsed))
        return sorted((float(w[list(s)].sum()),self.cost_of(s),s) for s in ss)

class StableSolver(CachedSolver):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw)
        arrays=[a[:-1] if self.native_func.__name__=='advanced_monte_carlo' else a for a in self.inst.samples]
        self.emu=np.array([a.mean() for a in arrays]);self.var=np.array([a.var() for a in arrays])
        self.guide_hist=None;self.guide_cache={};self.local_history=[];self.guide_fft=None

    def native_check(self,s,source,force=False):
        s=tuple(s)
        if s in self.native_cache and self.native_cache[s]>=.99:return self.native_cache[s]
        if not force and self.best is not None and self.cost_of(s)>=self.best['cost']-1e-8:return None
        if not force and self.native_func.__name__=='advanced_monte_carlo':
            guide=self.guide_probability(s)
            if guide<.9895:
                self.all_candidates[s]=dict(cost=self.cost_of(s),guide_probability=guide,probability=None,source=source)
                return None
        return super().native_check(s,source,force)

    def histograms(self,delta):
        # Finite-support CDF shift; nearest-bin projection guides proposals only.
        legacy=self.native_func.__name__=='advanced_monte_carlo';B=self.bins;hist=[]
        for samples in self.inst.samples:
            a=samples[:-1] if legacy else samples
            ix=np.rint(a/self.T*B).astype(int)
            h=np.bincount(ix[ix<B],minlength=B).astype(float)/len(a)
            left=float(delta)
            for k in np.flatnonzero(h):
                moved=min(left,h[k]);h[k]-=moved;left-=moved
                if left<=1e-15:break
            if ix.max()<B:h[int(ix.max())]+=delta-left
            hist.append(h)
        return np.array(hist,dtype=np.float32)

    def mip(self,weights=None,rhs=None,vcap=None,trust=None,center=None,seconds=1.,pool=8):
        if self.remaining()<5:return []
        t=time.monotonic();rows=[];lo=[];hi=[]
        if self.best is not None:rows.append(self.cost);lo.append(-np.inf);hi.append(self.best['cost']-1e-7)
        if weights is not None:rows.append(weights);lo.append(-np.inf);hi.append(rhs)
        if vcap is not None:rows.append(self.var);lo.append(-np.inf);hi.append(vcap)
        if center is not None and trust is not None:
            row=np.zeros(self.inst.n);row[list(center)]=1.;rows.append(row);lo.append(self.inst.m-trust);hi.append(np.inf)
        out=binary_model(self.groups,self.inst.n,self.cost,rows,lo,hi,min(seconds,self.remaining()-3),pool)
        self.models+=1;self.model_seconds+=time.monotonic()-t
        return out

    def init_frontier(self):
        # Mean/variance only generate proposals. Every accepted vector uses the original oracle.
        minmu=tuple(int(g[np.argmin(self.emu[g])]) for g in self.groups)
        mincost=tuple(int(g[np.argmin(self.cost[g])]) for g in self.groups)
        v0=max(1e-9,self.var[list(minmu)].sum());v1=max(v0*2,self.var[list(mincost)].sum())
        candidates={minmu,mincost}
        for v in np.geomspace(v0*.5,v1*1.5,20):
            if self.remaining()<20:break
            for z in [2.4 if self.search_target==.99 else 2.7]:
                candidates.update(self.mip(self.emu,self.T-z*np.sqrt(v),vcap=v,seconds=2.,pool=4))
        self.frontier_candidates=set(candidates)
        for s in sorted(candidates,key=lambda s:(self.cost_of(s),s)):
            self.native_check(s,'independent_mean_variance_frontier')
        if self.best is None:
            for _,_,s in self.propose(self.mu+3*self.sd,float(self.cost.max()*self.inst.m),theta=0.,pool=8,seconds=3):
                self.native_check(s,'original_low_risk_fallback',True)
                if self.best is not None:break

    def gradients(self,s):
        B=16384
        if self.guide_hist is None:
            # Nearest-bin is guidance only. Native oracle and original robust MITM are unchanged.
            arrays=[a[:-1] if self.native_func.__name__=='advanced_monte_carlo' else a for a in self.inst.samples]
            self.guide_hist=np.array([np.bincount(np.rint(a/self.T*B).astype(int)[np.rint(a/self.T*B).astype(int)<B],minlength=B)/len(a) for a in arrays])
        h=self.guide_hist;m=self.inst.m;unit=np.r_[1.,np.zeros(B-1)]
        pref=[unit];suff=[None]*(m+1);suff[m]=unit
        for j in s:pref.append(base.truncated_convolution(pref[-1],h[j],B))
        for g in range(m-1,-1,-1):suff[g]=base.truncated_convolution(h[s[g]],suff[g+1],B)
        p=float(pref[-1].sum());w=np.zeros(self.inst.n)
        for g in range(m):
            rest=base.truncated_convolution(pref[g],suff[g+1],B)
            cdf=np.cumsum(rest)[::-1]
            w[self.groups[g]]=h[self.groups[g]]@cdf-p
        return p,w

    def guide_probability(self,s):
        s=tuple(s)
        if s in self.guide_cache:return self.guide_cache[s]
        B=16384;alpha=16.;nfft=2*B
        if self.guide_fft is None:
            if self.guide_hist is None:self.gradients(s)
            self.guide_fft=np.fft.rfft(self.guide_hist*np.exp(-alpha*np.arange(B)/B),nfft,axis=1)
            self.guide_unweight=np.exp(alpha*np.arange(B)/B)
        freq=np.prod(self.guide_fft[list(s)],axis=0)
        p=float(np.dot(np.fft.irfft(freq,nfft)[:B],self.guide_unweight))
        self.guide_cache[s]=min(1.,max(0.,p));return self.guide_cache[s]

    def local_search(self,seconds=160):
        if self.best is None:return
        end=min(self.deadline-10,time.monotonic()+seconds);visited=set();queue={tuple(self.best['selection'])}
        queue.update(s for s in getattr(self,'frontier_candidates',()) if self.cost_of(s)<self.best['cost'] and self.guide_probability(s)>=.975)
        rounds=0
        while time.monotonic()<end and queue and rounds<100:
            def priority(s):
                p=self.guide_probability(s)
                return self.cost_of(s)+max(0.,self.search_target+.00015-p)*self.best['cost']*25
            center=min(queue,key=lambda s:(priority(s),s));queue.remove(center)
            if center in visited:continue
            visited.add(center);rounds+=1
            p,w=self.gradients(center);proposals=set()
            for trust in [2,4,8,16]:
                if time.monotonic()>end:break
                for target in sorted(set(min(.99995,x+self.search_target-.99) for x in [.975,.98,.985,.988,.9901,.992,.995,.999])):
                    if time.monotonic()>end:break
                    proposals.update(self.mip(-w,p-target,trust=trust,center=center,seconds=.5,pool=4))
            ranked=sorted(proposals,key=lambda q:(self.cost_of(q),q))
            old=self.best['cost']
            for q in ranked:
                if time.monotonic()>end:break
                if self.cost_of(q)>=self.best['cost']-1e-8:continue
                prob=self.guide_probability(q)
                if prob>=self.search_target-.00035 and q not in self.native_cache:
                    self.native_check(q,'CDF_sequential_local_model')
                if q not in visited and prob>=.982:queue.add(q)
            if self.best['cost']<old:queue.add(tuple(self.best['selection']))
            if len(queue)>100:
                queue=set(sorted(queue,key=lambda s:(priority(s),s))[:100])
        self.local_history.append(dict(rounds=rounds,visited=len(visited),pending=len(queue),unique_guides=len(self.guide_cache)))

    def run(self):
        self.init_frontier()
        self.local_search(min(160.,self.total_budget*.5))
        if self.best is None:self.save('completed');return
        m=self.inst.m;ranges=np.array([self.cost[g].max()-self.cost[g].min() for g in self.groups]);ordered=list(map(int,np.argsort(-ranges)))
        partitions=[(list(range(0,m,2)),list(range(1,m,2))),(list(range(m//2)),list(range(m//2,m))),(ordered[::2],ordered[1::2])]
        self.bins=512
        for delta in [.00025,0.,.0005]:
            for left,right in partitions:
                if self.remaining()<5:break
                self.matching(delta,left,right)
            if self.remaining()<5:break
        self.local_search(min(30,self.remaining()-10))
        self.save('completed')

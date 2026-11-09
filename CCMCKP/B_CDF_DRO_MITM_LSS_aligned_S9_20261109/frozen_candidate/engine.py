"""V50 independent-start ablations. No previous solutions or run outputs read.
Only original marginal samples/costs, a registered seed, and within-run state enter.
Histogram/DRO scoring is heuristic candidate guidance; native evaluator accepts.
"""
from __future__ import annotations
import os,json,time,gzip,math
from pathlib import Path
import numpy as np
import scipy.fft as spfft
from scipy.special import logsumexp
import native_evaluator as native
import lss_vendor as vendor
from native_support import checks

ARMS=('B_CDF_DRO_MITM','A1_NO_DRO','A2_CHERNOFF','A3_SEQUENTIAL','A4_NO_COST_DIVERSITY')
FRACTIONS=(.02,.01,.03,.005,.05,.08)
THETA=np.array([.1,.2,.5,1.,2.,5.,10.,20.,50.,100.,200.,500.,1000.])

def atomic_json(path,data):
    raw=json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
    if path.name.endswith('.gz'):raw=gzip.compress(raw,compresslevel=3,mtime=0)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(str(tmp),str(path))
    fd=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def chernoff_score(logmgf):
    # Markov applied to exp(t*S), for the same finite-support independent marginals.
    z=np.min(logmgf-THETA,axis=-1)
    return -np.expm1(np.minimum(0.,z))

def robust_logmgf(samples,T,bins,delta):
    a=np.asarray(samples,float)
    if not len(a) or a.min()<0:raise ValueError('nonnegative finite samples required')
    ix=np.ceil(a/(T/bins)-1e-12).astype(int)
    pos,count=np.unique(ix,return_counts=True);mass=count.astype(float)/len(a)
    left=float(delta)
    for k in range(len(mass)):
        moved=min(left,mass[k]);mass[k]-=moved;left-=moved
        if left<=1e-15:break
    mass[-1]+=float(delta)-left
    good=mass>0
    return logsumexp(np.log(mass[good])[:,None]+pos[good,None]/bins*THETA,axis=0)


def worst_cdf_hist(samples,T,bins,delta):
    a=np.asarray(samples,float)
    if np.min(a)<0:raise ValueError('Histogram convolution requires nonnegative resource samples')
    ix=np.ceil(a/(T/bins)-1e-12).astype(int)
    # Bin bins and larger cannot contribute to a strict sum<T.
    h=np.bincount(ix[ix<bins],minlength=bins).astype(float)/len(a)
    mass=float(delta);left=mass
    for k in np.flatnonzero(h>0):
        moved=min(left,h[k]);h[k]-=moved;left-=moved
        if left<=1e-15:break
    removed=mass-left;top=int(ix.max())
    if top<bins:h[top]+=removed
    return h

def truncated_convolution(a,b,bins):
    nfft=2*bins
    return np.maximum(0.,spfft.irfft(spfft.rfft(a,nfft)*spfft.rfft(b,nfft),nfft)[:bins])

class Solver:
    def __init__(self,inst,T,seed,seconds,out,started,arm):
        if arm not in ARMS:raise ValueError('unregistered ablation')
        self.arm=arm;self.inst=inst;self.T=float(T);self.seed=int(seed);self.out=Path(out)
        self.start=started;self.total_budget=float(seconds)
        self.deadline=started+seconds-min(15.,seconds*.1)
        self.rng=np.random.default_rng(seed);self.native_rng=np.random.RandomState(seed)
        self.groups=[np.asarray(g,int) for g in inst.groups]
        self.cost=np.asarray(inst.costs,float);self.mu=np.array([a.mean() for a in inst.samples]);self.sd=np.array([a.std(ddof=1) for a in inst.samples])
        self.best=None;self.events=[];self.native_cache={};self.screen_cache={};self.history=[];self.models=0;self.native_calls=0
        self.factors=[vendor.Factor(j,float(self.cost[j]),float(self.cost.max()-self.cost[j]),str(inst.path/f'{j}_sample.txt'),str(inst.path/f'{j}_big_sample.txt')) for j in range(inst.n)]
        L=len((inst.path/'0_sample.txt').read_text().split());self.param=[inst.m,len(self.groups[0]),L]
        self.checks=checks(L,inst.m,832273)
        self.native_func=native.advanced_exact_evaluation if L**inst.m<10**7 else native.advanced_monte_carlo
        self.indices=self.rng.integers(0,L-1,size=(inst.m,60000),dtype=np.int16)
        self.prior=[];self.extra=None;self.all_candidates={};self.model_seconds=0.;self.native_seconds=0.
        self.native_observations=[];self.bins=4096;self.match_history=[]
        self.half_width=max(1024,min(4096,(40960//inst.m)//512*512))
        self.stage_identity=None


    def cost_of(self,s):return float(self.cost[list(s)].sum())

    def screen(self,s):
            if s not in self.screen_cache:
                sums=np.zeros(60000,np.float64)
                for g,j in enumerate(s):sums+=self.inst.samples[j][self.indices[g]]
                self.screen_cache[s]=float(np.mean(sums<self.T))
            return self.screen_cache[s]

    def propose(self,*args,**kwargs):
        raise NotImplementedError('Instantiate StableSolver from stable_solver.py')

    def native_check(self,s,source,force=False):
            s=tuple(self.inst.validate_selection(s));cost=self.cost_of(s)
            if self.remaining()<3:return None
            if s in self.native_cache and self.native_cache[s]>=.99:return self.native_cache[s]
            if not force and self.best is not None and cost>=self.best['cost']-1e-8:return None
            screen=self.screen(s)
            if not force and screen<.975:
                self.all_candidates[s]={'cost':cost,'screen_probability':screen,'probability':None,'source':source};return None
            t=time.monotonic();outer=np.random.get_state()
            try:
                np.random.set_state(self.native_rng.get_state())
                p=float(self.native_func([self.factors[j] for j in s],self.T,1000000,.99,self.param,self.checks))
                self.native_rng.set_state(np.random.get_state())
            finally:np.random.set_state(outer)
            self.native_seconds+=time.monotonic()-t;self.native_calls+=1;self.native_cache[s]=p
            self.all_candidates[s]={'cost':cost,'screen_probability':screen,'probability':p,'source':source}
            self.native_observations.append(dict(selection=list(s),cost=cost,probability=p,source=source,elapsed=time.monotonic()-self.start))
            if p>=.99 and (self.best is None or cost<self.best['cost']-1e-8):
                self.best={'selection':list(s),'cost':cost,'probability':p,'probability_evaluator':self.native_func.__name__,'source':source,'found_seconds':time.monotonic()-self.start}
                self.events.append(dict(event='native_incumbent',cost=cost,p=p,source=source,elapsed=self.best['found_seconds']))
                self.save('running');print(json.dumps(self.events[-1]),flush=True)
            return p

    def histograms(self,delta):
            legacy=self.native_func.__name__=='advanced_monte_carlo'
            return np.asarray([worst_cdf_hist(a[:-1] if legacy else a,self.T,self.bins,delta) for a in self.inst.samples],np.float64)

    def diverse_half_prune(self,cc,p0,p1,pdf,sel):
            if len(cc)<=self.half_width:return cc,pdf,sel
            buckets=np.minimum(511,((cc-cc.min())/max(1e-9,cc.max()-cc.min())*512).astype(int));slots=self.half_width//512
            chosen=[];seen=set();counts={}
            def take(order,maximum):
                for k in order:
                    b=int(buckets[k])
                    if int(k) not in seen and counts.get(b,0)<maximum:
                        chosen.append(int(k));seen.add(int(k));counts[b]=counts.get(b,0)+1
            take(np.lexsort((cc,buckets)),1)
            take(np.lexsort((cc,-p0,buckets)),max(2,(slots+1)//2))
            take(np.lexsort((cc,-p1,buckets)),slots)
            kk=np.asarray(chosen[:self.half_width],int);return cc[kk],pdf[kk],sel[kk]

    def build_half(self,groups,other,hist,fft,anchors):
            B=self.bins;nfft=2*B;cap=self.best['cost'];rest_min=sum(float(self.cost[self.groups[g]].min()) for g in other)
            suffix=[None]*(len(groups)+1);suffix[-1]=np.r_[1.,np.zeros(B-1)]
            min_suffix=np.zeros(len(groups)+1)
            for k in range(len(groups)-1,-1,-1):
                g=groups[k];cdf=np.max(np.cumsum(hist[self.groups[g]],axis=1),axis=0);light=np.diff(np.r_[0.,cdf])
                suffix[k]=truncated_convolution(light,suffix[k+1],B);min_suffix[k]=min_suffix[k+1]+float(self.cost[self.groups[g]].min())
            completed=[]
            for anchor in anchors:
                q=np.r_[1.,np.zeros(B-1)]
                for g in other:q=truncated_convolution(q,hist[anchor[g]],B)
                completed.append(q)
            costs=np.array([0.]);pdf=np.zeros((1,B),np.float32);pdf[0,0]=1.;sel=np.full((1,self.inst.m),-1,np.int16)
            for depth,g in enumerate(groups):
                if self.remaining()<5:return None
                items=self.groups[g];cdf0=np.cumsum(truncated_convolution(suffix[depth+1],completed[0],B))[::-1]
                cdf1=np.cumsum(truncated_convolution(suffix[depth+1],completed[-1],B))[::-1]
                cdf0=cdf0.astype(np.float32);cdf1=cdf1.astype(np.float32)
                parent_fft=spfft.rfft(pdf,nfft,axis=1);crows=[];p0rows=[];p1rows=[];qrows=[];srows=[]
                for first in range(0,len(costs),64):
                    if self.remaining()<5:return None
                    last=min(len(costs),first+64);nf=last-first;K=len(items)
                    cc=(costs[first:last,None]+self.cost[items]).reshape(-1)
                    valid=cc<cap-rest_min-min_suffix[depth+1]-1e-8
                    if not np.any(valid):continue
                    freq=(parent_fft[first:last,None,:]*fft[items][None,:,:]).reshape(nf*K,-1)[valid]
                    pp=np.maximum(0.,spfft.irfft(freq,nfft,axis=1)[:,:B]).astype(np.float32)
                    ss=np.repeat(sel[first:last],K,axis=0);ss[:,g]=np.tile(items,nf)
                    crows.append(cc[valid]);p0rows.append(np.clip(pp@cdf0,0,1));p1rows.append(np.clip(pp@cdf1,0,1));qrows.append(pp);srows.append(ss[valid])
                if not crows:return None
                cc=np.concatenate(crows);p0=np.concatenate(p0rows);p1=np.concatenate(p1rows);qq=np.concatenate(qrows);ss=np.concatenate(srows)
                costs,pdf,sel=self.half_prune(cc,p0,p1,qq,ss)
            return costs,pdf,sel

    def cdf_matching(self,delta,left,right):
            hist=self.histograms(delta);fft=spfft.rfft(hist,2*self.bins,axis=1)
            anchors=[tuple(self.best['selection'])]
            if self.extra and self.extra not in anchors:anchors.append(self.extra)
            a=self.build_half(left,right,hist,fft,anchors)
            if a is None:return
            b=self.build_half(right,left,hist,fft,anchors)
            if b is None:return
            ca,pa,sa=a;cb,pb,sb=b;cdfB=np.ascontiguousarray(np.cumsum(pb,axis=1,dtype=np.float64)[:,::-1].T)
            proposals={};cap=self.best['cost'];fractions=[0.,.001,.0025,.005,.01,.02,.03,.05]
            for first in range(0,len(ca),64):
                if self.remaining()<5:break
                last=min(len(ca),first+64);cost=ca[first:last,None]+cb[None,:];prob=np.clip(pa[first:last]@cdfB,0.,1.)
                for fraction in fractions:
                    score=np.where(cost<cap*(1-fraction)-1e-8,prob,-np.inf).reshape(-1);n=min(48,int(np.isfinite(score).sum()))
                    if n==0:continue
                    ix=np.argpartition(score,len(score)-n)[-n:]
                    for k in ix:
                        ia=first+int(k)//len(cb);ib=int(k)%len(cb);key=(ia,ib)
                        proposals[key]=(float(score[k]),float(ca[ia]+cb[ib]))
            checked=0;potential=len(proposals)
            for (ia,ib),(p,cost) in sorted(proposals.items(),key=lambda z:(-z[1][0],z[1][1])):
                if self.remaining()<3 or checked>=1800:break
                if p<.975:continue
                s=sa[ia].copy();s[right]=sb[ib,right]
                self.native_check(tuple(int(j) for j in s),f'robust_mitm_delta{delta}_left'+','.join(map(str,left)))
                checked+=1
            self.match_history.append(dict(delta=delta,left=left,right=right,left_states=len(ca),right_states=len(cb),pair_count=len(ca)*len(cb),shortlist=potential,checked=checked,remaining=self.remaining()))
            self.save('running')


    def remaining(self):return self.deadline-time.monotonic()

    def half_prune(self,cc,p0,p1,pdf,sel):
        if self.arm!='A4_NO_COST_DIVERSITY':return self.diverse_half_prune(cc,p0,p1,pdf,sel)
        if len(cc)<=self.half_width:return cc,pdf,sel
        # Same width; replace cost buckets by a global probability ranking only.
        ix=np.lexsort((cc,-np.maximum(p0,p1)))[:self.half_width]
        return cc[ix],pdf[ix],sel[ix]

    def matching(self,delta,left,right):
        self.stage_identity=dict(delta=float(delta),left=left,right=right)
        if self.arm=='A2_CHERNOFF':return self.chernoff_matching(delta,left,right)
        if self.arm=='A3_SEQUENTIAL':return self.sequential_matching(delta,left,right)
        return self.cdf_matching(delta,left,right)

    def sequential_matching(self,delta,left,right):
        # Replace two half-beams and their join by one ordinary group-by-group beam.
        # The identical build_half/pruning/kernel is used with all groups and no other half.
        hist=self.histograms(delta);fft=spfft.rfft(hist,2*self.bins,axis=1)
        state=self.build_half(left+right,[],hist,fft,[tuple(self.best['selection'])])
        if state is None:return
        costs,pdfs,selections=state;proposals={};cap=self.best['cost']
        probs=np.clip(pdfs.sum(axis=1,dtype=np.float64),0.,1.)
        for first in range(0,len(costs),64):
            if self.remaining()<5:break
            last=min(len(costs),first+64)
            for fraction in FRACTIONS:
                score=np.where(costs[first:last]<cap*(1-fraction)-1e-8,probs[first:last],-np.inf)
                n=min(48,int(np.isfinite(score).sum()))
                if not n:continue
                for k in np.argpartition(score,len(score)-n)[-n:]:
                    k=first+int(k);proposals[k]=(float(probs[k]),float(costs[k]))
        checked=0
        for k,(p,cost) in sorted(proposals.items(),key=lambda z:(-z[1][0],z[1][1])):
            if self.remaining()<3 or checked>=1800:break
            if p<.975:continue
            self.native_check(tuple(map(int,selections[k])),f'sequential_delta{delta}_order'+','.join(map(str,left+right)))
            checked+=1
        self.match_history.append(dict(engine='sequential_CDF',delta=delta,left=left,right=right,states=len(costs),shortlist=len(proposals),checked=checked,remaining=self.remaining()))
        self.save('running')

    def chernoff_build_half(self,groups,other,mgf,anchors):
        cap=self.best['cost'];rest_min=sum(float(self.cost[self.groups[g]].min()) for g in other)
        suffix=np.zeros((len(groups)+1,len(THETA)));min_suffix=np.zeros(len(groups)+1)
        for k in range(len(groups)-1,-1,-1):
            g=groups[k];suffix[k]=suffix[k+1]+mgf[self.groups[g]].min(axis=0)
            min_suffix[k]=min_suffix[k+1]+float(self.cost[self.groups[g]].min())
        completed=[mgf[[anchor[g] for g in other]].sum(axis=0) if other else np.zeros(len(THETA)) for anchor in anchors]
        costs=np.array([0.]);states=np.zeros((1,len(THETA)));sel=np.full((1,self.inst.m),-1,np.int16)
        for depth,g in enumerate(groups):
            if self.remaining()<5:return None
            items=self.groups[g];crows=[];qrows=[];srows=[];p0rows=[];p1rows=[]
            for first in range(0,len(costs),64):
                if self.remaining()<5:return None
                last=min(len(costs),first+64);nf=last-first;K=len(items)
                cc=(costs[first:last,None]+self.cost[items]).reshape(-1)
                valid=cc<cap-rest_min-min_suffix[depth+1]-1e-8
                if not np.any(valid):continue
                pp=(states[first:last,None,:]+mgf[items][None,:,:]).reshape(nf*K,-1)[valid]
                ss=np.repeat(sel[first:last],K,axis=0);ss[:,g]=np.tile(items,nf)
                crows.append(cc[valid]);qrows.append(pp);srows.append(ss[valid])
                p0rows.append(chernoff_score(pp+suffix[depth+1]+completed[0]))
                p1rows.append(chernoff_score(pp+suffix[depth+1]+completed[-1]))
            if not crows:return None
            costs,states,sel=self.half_prune(np.concatenate(crows),np.concatenate(p0rows),np.concatenate(p1rows),np.concatenate(qrows),np.concatenate(srows))
        return costs,states,sel

    def chernoff_matching(self,delta,left,right):
        legacy=self.native_func.__name__=='advanced_monte_carlo'
        mgf=np.asarray([robust_logmgf(a[:-1] if legacy else a,self.T,self.bins,delta) for a in self.inst.samples])
        anchors=[tuple(self.best['selection'])]
        a=self.chernoff_build_half(left,right,mgf,anchors)
        if a is None:return
        b=self.chernoff_build_half(right,left,mgf,anchors)
        if b is None:return
        ca,pa,sa=a;cb,pb,sb=b;cap=self.best['cost'];proposals={}
        for first in range(0,len(ca),64):
            if self.remaining()<5:break
            last=min(len(ca),first+64);cost=ca[first:last,None]+cb[None,:]
            prob=chernoff_score(pa[first:last,None,:]+pb[None,:,:])
            for fraction in FRACTIONS:
                score=np.where(cost<cap*(1-fraction)-1e-8,prob,-np.inf).reshape(-1)
                n=min(48,int(np.isfinite(score).sum()))
                if not n:continue
                for k in np.argpartition(score,len(score)-n)[-n:]:
                    ia=first+int(k)//len(cb);ib=int(k)%len(cb)
                    proposals[(ia,ib)]=(float(score[k]),float(ca[ia]+cb[ib]))
        checked=0
        for (ia,ib),(p,cost) in sorted(proposals.items(),key=lambda z:(-z[1][0],z[1][1])):
            if self.remaining()<3 or checked>=1800:break
            if p<.975:continue
            s=sa[ia].copy();s[right]=sb[ib,right]
            self.native_check(tuple(map(int,s)),f'chernoff_delta{delta}_left'+','.join(map(str,left)))
            checked+=1
        self.match_history.append(dict(engine='Chernoff_MGF',delta=delta,left=left,right=right,left_states=len(ca),right_states=len(cb),pair_count=len(ca)*len(cb),shortlist=len(proposals),checked=checked,remaining=self.remaining()))
        self.save('running')

    def run(self):
        # Exactly the original V50 fallback: no imported priors or auxiliary anchors.
        for _,_,s in self.propose(self.mu+3*self.sd,float(self.cost.max()*self.inst.m),theta=0.,pool=8,seconds=3):
            self.native_check(s,'current_run_V50_original_low_risk_initialization',True)
            if self.best is not None:break
        if self.best is None:self.save('completed');return
        m=self.inst.m;ranges=np.array([self.cost[g].max()-self.cost[g].min() for g in self.groups]);ordered=list(map(int,np.argsort(-ranges)))
        partitions=[(list(range(0,m,2)),list(range(1,m,2))),(list(range(m//2)),list(range(m//2,m))),(ordered[::2],ordered[1::2])]
        # Preserve nine stage slots, order, natural revisits, and the shared time cap.
        radii=[0.,0.,0.] if self.arm=='A1_NO_DRO' else [.00025,0.,.0005]
        for delta in radii:
            for left,right in partitions:
                if self.remaining()<5:break
                self.matching(delta,left,right)
            if self.remaining()<5:break
        self.save('completed')

    def save(self,status):
        data=dict(schema='CDF_DRO_stability_S1',arm=self.arm,status=status,seed=self.seed,instance=self.inst.name,capacity=self.T,
            runtime_before_save=time.monotonic()-self.start,selected=self.best,events=self.events,
            native_evaluator=self.native_func.__name__,native_probability_calls=self.native_calls,native_seconds=self.native_seconds,
            screen_unique=len(self.screen_cache),candidate_unique=len(self.all_candidates),models=self.models,model_seconds=self.model_seconds,
            initialization_models=self.history,native_observations=self.native_observations,match_history=self.match_history,
            external_solution_inputs=False,prior_count=0,extra_completion=None,
            local_history=getattr(self,'local_history',[]),guide_unique=len(getattr(self,'guide_cache',{})),
            config=dict(variant='S1',backend='scipy_HiGHS',projection='nearest for MITM guidance, original native acceptance',bins=self.bins,half_width=self.half_width,cost_bins=512,native_gate=.99,screen_gate=.975,screen_draws=60000,native_draws=1000000,
                native_stream_seed=self.seed,radii=[0.,0.,0.] if self.arm=='A1_NO_DRO' else [.00025,0.,.0005],time_budget=self.total_budget,work_reserve=min(15.,self.total_budget*.1)),
            evidence_note='All native calls including negatives retained; probabilities are original evaluator observations, not population confidence certificates; worker immediate clock includes this save.')
        atomic_json(self.out,data)

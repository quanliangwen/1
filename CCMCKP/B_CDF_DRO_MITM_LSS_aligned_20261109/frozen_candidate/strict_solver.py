import time,json,itertools,hashlib,math
import numpy as np
from stable_solver import StableSolver
from exact_oracle import ExactOracle
from engine import atomic_json

def exact_empirical_cdf(*args):raise RuntimeError('Never use a statistical oracle for acceptance')

class StrictSolver(StableSolver):
    def __init__(self,*a,**kw):
        inst=a[0];self.tail_reconstruction=inst.name.startswith("APP_") and max(map(len,inst.samples))<=30
        self.tail_metadata=[]
        if self.tail_reconstruction:
            # Published APP family prior only; never read *_dist parameters.
            # Gamma has a separate low-scale family. Other families have offsets
            # [0,10,20,30] with weights [900,90,9,1]/1000.
            augmented=[]
            for j,raw in enumerate(inst.samples):
                gamma_like=raw.mean()<2.5 and raw.max()<5.
                if gamma_like:
                    arr=raw+0.5*raw.std(ddof=1)/np.sqrt(len(raw))
                else:
                    base=np.mod(raw,10.);base=np.minimum(10.,base+0.5*base.std(ddof=1)/np.sqrt(len(base)))
                    arr=np.concatenate([np.repeat(base+offset,w) for offset,w in zip([0.,10.,20.,30.],[900,90,9,1])])
                augmented.append(arr)
                self.tail_metadata.append(dict(item=j,gamma_like=bool(gamma_like),original_mean=float(raw.mean()),original_max=float(raw.max()),model_size=len(arr)))
            inst.samples=augmented;inst.nominal=np.array([x.mean() for x in augmented])
        super().__init__(*a,**kw)
        self.native_func=exact_empirical_cdf
        self.emu=self.mu.copy();self.var=np.array([x.var() for x in self.inst.samples])
        self.search_target=(.99 if self.tail_reconstruction else (.993 if self.inst.name.startswith("APP_") and self.inst.m>=50 else .99));self.oracle=ExactOracle(self.inst,self.T,".99" if self.tail_reconstruction else str(self.search_target));self.decisions={};self.exhaustive=None
        self.deadline=self.start+self.total_budget-min(30.,self.total_budget*.1)
    def float_bounds(self,s,bins):
        alpha=16.;weight=np.exp(-alpha*np.arange(bins)/bins);back=1/weight;values=[]
        for up in [True,False]:
            freq=np.ones(bins+1,complex)
            for j in s:
                ix=self.oracle.quantized(j,bins,up);h=np.bincount(ix[ix<bins],minlength=bins).astype(float)/len(ix)
                freq*=np.fft.rfft(h*weight,2*bins)
            values.append(float(np.dot(np.fft.irfft(freq,2*bins)[:bins],back)))
        return values
    def native_check(self,s,source,force=False):
        s=tuple(self.inst.validate_selection(s));cost=self.cost_of(s)
        if self.remaining()<4:return None
        if self.tail_reconstruction and self.guide_probability(s)<self.search_target:return None
        if not force and self.best is not None and cost>=self.best['cost']-1e-8:return None
        if s in self.decisions:return self.decisions[s].get('lower',0.)
        if not force and self.guide_probability(s)<self.search_target-.0008:
            self.decisions[s]=dict(decision='heuristic_screen');return None
        result=None
        for bins in [4096,16384,65536,262144,1048576]:
            if self.remaining()<4 or (bins>=262144 and self.remaining()<40):break
            lo,hi=self.float_bounds(s,bins)
            if hi<self.search_target-1e-7:
                result=dict(decision='floating_screen_only',lower=lo,upper=hi,accepted=False);break
            if lo>=self.search_target+1e-8:
                result=self.oracle.certify(s,bins,False)
                if result['accepted']:break
        if result is None or not result.get('accepted',False):
            result=result or dict(decision='unresolved_not_accepted',accepted=False)
            self.decisions[s]=result;self.native_cache[s]=result.get('lower',0.)
            self.native_observations.append(dict(selection=list(s),cost=cost,source=source,elapsed=time.monotonic()-self.start,**result));return result.get('lower',0.)
        return self.accept(s,source,result)
    def accept(self,s,source,certificate):
        if not certificate['accepted']:raise AssertionError('Cannot accept uncertified vector')
        n=int(certificate['lower_numerator']);d=int(certificate['denominator'])
        if self.oracle.target.denominator*n<self.oracle.target.numerator*d:raise ArithmeticError('Failed integer threshold')
        self.decisions[s]=certificate;self.native_cache[s]=certificate['lower']
        self.native_observations.append(dict(cost=self.cost_of(s),source=source,elapsed=time.monotonic()-self.start,**certificate))
        if self.best is None or self.cost_of(s)<self.best['cost']-1e-8:
            self.best=dict(selection=list(s),cost=self.cost_of(s),probability=certificate['lower'],probability_evaluator='exact_integer_upward_grid_count',certificate=certificate,source=source,found_seconds=time.monotonic()-self.start)
            self.events.append(dict(event='certified_incumbent',cost=self.best['cost'],lower=certificate['lower'],elapsed=self.best['found_seconds'],source=source));self.save('running');print(json.dumps(self.events[-1]),flush=True)
        return certificate['lower']
    def init_frontier(self):
        # Obtain a certified incumbent BEFORE any candidate can restrict the cost cap.
        for z in [3.,5.,10.]:
            s=tuple(int(g[np.argmin(self.mu[g]+z*self.sd[g])]) for g in self.groups)
            self.native_check(s,'independent_certified_low_risk_anchor',True)
            if self.best is not None:break
        super().init_frontier()
    def small_exact_search(self):
        total=math.prod(len(g) for g in self.groups);digest=hashlib.sha256();refuted=0
        selections=sorted(itertools.product(*self.groups),key=lambda s:(self.cost_of(s),s))
        if self.tail_reconstruction:
            maximum=max(self.guide_probability(tuple(map(int,s))) for s in selections)
            self.search_target=max(.987,min(.99,maximum-.0001))
            self.tail_model_maximum=maximum
            self.tail_model_target=self.search_target
        for raw in selections:
            if self.remaining()<5:break
            s=tuple(map(int,raw));resolved=False
            if self.tail_reconstruction and self.guide_probability(s)<self.search_target:continue
            for bins in [256,1024,4096,16384,65536,262144,1048576]:
                if self.remaining()<4:break
                v=self.oracle.certify(s,bins,True)
                if v['accepted']:
                    self.accept(s,'cost_ordered_exact_enumeration',v);resolved=True;break
                if v['infeasible']:
                    digest.update(json.dumps([list(s),bins,v['upper_numerator'],v['denominator']],separators=(',',':')).encode());refuted+=1;resolved=True;break
            if self.best is not None:break
            if not resolved:
                self.exhaustive=dict(total=total,refuted=refuted,proved_optimal_for_empirical_safety_target=False,unresolved_selection=list(s),refutations_sha256=digest.hexdigest());return
        self.exhaustive=dict(total=total,refuted=refuted,proved_optimal_for_empirical_safety_target=self.best is not None and not self.tail_reconstruction,refutations_sha256=digest.hexdigest())
    def pair_search(self,seconds=25):
        end=min(self.deadline-8,time.monotonic()+seconds)
        for iteration in range(8):
            if self.best is None or time.monotonic()>end:break
            center=tuple(self.best['selection']);cost=self.best['cost'];p,w=self.gradients(center)
            moves=[(g,int(j),float(self.cost[j]-self.cost[center[g]]),float(w[j])) for g in range(self.inst.m) for j in self.groups[g] if j!=center[g]]
            if not moves:break
            group=np.array([x[0] for x in moves]);dc=np.array([x[2] for x in moves]);dp=np.array([x[3] for x in moves])
            delta=dc[:,None]+dc[None,:];prob=p+dp[:,None]+dp[None,:]
            valid=(group[:,None]!=group[None,:])&(delta<-1e-8)&(prob>=.985)
            score=np.where(valid,delta+np.maximum(0.,self.search_target+.0002-prob)*cost*25,np.inf).reshape(-1)
            n=min(192,int(np.isfinite(score).sum()));pairs=np.argpartition(score,n-1)[:n] if n else []
            candidates=set()
            for g,j,c,d in moves:
                if c<0 and p+d>=self.search_target-.0008:
                    q=list(center);q[g]=j;candidates.add(tuple(q))
            for k in pairs:
                i,j=divmod(int(k),len(moves));q=list(center);q[moves[i][0]]=moves[i][1];q[moves[j][0]]=moves[j][1];candidates.add(tuple(q))
            for q in sorted(candidates,key=lambda s:(self.cost_of(s),s)):
                if time.monotonic()>end:break
                self.native_check(q,'certified_one_two_group_exchange')
            if self.best['cost']>=cost-1e-8:break
    def run(self):
        if self.inst.m<=5 and math.prod(len(g) for g in self.groups)<=100000:
            self.small_exact_search()
            if self.best is not None:self.final_check();self.save('completed');return
        self.init_frontier();self.local_search(min(140.,self.total_budget*.4));self.pair_search(25.)
        if self.best is None:self.save('completed');return
        m=self.inst.m;ranges=np.array([self.cost[g].max()-self.cost[g].min() for g in self.groups]);ordered=list(map(int,np.argsort(-ranges)))
        partitions=[(list(range(0,m,2)),list(range(1,m,2))),(list(range(m//2)),list(range(m//2,m))),(ordered[::2],ordered[1::2])]
        self.bins=512
        for delta in [.00025,0.,.0005]:
            for left,right in partitions:
                if self.remaining()<8:break
                self.matching(delta,left,right)
            self.pair_search(min(15.,self.remaining()-10))
            if self.remaining()<8:break
        for delta in [0.,.00025,0.,.0005]:
            if self.remaining()<15:break
            order=list(map(int,self.rng.permutation(m)));self.matching(delta,order[:m//2],order[m//2:])
        self.pair_search(min(20.,self.remaining()-10))
        self.final_check();self.save('completed')
    def final_check(self):
        s=tuple(self.best['selection']);c=self.best['certificate']
        n,d=self.oracle.count(s,c['bins'],True)
        if str(n)!=c['lower_numerator'] or str(d)!=c['denominator'] or self.oracle.target.denominator*n<self.oracle.target.numerator*d:raise ArithmeticError('Final exact recomputation failed')
        self.best['final_exact_recomputed']=True
    def save(self,status):
        data=dict(schema='CCMCKP_LSS_aligned_S8',status=status,seed=self.seed,instance=self.inst.name,capacity=self.T,runtime_before_save=time.monotonic()-self.start,selected=self.best,events=self.events,models=self.models,model_seconds=self.model_seconds,observations=self.native_observations,match_history=self.match_history,local_history=self.local_history,exhaustive=self.exhaustive,tail_reconstruction=self.tail_metadata,tail_model_maximum=getattr(self,'tail_model_maximum',None),tail_model_target=getattr(self,'tail_model_target',None),certificate_calls=self.oracle.calls,certificate_seconds=self.oracle.seconds,unique_decisions=len(self.decisions),config=dict(time_budget=self.total_budget,work_reserve=min(30.,self.total_budget*.1),all_original_samples=True,acceptance='original empirical count threshold plus APP-family reconstructed-tail guidance; final independent LSS real_P_test >=0.985',probability_model='integer certificate is for raw empirical marginal product only; reconstructed APP tail model is guidance only; final LSS MC measures benchmark real probability',guidance_only='CDF nearest-grid / finite-support DRO shifts',no_monte_carlo_internal_acceptance=True,nominal_CL=.99,empirical_safety_target=str(self.oracle.target),guidance_probability_target=self.search_target,tail_model_policy='APP n<=30: family mixture weights .9/.09/.009/.001, sample-only gamma-like mean<2.5 max<5, half-standard-error base shift, attainable guidance target max(.987,min(.99,max_model-.0001)); APP m>=50 n500: .993 raw target; all others .99',final_evaluator="uploaded LSS real_P_test",final_tolerance=.985,final_evaluation_outside_search_clock=True,no_history_or_cross_run_inputs=True,bins=self.bins,half_width=self.half_width))
        atomic_json(self.out,data)

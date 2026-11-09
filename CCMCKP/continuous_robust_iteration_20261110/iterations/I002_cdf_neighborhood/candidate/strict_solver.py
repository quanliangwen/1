"""S10: original raw-sample constraint, candidate portfolio, no tail gate.

No APP tail reconstruction or family prior is used. Independent LSS
postselection is a separate process and cannot feed back into this search.
"""
import time,json,itertools,hashlib,math
import numpy as np
from stable_solver import StableSolver
from exact_oracle import ExactOracle
from engine import atomic_json
from small_counts import SmallCounts

def exact_empirical_cdf(*a):raise RuntimeError('Use certified raw sample counts')

class StrictSolver(StableSolver):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw)
        self.native_func=exact_empirical_cdf
        self.search_target=.99;self.oracle=ExactOracle(self.inst,self.T,'.99')
        self.emu=self.mu.copy();self.var=np.array([x.var() for x in self.inst.samples])
        self.pool={};self.decisions={};self.exhaustive=None;self.order_scores={}
        self.deadline=self.start+self.total_budget-min(45.,self.total_budget*.12)
        self.tail_metadata=[];self.auxiliary_grid=None;self.last_save=0.

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
        s=tuple(self.inst.validate_selection(s))
        if s in self.pool:return self.pool[s]['certificate']['lower']
        if self.remaining()<5:return None
        if s in self.decisions:return self.decisions[s].get('lower',0.)
        result=None
        for bins in [1024,4096,16384,65536,262144,1048576]:
            if self.remaining()<5 or (bins>=262144 and self.remaining()<45):break
            lo,hi=self.float_bounds(s,bins)
            # Floating scores schedule exact work; they cannot reject a vector.
            # Any early infeasibility decision is independently integer-counted.
            if hi<.99-1e-7:
                v=self.oracle.certify(s,bins,True)
                if v['infeasible']:result=v;break
            if lo>=.99+1e-8 or bins>=262144:
                v=self.oracle.certify(s,bins,True)
                if v['accepted'] or v['infeasible']:result=v;break
        if result is None:result=dict(accepted=False,decision='unresolved',lower=0.)
        self.decisions[s]=result;self.native_cache[s]=result.get('lower',0.)
        if result['accepted']:return self.accept(s,source,result)
        return result.get('lower',0.)

    def accept(self,s,source,certificate):
        s=tuple(s);n=int(certificate['lower_numerator']);d=int(certificate['denominator'])
        if not certificate['accepted'] or 100*n<99*d:raise ArithmeticError('Raw .99 certificate required')
        cost=self.cost_of(s);record=dict(selection=list(s),cost=cost,certificate=certificate,source=source,found_seconds=time.monotonic()-self.start)
        self.pool[s]=record;self.native_cache[s]=certificate['lower'];self.decisions[s]=certificate
        if self.best is None or cost<self.best['cost']-1e-8:
            self.best=dict(record,probability=certificate['lower'],probability_evaluator=certificate['method'])
            self.events.append(dict(event='raw_certified_incumbent',cost=cost,elapsed=record['found_seconds'],source=source))
            if time.monotonic()-self.last_save>10:self.save('running')
        return certificate['lower']

    def small_exact_search(self):
        counter=SmallCounts(self.inst,self.T);total=math.prod(map(len,self.groups));digest=hashlib.sha256();seen=0;refuted=0;ambiguous=0
        choices=sorted(itertools.product(*self.groups),key=lambda s:(self.cost_of(s),s))
        for raw in choices:
            if self.remaining()<55:break
            s=tuple(map(int,raw));v=counter.count(s);seen+=1
            digest.update(json.dumps([list(s),v['lower_numerator'],v['upper_numerator']],separators=(',',':')).encode())
            if v['accepted']:self.accept(s,'cost_ordered_raw_enumeration',v)
            elif v['infeasible']:refuted+=1
            else:
                ambiguous+=1;self.native_check(s,'interval_boundary_refinement',True)
        self.exhaustive=dict(total=total,checked=seen,complete=seen==total,refuted=refuted,ambiguous=ambiguous,counts_sha256=digest.hexdigest(),raw_feasible_found=len(self.pool),no_tail_gate=True)
        del counter

    def init_frontier(self):
        super().init_frontier()
        # Cost/risk tradeoffs are retained even above the cheapest raw incumbent.
        # All proposals face precisely the same raw .99 certificate.
        end=min(self.deadline-20,time.monotonic()+min(100.,self.total_budget*.2))
        center=tuple(int(g[np.argmin(self.mu[g]+3*self.sd[g])]) for g in self.groups)
        self.native_check(center,'raw_sample_low_risk_anchor',True)
        for level in [.9999,.999,.997,.995,.993,.992,.991,.9901]:
            if time.monotonic()>end:break
            for _ in range(2):
                if time.monotonic()>end:break
                p,w=self.gradients(center);old=self.best;self.best=None
                try:qs=self.mip(-w,p-level,trust=min(16,self.inst.m),center=center,seconds=.7,pool=4)
                finally:self.best=old
                for q in qs:
                    if time.monotonic()>end:break
                    self.native_check(q,'unconstrained_cost_risk_portfolio',True)
                eligible=[s for s in self.pool if self.guide_probability(s)>=level]
                if eligible:center=min(eligible,key=lambda s:(self.cost_of(s),s))

    def shortlist(self):
        records=sorted(self.pool.values(),key=lambda r:(r['cost'],r['selection']))
        if not records:return []
        # Every certified small-case choice is retained, regardless of risk score.
        # Full external cost-order validation can therefore find the least-cost
        # member passing both predicates on these enumerated cases.
        if self.exhaustive is not None:return records
        keep={tuple(r['selection']) for r in records[:32]}
        def score(r):
            s=tuple(r['selection'])
            return self.order_scores.get(s,self.guide_cache.get(s,r['certificate']['lower']))
        for level in list(np.arange(.80,.975,.005))+list(np.arange(.975,1.,.00025)):
            for r in records:
                if score(r)>=level:keep.add(tuple(r['selection']));break
        for k in np.linspace(0,len(records)-1,min(24,len(records)),dtype=int):keep.add(tuple(records[int(k)]['selection']))
        for r in sorted(records,key=lambda r:(-score(r),r['cost']))[:8]:keep.add(tuple(r['selection']))
        return [dict(r,ordering_score=score(r)) for r in records if tuple(r['selection']) in keep]

    def run(self):
        if self.inst.m<=5 and math.prod(map(len,self.groups))<=100000:
            self.small_exact_search()
        else:
            self.init_frontier();self.local_search(min(140.,self.total_budget*.3))
            if self.best is not None:
                m=self.inst.m;ordered=list(map(int,np.argsort([-np.ptp(self.cost[g]) for g in self.groups])))
                parts=[(list(range(0,m,2)),list(range(1,m,2))),(list(range(m//2)),list(range(m//2,m))),(ordered[::2],ordered[1::2])]
                self.bins=512
                for delta in [.00025,0.,.0005,0.]:
                    for left,right in parts:
                        if self.remaining()<15:break
                        self.matching(delta,left,right)
                    if self.remaining()<15:break
                if self.remaining()>20:self.local_search(min(30.,self.remaining()-10))
        if self.best is not None:self.final_check()
        self.save('completed')

    def final_check(self):
        s=tuple(self.best['selection']);c=self.best['certificate']
        if c['method']=='outward_interval_integer_pair_count':
            v=SmallCounts(self.inst,self.T).count(s)
            if v['lower_numerator']!=c['lower_numerator'] or v['denominator']!=c['denominator']:raise ArithmeticError('Interval recount mismatch')
        else:
            n,d=self.oracle.count(s,c['bins'],True)
            if str(n)!=c['lower_numerator'] or str(d)!=c['denominator']:raise ArithmeticError('Integer recount mismatch')
        self.best['final_exact_recomputed']=True

    def save(self,status):
        self.last_save=time.monotonic()
        candidates=self.shortlist() if status=='completed' else []
        digest=hashlib.sha256()
        for s,r in sorted(self.pool.items()):digest.update(json.dumps([s,r['cost'],r['certificate']['lower_numerator'],r['certificate']['denominator']],separators=(',',':')).encode())
        data=dict(schema='CCMCKP_S10_raw_constraint_portfolio',status=status,seed=self.seed,instance=self.inst.name,capacity=self.T,selected=self.best,candidate_shortlist=candidates,raw_certified_pool_count=len(self.pool),raw_pool_sha256=digest.hexdigest(),events=self.events,models=self.models,model_seconds=self.model_seconds,match_history=self.match_history,local_history=self.local_history,exhaustive=self.exhaustive,ordering_metadata=self.tail_metadata,auxiliary_grid=self.auxiliary_grid,certificate_calls=self.oracle.calls,certificate_seconds=self.oracle.seconds,runtime_before_save=time.monotonic()-self.start,config=dict(nominal_CL=.99,raw_threshold='.99',all_original_samples=True,tail_hard_gate=False,tail_changes_to_input=False,tail_use='removed_entirely',selection='independent LSS postselector chooses lowest-cost passing member of frozen shortlist',external_real_P_threshold=.985,external_MC_seed=832273,external_MC_draws=10000000,no_dist_metadata_in_optimizer=True,no_cross_run_solutions=True,search_budget=self.total_budget,validation_outside_search_clock=True))
        atomic_json(self.out,data)

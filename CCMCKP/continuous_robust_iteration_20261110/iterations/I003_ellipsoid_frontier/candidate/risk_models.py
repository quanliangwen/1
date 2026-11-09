"""Robust subproblems propose choices; original exact .99 remains acceptance."""
import time,math
import numpy as np
from mip_backend import binary_model

def cvar_weights(losses,epsilon):
    losses=np.asarray(losses,float);n=len(losses);mass=float(epsilon)*n
    if n==0 or not 0<float(epsilon)<=1:raise ValueError('Invalid CVaR tail mass')
    order=np.argsort(-losses,kind='stable');k=int(math.floor(mass));r=mass-k;w=np.zeros(n)
    w[order[:k]]=1./mass
    if k<n and r>0:w[order[k]]=r/mass
    if abs(w.sum()-1)>1e-12 or w.max()>1/mass+1e-12:raise ArithmeticError('Invalid risk-envelope weights')
    return w

def gamma_support(deviations,gamma):
    d=np.sort(np.maximum(np.asarray(deviations,float),0.))[::-1];g=min(float(gamma),len(d));k=int(g)
    return float(d[:k].sum()+(g-k)*d[k]) if k<len(d) else float(d.sum())

class RiskProposals:
    def __init__(self,solver,seconds):
        self.s=solver;self.end=min(solver.deadline-12,time.monotonic()+max(0.,seconds));self.records=[];self.proposed=set();self.initial_pool=set(solver.pool)
    def remaining(self):return self.end-time.monotonic()
    def solve(self,rows,limits,label,seconds=.45,pool=2):
        if self.remaining()<7 or self.s.remaining()<15:return []
        start=time.monotonic();choices=binary_model(self.s.groups,self.s.inst.n,self.s.cost,rows,[-np.inf]*len(rows),limits,min(seconds,max(.01,self.remaining()-6)),pool)
        self.s.models+=1;self.s.model_seconds+=time.monotonic()-start;fresh=[]
        for q in choices:
            q=tuple(map(int,q));self.proposed.add(q)
            if q not in self.s.pool and self.remaining()>5:
                p=self.s.native_check(q,label,True);v=self.s.decisions.get(q,{})
                fresh.append(dict(selection=list(q),cost=self.s.cost_of(q),raw_lower_bound=p,certified=q in self.s.pool,outcome='certified' if q in self.s.pool else 'refuted' if v.get('infeasible') else 'unresolved',decision=v))
        self.records.append(dict(kind=label,seconds=time.monotonic()-start,choices=len(choices),checked=fresh))
        return choices
    def cvar(self):
        if self.remaining()<10:return
        rng=np.random.default_rng(self.s.seed+177013);N=2048
        A=np.column_stack([x[rng.integers(0,len(x),N)] for x in self.s.inst.samples])
        anchors=sorted(self.s.pool,key=lambda q:(self.s.cost_of(q),q))
        if not anchors:return
        for eps in [.02,.05,.01,.10]:
            for factor in [1.,1.005,1.01]:
                if self.remaining()<9:return
                q=anchors[0];cuts=[];rhs=[];risks=[]
                for iteration in range(8):
                    if self.remaining()<8:break
                    loss=A[:,list(q)].sum(axis=1);w=cvar_weights(loss,eps);risk=float(w@loss)
                    cuts.append(w@A);rhs.append(self.s.T*factor);risks.append(risk)
                    proposals=self.solve(cuts,rhs,f'CVaR_envelope_eps{eps}_Tfactor{factor}',seconds=.5,pool=2)
                    if not proposals:break
                    nextq=tuple(map(int,min(proposals,key=lambda p:(self.s.cost_of(p),p))))
                    nextloss=A[:,list(nextq)].sum(axis=1);next_risk=float(cvar_weights(nextloss,eps)@nextloss)
                    if nextq==q or next_risk<=self.s.T*factor+1e-8:break
                    q=nextq
                self.records.append(dict(kind='CVaR_cut_path',epsilon=eps,threshold_factor=factor,cuts=len(cuts),risk_trace=risks,scenario_count=N))
    def gamma(self):
        if self.remaining()<9:return
        for quantile in [.9,.95,.99]:
            d=np.array([max(0.,np.quantile(x,quantile)-x.mean()) for x in self.s.inst.samples]);pivots=np.unique(np.r_[0.,np.quantile(d,[.1,.3,.5,.7,.9,1.])])
            for gamma in [.5,1.,2.,3.,5.,8.]:
                if gamma>self.s.inst.m:continue
                for pivot in pivots:
                    if self.remaining()<8:return
                    row=self.s.mu+np.maximum(d-pivot,0.)
                    self.solve([row],[self.s.T-gamma*pivot],f'Gamma_box_q{quantile}_G{gamma}_pi{float(pivot):.6g}',seconds=.25,pool=2)
    def summary(self):
        return dict(proposals=len(self.proposed),new_certified=len(set(self.s.pool)-self.initial_pool),initial_certified=len(self.initial_pool),final_certified=len(self.s.pool),records=self.records,acceptance_unchanged='raw exact .99 plus external original LSS .985',external_data_used=False)

"""Robust CDF-guided neighborhoods around multiple raw-risk portfolio centers.

Unlike the baseline's cost cap at the cheapest raw-feasible member, each local
subproblem may improve any independently generated portfolio center. No true
distribution or validation result chooses these centers.
"""
import time
import numpy as np
from engine import worst_cdf_hist,truncated_convolution
from risk_models import RiskProposals

def cdf_gradients(groups,hist,selection):
    B=hist.shape[1];m=len(groups);unit=np.r_[1.,np.zeros(B-1)];pref=[unit];suff=[None]*(m+1);suff[m]=unit
    for j in selection:pref.append(truncated_convolution(pref[-1],hist[j],B))
    for g in range(m-1,-1,-1):suff[g]=truncated_convolution(hist[selection[g]],suff[g+1],B)
    p=float(pref[-1].sum());weights=np.zeros(len(hist))
    for g in range(m):
        rest=truncated_convolution(pref[g],suff[g+1],B);cdf=np.cumsum(rest)[::-1]
        weights[groups[g]]=hist[groups[g]]@cdf-p
    return p,weights

class PortfolioLNS(RiskProposals):
    def run(self):
        if not self.s.pool:return
        start=time.monotonic();records=sorted(self.s.pool.values(),key=lambda r:(r['cost'],r['selection']));centers=[];seen=set()
        def add(r):
            q=tuple(r['selection'])
            if q not in seen:seen.add(q);centers.append(q)
        for level in [.995,.992,.999,.9901,.997,.993,.9995,.991,.9999]:
            eligible=[r for r in records if r['certificate']['lower']>=level]
            if eligible:add(eligible[0])
        for k in np.linspace(0,len(records)-1,min(7,len(records)),dtype=int):add(records[int(k)])
        B=2048;histograms={d:np.asarray([worst_cdf_hist(a,self.s.T,B,d) for a in self.s.inst.samples]) for d in [0.,.00025,.0005]}
        for center in centers:
            if self.remaining()<10:break
            mask=np.zeros(self.s.inst.n);mask[list(center)]=1.;cap=self.s.cost_of(center)-1e-7
            for delta in [0.,.00025,.0005]:
                if self.remaining()<9:break
                p,w=cdf_gradients(self.s.groups,histograms[delta],center)
                for trust in [2,4,8]:
                    for drop in [.0005,.002,.005]:
                        if self.remaining()<8:break
                        target=max(.99 if delta==0. else .95,p-drop)
                        self.solve([self.s.cost,-w,-mask],[cap,p-target,-(self.s.inst.m-trust)],f'robust_CDF_portfolio_delta{delta}_trust{trust}_drop{drop}',seconds=.3,pool=2)
                self.records.append(dict(kind='portfolio_center',selection=list(center),cost=cap+1e-7,delta=delta,model_probability=p,raw_certificate=self.s.pool[center]['certificate']['lower']))
        self.records.append(dict(kind='portfolio_LNS_total',initial_centers=len(centers),bins=B,seconds=time.monotonic()-start,final_raw_threshold=.99,uncertainty_model='finite-support lower-CDF mass shift, proposal only'))

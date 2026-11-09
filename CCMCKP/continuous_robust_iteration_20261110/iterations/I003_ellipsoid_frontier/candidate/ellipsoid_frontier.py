"""Ellipsoidal uncertainty support with adaptive variance-band relaxations.

For independent item-coordinate deviations a=mu+diag(sd)u, ||u||_2<=k,
the support at a binary one-choice-per-group vector is mu*x+k*sqrt(var*x).
Secants of sqrt give lower bounds within a variance band. These MILPs only
propose candidates; neither this surrogate nor k certifies a chance constraint.
The unchanged exact empirical oracle and separate original LSS decide acceptance.
"""
import time,math
import numpy as np
from risk_models import RiskProposals

def sqrt_secant(lo,hi):
    if lo<0 or hi<=lo:raise ValueError('Invalid variance interval')
    a=1./(math.sqrt(hi)+math.sqrt(lo));b=math.sqrt(lo)-a*lo
    return a,b

class EllipsoidFrontier(RiskProposals):
    def run(self):
        v=np.maximum(self.s.var,0.);groups=self.s.groups
        lo=float(sum(v[g].min() for g in groups));hi=float(sum(v[g].max() for g in groups))
        if hi<=lo+1e-12:return
        # Global range comes exclusively from this run's sample variances.
        edges=np.geomspace(max(lo,hi*1e-7),hi,9)
        edges[0]=lo
        radii=[2.3,2.,2.5,1.8,2.7,2.15,3.,1.6,2.4,3.3]
        queues={k:[(float(a),float(b),0) for a,b in zip(edges[:-1],edges[1:])] for k in radii}
        counts={k:0 for k in radii};rounds=0
        while self.remaining()>9 and any(queues.values()):
            rounds+=1
            for k in radii:
                if self.remaining()<9:break
                if not queues[k]:continue
                lower,upper,depth=queues[k].pop(0);a,b=sqrt_secant(lower,upper)
                qs=self.solve([self.s.mu+k*a*v,v,-v],[self.s.T-k*b,upper,-lower],f'ellipsoid_k{k}_band{lower:.8g}_{upper:.8g}_d{depth}',seconds=.4,pool=3)
                counts[k]+=1
                self.records.append(dict(kind='ellipsoid_band',radius=k,variance_lower=lower,variance_upper=upper,depth=depth,secant_slope=a,secant_intercept=b,returned_variances=[float(v[list(q)].sum()) for q in qs],bound_role='sqrt secant is lower bound; proposal-only, no original-problem optimality claim'))
                if depth<2 and qs:
                    actual=float(v[list(qs[0])].sum());mid=actual if lower+.2*(upper-lower)<actual<upper-.2*(upper-lower) else (lower+upper)/2
                    queues[k].extend([(lower,mid,depth+1),(mid,upper,depth+1)])
        self.records.append(dict(kind='ellipsoid_frontier_total',global_variance_range=[lo,hi],radii=radii,models_per_radius=counts,rounds=rounds,remaining_bands=sum(map(len,queues.values())),uncertainty_set='a=mu+diag(sd)u, ||u||2<=radius',no_population_confidence_claim=True,acceptance='unchanged exact empirical .99 and separate original LSS .985'))

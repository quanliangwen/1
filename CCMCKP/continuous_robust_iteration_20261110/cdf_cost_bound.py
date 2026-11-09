"""Exploratory cost-discounted optimistic CDF envelope.

Only positive direct convolutions, no Fourier cancellation. Floating arithmetic
is diagnostic, not an infeasibility or global-optimality certificate. Input-only
module; no original distribution, historical selection or validation cache.
"""
import math
import numpy as np

def item_cdfs(samples,capacity,bins):
    if bins<2 or capacity<=0:raise ValueError('Invalid grid')
    out=[]
    for values in samples:
        values=np.asarray(values,float)
        if values.min()<0:raise ValueError('Nonnegative samples required')
        # Floating floor projection is optimistic but not a rigorous arithmetic
        # enclosure. Integer/rational quantization is needed for proof claims.
        q=np.minimum(bins+1,np.floor(values/capacity*bins).astype(int))
        out.append(np.cumsum(np.bincount(q,minlength=bins+2)[:bins+1])/len(values))
    return np.asarray(out)

def envelope_pmfs(groups,cost,cdfs,lam,fixed=None):
    if lam<0:raise ValueError('Nonnegative multiplier required')
    cost=np.asarray(cost,float);pmfs=[];minimum=0.;fixed={} if fixed is None else fixed
    for g,group in enumerate(groups):
        group=np.asarray(group,int);c0=float(cost[group].min());minimum+=c0
        ids=np.asarray([fixed[g]],int) if g in fixed else group
        if not all(int(j) in group for j in ids):raise ValueError('Invalid fixed item')
        weights=np.exp(-lam*(cost[ids]-c0))
        envelope=np.max(weights[:,None]*cdfs[ids],axis=0)
        h=np.diff(np.r_[0.,envelope])
        if h.min() < -1e-13:raise ArithmeticError('Nonmonotone envelope')
        pmfs.append(np.maximum(h,0.))
    return pmfs,minimum

def positive_log_convolution_mass(pmfs,limit):
    p=np.array([1.]);logscale=0.
    for h in pmfs:
        h=np.asarray(h,float);mass=float(h.sum())
        if not mass>0:return None
        p=np.convolve(p,h/mass)[:limit+1]
        retained=float(p.sum())
        if not retained>0:return None
        logscale+=math.log(mass)+math.log(retained);p/=retained
    return logscale

def diagnostic_bound(groups,cost,cdfs,capacity_cost,lam,fixed=None):
    pmfs,minimum=envelope_pmfs(groups,cost,cdfs,lam,fixed)
    if capacity_cost<minimum:return dict(dual_multiplier=lam,log_upper=None,upper=None,status='empty cost range',proof=False)
    logmass=positive_log_convolution_mass(pmfs,cdfs.shape[1]-1)
    if logmass is None:return dict(dual_multiplier=lam,log_upper=None,upper=None,status='numerically unresolved zero mass',proof=False)
    logupper=lam*(capacity_cost-minimum)+logmass
    return dict(dual_multiplier=float(lam),log_upper=logupper,upper=math.exp(min(0.,logupper)),envelope_log_mass=logmass,status='floating diagnostic only',proof=False)

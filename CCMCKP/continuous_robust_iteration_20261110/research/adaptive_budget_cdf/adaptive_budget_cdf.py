"""Diagnostic adaptive-policy upper relaxation of fixed-choice chance CDF.

Costs/time are rounded down. A relaxed policy may choose remaining items after
seeing current weight; hence it dominates fixed nonadaptive selections. This
FLOAT FFT implementation is exploratory only and MUST NOT prune proof nodes.
"""
import numpy as np
from scipy.fft import rfft,irfft,next_fast_len

def adaptive_upper(groups,cost,cdfs,limit,cost_bins,reverse=False):
 cost=np.asarray(cost,float);K=int(cost_bins);B=cdfs.shape[1]-1
 minima=[min(cost[g]) for g in groups];delta=float(limit)-sum(minima)
 if delta<0:return 0.
 weights=np.diff(np.c_[np.zeros(len(cost)),cdfs],axis=1)
 U=np.ones((K+1,B+1));length=next_fast_len(2*B+1)
 order=list(range(len(groups)))
 if reverse:order.reverse()
 for g in order:
  transformed=rfft(U,n=length,axis=1);new=np.zeros_like(U)
  for j in groups[g]:
   excess=cost[j]-minima[g]
   units=(0 if excess==0 else K+1) if delta==0 else int(np.floor(excess*K/delta))
   if units>K:continue
   h=rfft(weights[j],n=length)
   values=irfft(transformed[:K+1-units]*h,n=length,axis=1)[:,:B+1]
   np.maximum(new[units:],values,out=new[units:])
  U=np.clip(new,0.,1.)
 return float(U[K,B])

"""Batch finite-grid CDF guidance for small instances. Guidance only.
Two half convolutions reduce 100000 full FFT evaluations to 1100 prefix
convolutions plus a matrix product. A deadline bounds auxiliary work.
"""
import itertools,time
import numpy as np
from engine import truncated_convolution

def all_small_guides(groups,hist,deadline):
    B=hist.shape[1];split=len(groups)//2
    def half(gs):
        choices=[()];pdf=np.ones((1,B));pdf[0,1:]=0.
        for depth,g in enumerate(gs):
            next_choices=[];rows=[]
            for prefix,a in zip(choices,pdf):
                if time.monotonic()>=deadline:return None,None
                for item in g:
                    rows.append(hist[int(item)].copy() if depth==0 else truncated_convolution(a,hist[int(item)],B))
                    next_choices.append(prefix+(int(item),))
            pdf=np.asarray(rows);choices=next_choices
        return choices,pdf
    left,lp=half(groups[:split])
    if left is None:return {},False
    right,rp=half(groups[split:])
    if right is None:return {},False
    rcdf=np.ascontiguousarray(np.cumsum(rp,axis=1)[:,::-1]);del rp
    scores={}
    for start in range(0,len(left),8):
        if time.monotonic()>=deadline:return scores,False
        values=np.clip(lp[start:start+8]@rcdf.T,0.,1.)
        for a,row in zip(left[start:start+8],values):
            for b,p in zip(right,row):scores[a+b]=float(p)
    return scores,True

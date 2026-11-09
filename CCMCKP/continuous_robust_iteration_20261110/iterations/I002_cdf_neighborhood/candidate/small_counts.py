"""Certified integer counts from outward IEEE-754 sample-sum intervals.

Each decimal input is enclosed by the adjacent doubles around its correctly
rounded conversion. Every addition/subtraction is rounded outward one ulp.
Thus every counted upper-sum pair is certainly below the original decimal T.
No approximate probability or Monte Carlo decides acceptance.
"""
import math
import numpy as np

class SmallCounts:
    def __init__(self, inst, capacity):
        self.inst=inst; self.split=inst.m//2; self.cache={}
        self.tlo=np.nextafter(float(capacity),-np.inf)
        self.thi=np.nextafter(float(capacity),np.inf)
    def half(self, s):
        s=tuple(s)
        if s not in self.cache:
            lo=np.zeros(1);hi=np.zeros(1)
            for j in s:
                a=self.inst.samples[j]
                lo=np.nextafter(lo[:,None]+np.nextafter(a,-np.inf)[None,:],-np.inf).reshape(-1)
                hi=np.nextafter(hi[:,None]+np.nextafter(a,np.inf)[None,:],np.inf).reshape(-1)
            self.cache[s]=(np.sort(lo),np.sort(hi))
        return self.cache[s]
    def count(self, s):
        al,au=self.half(s[:self.split]);bl,bu=self.half(s[self.split:])
        lower=int(np.searchsorted(bu,np.nextafter(self.tlo-au,-np.inf),side='left').sum())
        upper=int(np.searchsorted(bl,np.nextafter(self.thi-al,np.inf),side='left').sum())
        den=len(al)*len(bl)
        return dict(selection=list(s),lower_numerator=str(lower),upper_numerator=str(upper),denominator=str(den),lower=lower/den,upper=upper/den,accepted=100*lower>=99*den,infeasible=100*upper<99*den,search_threshold='99/100',method='outward_interval_integer_pair_count',all_original_samples=True,strict_event='sum<T')

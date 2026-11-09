"""Exact empirical feasibility certificates via integer polynomial counts.
All source decimal samples are included. No statistical acceptance or FP guard.
"""
from fractions import Fraction
from pathlib import Path
import math,time
import numpy as np
from flint import fmpz_poly

class ExactOracle:
    def __init__(self,inst,capacity,target="0.99"):
        self.target=Fraction(str(target));self.inst=inst;self.cap=Fraction(str(capacity));self.raw={};self.indices={};self.certificates={};self.calls=0;self.seconds=0.
    def fractions(self,j):
        if j not in self.raw:
            lines=(self.inst.path/f'{j}_sample.txt').read_text().split()
            a=[Fraction(x) for x in lines]
            if not a or any(x<0 for x in a):raise ValueError('Nonnegative nonempty source samples required')
            self.raw[j]=a
        return self.raw[j]
    def quantized(self,j,bins,up):
        key=(int(j),bins,up)
        if key not in self.indices:
            out=[];tn=self.cap.numerator;td=self.cap.denominator
            for a in self.fractions(j):
                n=a.numerator*bins*td;d=a.denominator*tn
                q=(n+d-1)//d if up else n//d
                out.append(min(bins,q))
            self.indices[key]=np.asarray(out,dtype=np.int64)
        return self.indices[key]
    def count(self,s,bins,up):
        arrays=[self.quantized(j,bins,up) for j in s];offset=sum(int(a.min()) for a in arrays);cut=bins-offset
        den=math.prod(len(a) for a in arrays)
        if cut<=0:return 0,den
        if sum(int(a.max()) for a in arrays)<bins:return den,den
        polys=[]
        for a in arrays:
            ix=a-int(a.min());ix=ix[ix<cut]
            coeff=np.bincount(ix).tolist() if len(ix) else []
            polys.append(fmpz_poly(coeff))
        while len(polys)>1:
            polys=[(polys[k]*polys[k+1]).truncate(cut) if k+1<len(polys) else polys[k] for k in range(0,len(polys),2)]
        num=int(polys[0](1))
        if not 0<=num<=den:raise ArithmeticError('Invalid exact count')
        return num,den
    def certify(self,s,bins,include_upper=False):
        s=tuple(self.inst.validate_selection(s));key=(s,bins,include_upper)
        if key in self.certificates:return self.certificates[key]
        t=time.monotonic();num,den=self.count(s,bins,True)
        result=dict(selection=list(s),bins=bins,lower_numerator=str(num),denominator=str(den),lower=float(Fraction(num,den)),accepted=self.target.denominator*num>=self.target.numerator*den,search_threshold=str(self.target),method='exact_integer_upward_grid_count',all_original_samples=True,strict_event='sum<T')
        if include_upper:
            upper,d2=self.count(s,bins,False);assert den==d2 and num<=upper
            result.update(upper_numerator=str(upper),upper=float(Fraction(upper,den)),infeasible=self.target.denominator*upper<self.target.numerator*den)
        result['certificate_seconds']=time.monotonic()-t;self.calls+=1;self.seconds+=result['certificate_seconds'];self.certificates[key]=result
        return result

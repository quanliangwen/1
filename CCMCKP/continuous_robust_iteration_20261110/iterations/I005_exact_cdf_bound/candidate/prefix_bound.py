"""Exact optimistic-CDF branch bound for original empirical chance feasibility.

This certifies exclusion only for the declared decimal cost line and raw >=.99
predicate, and never claims LSS qualification for a raw candidate. Unassigned
groups use a CDF upper envelope; all counts use exact rational floor projections
and integer polynomial convolutions. Cost comparisons use source decimal costs.
"""
import time,math,json,gzip
from fractions import Fraction
from pathlib import Path
import numpy as np
from flint import fmpz_poly
from exact_oracle import ExactOracle

class PrefixBound:
    def __init__(self,inst,capacity,cost_limit,bins,seconds,out):
        self.inst=inst;self.T=Fraction(str(capacity));self.C=Fraction(str(cost_limit));self.B=int(bins);self.K=self.B+1;self.out=Path(out);self.start=time.monotonic();self.end=self.start+seconds
        self.cost=[Fraction(s) for s in (inst.path/'cost.txt').read_text().split()]
        self.groups=[list(map(int,g)) for g in inst.groups];self.m=len(self.groups);self.order=list(range(self.m));self.oracle=ExactOracle(inst,capacity,'.99');self.items={};self.env=[];self.denoms=[]
        if len(self.cost)!=inst.n or self.B<8 or self.T<=0:raise ValueError('Invalid proof input')
        for group in self.groups:
            arrays={j:self.oracle.fractions(j) for j in group};D=math.lcm(*(len(x) for x in arrays.values()));cdfs=[]
            for j in group:
                h=[0]*self.K
                for x in arrays[j]:
                    q=(x.numerator*self.B*self.T.denominator)//(x.denominator*self.T.numerator)
                    if q<=self.B:h[q]+=D//len(arrays[j])
                self.items[j]=fmpz_poly(h);cdfs.append(np.cumsum(h,dtype=object))
            cdf=np.max(np.asarray(cdfs,dtype=object),axis=0);pmf=[int(cdf[0])]+[int(cdf[k]-cdf[k-1]) for k in range(1,self.K)]
            if min(pmf)<0 or sum(pmf)>D:raise ArithmeticError('Invalid optimistic CDF')
            self.env.append(fmpz_poly(pmf));self.denoms.append(D)
        self.D=math.prod(self.denoms);self.suffix=[None]*(self.m+1);self.suffix[-1]=fmpz_poly([1]);self.min_remaining=[Fraction(0)]*(self.m+1)
        for g in range(self.m-1,-1,-1):
            self.suffix[g]=(self.env[g]*self.suffix[g+1]).truncate(self.K)
            self.min_remaining[g]=self.min_remaining[g+1]+min(self.cost[j] for j in self.groups[g])
        self.total=math.prod(map(len,self.groups));self.visited=0;self.covered=0;self.counts=dict(cost=0,cdf=0,raw_refuted=0,raw_accepted=0,unresolved=0);self.candidates=[]

    def upper_count(self,poly,depth):
        n=int((poly*self.suffix[depth]).truncate(self.K)(1))
        if not 0<=n<=self.D:raise ArithmeticError('Invalid integer upper bound')
        return n

    def run(self):
        stack=[((),fmpz_poly([1]),Fraction(0))];log=self.out.with_name(self.out.name+'.proof.jsonl.gz');status='budget_exhausted'
        with gzip.open(log,'xt',encoding='utf8') as f:
            def terminal(prefix,kind,**extra):
                cover=math.prod(len(g) for g in self.groups[len(prefix):]);self.covered+=cover;self.counts[kind]+=1
                f.write(json.dumps(dict(prefix=list(prefix),kind=kind,cover=cover,**extra),separators=(',',':'))+'\n')
            while stack and time.monotonic()<self.end-2:
                prefix,poly,cost=stack.pop();depth=len(prefix);self.visited+=1
                least=cost+self.min_remaining[depth]
                if least>self.C:terminal(prefix,'cost',minimum_completion_cost=str(least));continue
                numerator=self.upper_count(poly,depth)
                if 100*numerator<99*self.D:terminal(prefix,'cdf',upper_numerator=str(numerator),denominator=str(self.D));continue
                if depth==self.m:
                    decision=None;last_check=None
                    for bins in [1024,4096,16384,65536,262144,1048576]:
                        if time.monotonic()>self.end-2:break
                        if bins>=262144 and self.end-time.monotonic()<20:break
                        value=self.oracle.certify(prefix,bins,True)
                        last_check=value
                        if value['accepted'] or value['infeasible']:decision=value;break
                    if decision is None:terminal(prefix,'unresolved',cost=str(cost),last_certificate=last_check);continue
                    if decision['accepted']:
                        candidate=dict(selection=list(prefix),cost_decimal=str(cost),certificate=decision,LSS_qualified=False)
                        self.candidates.append(candidate);terminal(prefix,'raw_accepted',candidate=candidate);status='found_raw_feasible';break
                    terminal(prefix,'raw_refuted',cost=str(cost),certificate=decision);continue
                for j in sorted(self.groups[depth],key=lambda j:(self.cost[j],j),reverse=True):
                    stack.append((prefix+(j,),(poly*self.items[j]).truncate(self.K),cost+self.cost[j]))
        if not stack and status!='found_raw_feasible':status='exhausted'
        pending=[dict(prefix=list(p),cost=str(c)) for p,_,c in stack];remaining=sum(math.prod(len(g) for g in self.groups[len(p):]) for p,_,_ in stack)
        if self.covered+remaining!=self.total:raise ArithmeticError('Proof coverage accounting mismatch')
        excluded=status=='exhausted' and self.counts['raw_accepted']==0 and self.counts['unresolved']==0
        result=dict(schema='I005_exact_optimistic_CDF_prefix_proof',status=status,instance=self.inst.name,capacity=str(self.T),cost_limit=str(self.C),cost_semantics='exact source decimal costs and declared decimal limit, inclusive <=',raw_predicate='original independent empirical marginals; strict sum<T probability>=.99',upper_predicate='integer floor grid inclusive sum<=B, optimistic CDF max for every unassigned group',bins=self.B,denominator=str(self.D),group_order=self.order,groups=self.groups,total_combinations=str(self.total),visited_nodes=self.visited,terminal_counts=self.counts,covered_combinations=str(self.covered),remaining_combinations=str(remaining),pending_frontier=pending,candidates=self.candidates,raw_cost_line_excluded=excluded,joint_exclusion_implication=excluded,LSS_calls=0,elapsed=time.monotonic()-self.start,all_original_samples=True,tail_hard_gate_added=False,proof_log=log.name)
        with self.out.open('x') as f:json.dump(result,f,indent=2)
        return result

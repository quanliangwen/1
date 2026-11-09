"""Joint two-group finite-support robust-CDF exchange, no linearization.

Exponential tilting and a Fourier linear functional evaluate all alternative
pairs against the same rest distribution. These are floating guidance scores,
never feasibility certificates. Final unchanged integer counts are mandatory.
"""
import time
import numpy as np
from engine import worst_cdf_hist
from risk_models import RiskProposals

def tilted_fourier(hist,alpha=16.):
    B=hist.shape[1];N=2*B
    F=np.fft.rfft(hist*np.exp(-alpha*np.arange(B)/B),N,axis=1)
    target=np.r_[np.exp(alpha*np.arange(B)/B),np.zeros(B)]
    W=np.conj(np.fft.rfft(target,N))/N;W[1:-1]*=2.
    return F,W

def pair_scores(F,W,rest,left,right):
    return np.real((F[left]*(rest*W))@F[right].T)

class RobustPairs(RiskProposals):
    def run(self):
        B=4096;records=sorted(self.s.pool.values(),key=lambda r:(r['cost'],r['selection']));centers=[];seen=set()
        def add(r):
            q=tuple(r['selection'])
            if q not in seen:seen.add(q);centers.append(q)
        for level in [.995,.992,.999,.9901,.997,.993,.9995,.991]:
            eligible=[r for r in records if r['certificate']['lower']>=level]
            if eligible:add(eligible[0])
        for k in np.linspace(0,len(records)-1,min(5,len(records)),dtype=int):add(records[int(k)])
        if not centers:return
        groups=self.s.groups;m=len(groups);histograms={}
        for delta in [0.,.00025,.0005]:
            if self.remaining()<12:break
            hist=np.asarray([worst_cdf_hist(a,self.s.T,B,delta) for a in self.s.inst.samples]);F,W=tilted_fourier(hist);histograms[delta]=(F,W)
            for center in list(centers):
                if self.remaining()<10:break
                start=time.monotonic();chosen=F[list(center)];pref=[np.ones(B+1,complex)];suffix=[None]*(m+1);suffix[m]=np.ones(B+1,complex)
                for f in chosen:pref.append(pref[-1]*f)
                for g in range(m-1,-1,-1):suffix[g]=chosen[g]*suffix[g+1]
                p=float(np.real(pref[-1]@W));cap=self.s.cost_of(center);candidates={};pairs_seen=0
                floor=max(.985 if delta==0. else .95,p-.005)
                for ga in range(m-1):
                    middle=np.ones(B+1,complex)
                    for gb in range(ga+1,m):
                        if self.remaining()<8:break
                        rest=pref[ga]*middle*suffix[gb+1];left=groups[ga];right=groups[gb]
                        probs=pair_scores(F,W,rest,left,right)
                        costs=cap-self.s.cost[center[ga]]-self.s.cost[center[gb]]+self.s.cost[left,None]+self.s.cost[right][None,:]
                        eligible=(costs<cap-1e-7)&(probs>=floor)
                        # Keep both risk layers and low-cost pairs; this is a proposal
                        # queue, not an assertion that the best pair is globally best.
                        for target in [floor,max(floor,p-.002),max(floor,p-.0005),p,min(.99999,p+.002)]:
                            idx=np.flatnonzero(eligible&(probs>=target))
                            for j in sorted(idx,key=lambda j:(costs.flat[j],-probs.flat[j],int(j)))[:3]:
                                a,b=np.unravel_index(j,costs.shape);q=list(center);q[ga]=int(left[a]);q[gb]=int(right[b]);q=tuple(q)
                                if q not in self.s.decisions:candidates[q]=(float(costs[a,b]),float(probs[a,b]))
                        pairs_seen+=1;middle*=chosen[gb]
                    if self.remaining()<8:break
                selected=[];selected_set=set()
                for target in [p,max(floor,p-.0005),max(floor,p-.002),floor,min(.99999,p+.002)]:
                    for q in sorted((q for q in candidates if candidates[q][1]>=target),key=lambda q:(candidates[q][0],-candidates[q][1],q))[:16]:
                        if q not in selected_set:selected_set.add(q);selected.append(q)
                checks=[]
                for q in selected:
                    if self.remaining()<6:break
                    self.proposed.add(q);self.s.native_check(q,f'joint_robust_pair_delta{delta}',True)
                    v=self.s.decisions.get(q,{})
                    checks.append(dict(selection=list(q),cost=candidates[q][0],guide_probability=candidates[q][1],certified=q in self.s.pool,outcome='certified' if q in self.s.pool else 'refuted' if v.get('infeasible') else 'unresolved',decision=v))
                self.records.append(dict(kind='joint_pair_neighborhood',center=list(center),center_cost=cap,delta=delta,center_guide=p,bins=B,pairs_checked=pairs_seen,possible_group_pairs=m*(m-1)//2,complete_pair_scan=pairs_seen==m*(m-1)//2,eligible_proposals=len(candidates),checked=checks,seconds=time.monotonic()-start,score_role='floating worst-CDF guidance; independent exact acceptance only'))
        self.records.append(dict(kind='robust_pair_total',centers=len(centers),grid_bins=B,final_hard_gate_added=False,external_data_used=False))

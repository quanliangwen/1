"""Proposal-only third-group repair of an own two-group move under own center cost.

Floating finite-support CDF scores select proposals; exact original empirical
certification and external original LSS acceptance remain separate and unchanged.
"""
import numpy as np
from portfolio_lns import cdf_gradients

def propose(groups,cost,hist,center,pair,per_layer=3):
 center=tuple(center);pair=tuple(pair)
 if len(center)!=len(groups) or len(pair)!=len(groups) or any(center[g] not in groups[g] or pair[g] not in groups[g] for g in range(len(groups))):raise ValueError('Canonical own center/pair required')
 changed={g for g in range(len(groups)) if center[g]!=pair[g]}
 if len(changed)!=2:raise ValueError('Exactly two changed groups required')
 cap=float(sum(cost[j] for j in center));base=float(sum(cost[j] for j in pair));p,w=cdf_gradients(groups,hist,pair);rows=[]
 for g,group in enumerate(groups):
  if g in changed:continue
  for j in group:
   if j==pair[g]:continue
   c=base-float(cost[pair[g]])+float(cost[j]);guide=p+float(w[j]);q=list(pair);q[g]=int(j)
   if c<cap-1e-7:rows.append(dict(selection=q,cost=c,guide_probability=guide,third_group=g))
 selected={}
 for layer,target in enumerate([p,min(1.,max(.99,p+.0005)),min(1.,max(.992,p+.001))]):
  for row in sorted((r for r in rows if r['guide_probability']>=target),key=lambda r:(r['cost'],-r['guide_probability'],r['selection']))[:per_layer]:
   q=tuple(row['selection'])
   if q not in selected:selected[q]=dict(row,layers=[],layer_targets=[],pair_guide=p,center_cost_cap=cap)
   selected[q]['layers'].append(layer);selected[q]['layer_targets'].append(target)
 return list(selected.values())

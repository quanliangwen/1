"""Exact necessary risk-budget relaxation, never an added final tail gate.

Let ag be the global minimum support in group g. If selected Xg >=
T-sum(ah,h!=g), then sum>=T, violating the fixed raw strict event.
With marginal probabilities qg, raw success <=product(1-qg)<=1/(1+sum qg).
Raw success>=99/100 therefore requires sum qg<=1/99. Scale by a common
sample denominator D: integer risk budget floor(D/99). Min-cost DP under
this necessary condition is a lower bound, not a feasible solution.
"""
from pathlib import Path
from fractions import Fraction
from bisect import bisect_left
import json,pickle,math,time
H=Path(__file__).parent;cases=json.load(open(H/'CASES.json'));base={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};models={};rows=[];start=time.monotonic()
for c in cases:
 if c['index'] not in [30,32,35,37,38,39,40]:continue
 p=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance']
 if c['instance'] not in models:
  cost=[Fraction(x) for x in (p/'cost.txt').read_text().split()];groups=pickle.load(open(p/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;samples={j:sorted(Fraction(x) for x in (p/f'{j}_sample.txt').read_text().split()) for g in groups for j in g};models[c['instance']]=(cost,groups,samples)
 cost,groups,samples=models[c['instance']];mins=[min(samples[j][0] for j in g) for g in groups];support_sum=sum(mins,Fraction(0));T=Fraction(str(c['tmax']));D=math.lcm(*(len(a) for a in samples.values()));budget=D//99;dp=[None]*(budget+1);dp[0]=Fraction(0);counts=[]
 for g,group in enumerate(groups):
  threshold=T-(support_sum-mins[g]);risk={j:(len(samples[j])-bisect_left(samples[j],threshold))*(D//len(samples[j])) for j in group};counts.append([risk[j] for j in group]);next_dp=[None]*(budget+1)
  for used,value in enumerate(dp):
   if value is None:continue
   for j in group:
    q=used+risk[j]
    if q>budget:continue
    candidate=value+cost[j]
    if next_dp[q] is None or candidate<next_dp[q]:next_dp[q]=candidate
  dp=next_dp
 valid=[v for v in dp if v is not None];lower=min(valid) if valid else None
 rows.append(dict(index=c['index'],T=str(T),sample_denominator=D,necessary_integer_risk_budget=budget,risk_counts=counts,cost_lower_exact=str(lower) if lower is not None else None,cost_lower_float=float(lower) if lower is not None else None,old_cost=base[c['index']]['old_best'],S10_cost=base[c['index']]['new_avg'],role='necessary-only relaxation, not raw or LSS qualification; original samples only, no tail reconstruction'))
(H/'NECESSARY_ITEM_BOUND_DIAGNOSTIC.json').write_text(json.dumps(dict(rows=rows,seconds=time.monotonic()-start,claim='mathematically necessary risk-budget cost relaxation; a low lower bound cannot establish feasibility'),indent=2));print(json.dumps([(r['index'],r['cost_lower_float'],r['old_cost']) for r in rows]))

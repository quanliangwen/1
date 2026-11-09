import pathlib,json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
H=pathlib.Path(__file__).resolve().parent;S=json.load(open(H/'USER_VALIDATION_SUMMARY.json'));rows=S['rows']
if len(rows)!=40 or S['lss_accepted']!=1200 or S['all_30_accepted_cases']!=40:raise RuntimeError('Plot requires all 1200 LSS-accepted final runs')
x=np.arange(40);gap=np.array([r['gap_to_old_best_pct'] for r in rows]);old=np.array([r['old_CDF_Best_real_probability'] for r in rows]);new=np.array([r['probability_min'] for r in rows]);labels=[('L' if r['index']<=20 else 'A')+f"{(r['index']-1)%20+1:02d}" for r in rows]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
fig,(a,b)=plt.subplots(2,1,figsize=(16,8),sharex=True,gridspec_kw={'height_ratios':[1.3,1]})
colors=np.where(gap<=1e-8,'#287a8e','#e9983d');a.bar(x,gap,color=colors,width=.72);a.axhline(0,color='#333333',lw=1);a.set_ylabel('Final Avg / old CDF Best - 1 (%)');a.set_title('CCMCKP: 40 cases x 30 independent searches; LSS-aligned final acceptance')
for k,v in enumerate(gap):
 if v>10:a.text(k,v+1.5,f'{v:.1f}',ha='center',va='bottom',fontsize=8)
a.set_ylim(min(-3,float(gap.min())-2),float(gap.max())+10);a.grid(axis='y',alpha=.18);a.set_axisbelow(True)
from matplotlib.patches import Patch
a.legend(handles=[Patch(color='#287a8e',label='Avg <= old CDF Best'),Patch(color='#e9983d',label='Avg > old CDF Best')],loc='upper left',frameon=False)
b.scatter(x,old,marker='x',s=35,color='#b55044',label='Old CDF Best: LSS real probability');b.scatter(x,new,marker='o',s=24,color='#287a8e',label='Final: minimum over 30 runs');b.axhline(.985,color='#333333',ls='--',lw=1,label='LSS acceptance >= 0.985');b.set_ylim(max(0,float(old.min())-.015),1.008);b.yaxis.set_major_formatter(PercentFormatter(1));b.set_ylabel('Original LSS real_P_test');b.grid(axis='y',alpha=.18);b.set_axisbelow(True);b.legend(loc='lower left',frameon=False,ncol=3)
for ax in [a,b]:ax.axvline(19.5,color='#777777',lw=.8,ls=':');ax.set_xlim(-.8,39.8)
b.set_xticks(x);b.set_xticklabels(labels,rotation=90,fontsize=8);b.set_xlabel('L01-L20: LAB cases 1-20; A01-A20: APP cases 21-40 (see results table for capacities)')
fig.text(.01,.005,f"LSS probability accepted: {S['lss_accepted']}/1200. Total-time overruns: {S['total_budget_overrun_count']}. Original LSS: 10,000,000 draws, seed 832273, sum<=T. Unique deterministic final MC calls: {S['unique_MC_calls']}.",fontsize=9)
fig.tight_layout(rect=[0,.025,1,1]);fig.savefig(H/'cost_and_probability.png',dpi=200);fig.savefig(H/'cost_and_probability.svg');plt.close(fig)

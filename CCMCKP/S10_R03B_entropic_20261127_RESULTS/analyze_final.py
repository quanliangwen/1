from pathlib import Path
from collections import Counter
from fractions import Fraction
import json,statistics,base64,hashlib,math
R=Path(__file__).resolve().parent;E=R/'evidence';read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
a=read(E/'formal/FINAL_INDEPENDENT_AUDIT.json');assert a['terminal']==360 and not a['global_errors']
protocol=read(E/'formal/PROTOCOL.json');case_names={c['index']:c['instance'] for c in protocol['cases']}
cost_inputs={}
for key,item in read(R/'COST_INPUTS.json').items():
 data=base64.b64decode(item['base64']);assert hashlib.sha256(data).hexdigest()==item['sha256']
 assert item['sha256']==protocol['input_pins']['benchmark/'+case_names[int(key)]+'/cost.txt']
 cost_inputs[int(key)]=[float(v) for line in data.decode().splitlines() for v in line.split('#')[0].split()]
rows=[]
for row in a['rows']:
 r=dict(row);D=E/'formal/runs'/r['identity'];raw=read(D/'S10_search.json') if (D/'S10_search.json').exists() else {}
 meta=read(D/'S10_search.run.json') if (D/'S10_search.run.json').exists() else {}
 result=read(D/'RESULT.json') if (D/'RESULT.json').exists() else {}
 r.update(search_seconds=meta.get('elapsed'),shortlist_count=len(raw.get('candidate_shortlist',[])),raw_pool_count=raw.get('raw_certified_pool_count',0),transport_exclusions_verified=r.get('transport_exclusions_verified',0),budget_proofs_verified=r.get('budget_proofs_verified',{'proofs':0,'qualified':0,'rejected':0,'subproblems':0,'exact_cost_cuts':0}),budget_statistics=raw.get('adaptive_RO_statistics'),active_certificate_calls=raw.get('search_certificate_calls',0),active_certificate_seconds=raw.get('search_certificate_seconds',0),funnel1=raw.get('stage1_model'),funnel2=raw.get('stage2_ro_candidates'),funnel3=raw.get('stage3_internal_cdf_and_polish'),funnel4=result.get('stage4_lss_final'))
 r['gamma_query_count']=len(raw.get('adaptive_RO_queries',[]))
 r['query_count']=len(raw.get('adaptive_RO_queries',[]))+len(raw.get('entropic_queries',[]))
 r['entropic_statistics']=raw.get('entropic_statistics')
 r['model_statistics']=r['entropic_statistics'] or r['budget_statistics']
 r['model_type']={'block_mitm':'B01','block_winf_transport':'D02_Winf_DRO','cvar_budget_calibrated':'R02_ES95_budget_RO','entropy_cdf_calibrated':'R03b_entropic_risk_proxy'}.get(raw.get('search_flow'),'unavailable')
 r['tables_prepared']=len((raw.get('entropic_model') or {}).get('tables',[])) if raw.get('entropic_model') else None
 r['LSS_accepted_count']=(result.get('stage4_lss_final') or {}).get('lss_accepted_count')
 r['query_reference_checks']=0
 if raw.get('adaptive_RO_model'):
  model=raw['adaptive_RO_model'];deltas=[Fraction(p['deviation']) for p in model['items']];guard=Fraction(str(raw['capacity']))-Fraction(1,10**8)
  for query in raw['adaptive_RO_queries']:
   gamma=Fraction(query['gamma']);ts=[Fraction(t['theta']) for t in query['solver_tasks']]
   for index in set(query['candidate_refs']):
    proof=raw['adaptive_RO_proposals'][index];mu=Fraction(proof['nominal_sum']);ds=sorted((deltas[j] for j in proof['selection']),reverse=True);whole=gamma.numerator//gamma.denominator
    protect=sum(ds[:whole],Fraction())+(gamma-whole)*ds[whole] if whole<len(ds) else sum(ds,Fraction())
    assert mu+protect<=guard,'Query reference lacks its own Gamma feasibility'
    assert ts and min(mu+gamma*t+sum((max(Fraction(),v-t) for v in ds),Fraction()) for t in ts)<=guard,'Query reference lacks any queried theta witness'
    r['query_reference_checks']+=1
 if raw.get('adaptive_RO_model') and r.get('funnel1'):
  r['funnel1']=dict(r['funnel1'])
  for key in ['gamma_bisect_lo','gamma_bisect_hi','gamma_bisect_rounds']:r['funnel1'][key]=raw['adaptive_RO_model'].get(key)
  r['funnel1']['model_preparation_plus_MIP_seconds']=raw['adaptive_RO_statistics']['preparation_seconds']+raw['adaptive_RO_statistics']['MIP_seconds']
  r['funnel1']['ro_seconds']=None
  r['funnel1']['ro_seconds_note']='Model preparation and MIP are separately timed; complete RO stage including threshold ranking is not separately measured and is not fabricated.'
  r['funnel2']=dict(r['funnel2']);r['funnel2']['best_ro_cost_before_cdf']=min((math.fsum(cost_inputs[r['case_index']][j] for j in p['selection']) for p in raw['adaptive_RO_proposals'] if p['robust_feasible'] and p['fixed_theta_feasible']),default=None)
 initial=next((q for q in raw.get('events',[]) if q.get('event')=='raw_certified_incumbent'),None);r['self_first_accepted_cost']=initial['cost'] if initial else None
 if r['valid'] and r['arm']=='C_R02_CVAR_BUDGET':
  p=next(p for p in raw['adaptive_RO_proposals'] if p['selection']==r['selection'] and p['robust_feasible'] and p['fixed_theta_feasible'])
  r.update(final_budget_gamma=p['gamma'],final_budget_theta=p['theta'],final_budget_worst_load=float(Fraction(p['budget_worst_sum'])))
 if raw.get('entropic_model') and r.get('funnel1'):
  r['funnel1']=dict(r['funnel1']);r['funnel2']=dict(r['funnel2'])
  r['funnel1']['ro_seconds']=None
  r['funnel1']['model_preparation_plus_MIP_seconds']=raw['entropic_statistics']['preparation_seconds']+raw['entropic_statistics']['MIP_seconds']
  r['funnel1']['eta_max_by_t']=[{'t':t['t'],'eta_max':t['eta_max']} for t in raw['entropic_model']['tables']]
  r['funnel2']['best_ro_cost_before_cdf']=min((math.fsum(cost_inputs[r['case_index']][j] for j in p['selection']) for p in raw['entropic_proposals']),default=None)
 if r['valid'] and r['arm']=='D_R03B_ENTROPIC':
  p=next(p for p in raw['entropic_proposals'] if p['selection']==r['selection'])
  r.update(final_entropic_t=p['t'],final_entropic_eta=p['eta'],final_entropic_sum_upper=float(Fraction(p['weight_sum_upper'])),final_entropic_eta_max=raw['entropic_model']['tables'][p['table_index']]['eta_max'])
 r['gamma_max']=(raw.get('adaptive_RO_model') or {}).get('gamma_max_exact')
 rows.append(r)
groups=[]
for g in a['groups']:
 rr=[r for r in rows if r['case_index']==g['case_index'] and r['arm']==g['arm']];vv=[r for r in rr if r['valid']];best=min((r['cost'] for r in vv),default=None);hits=[r for r in vv if r['cost']==best]
 groups.append(dict(g,valid_whole_mean=statistics.mean(r['process_wall_seconds'] for r in vv) if vv else None,whole_max=max(r['process_wall_seconds'] for r in rr),whole_std=statistics.stdev(r['process_wall_seconds'] for r in rr),first_found_mean=statistics.mean(r['first_found_seconds'] for r in vv) if len(vv)==30 else None,best_hits=len(hits),best_conditional_found_mean=statistics.mean(r['first_found_seconds'] for r in hits) if hits else None,valid_search_mean=statistics.mean(r['search_seconds'] for r in vv) if vv else None,valid_LSS_mean=statistics.mean(r['LSS_seconds'] for r in vv) if vv else None,raw_best_avg=statistics.mean(r['raw_final_cost'] for r in vv) if len(vv)==30 else None))
primary=[c for c in a['comparisons'] if c['candidate']=='D_R03B_ENTROPIC'];complete=[c for c in primary if c['complete30']]
headline='独立有效%d/360；R03b对三新鲜对照的完整30次比较，%d项均值较优、%d项较劣，Holm18显著优%d项、显著劣%d项。'%(a['independent_valid'],sum(c['avg_diff']<0 for c in complete),sum(c['avg_diff']>0 for c in complete),sum(c['avg_diff']<0 and c['cost_p_holm18']<.05 for c in complete),sum(c['avg_diff']>0 and c['cost_p_holm18']<.05 for c in complete))
diag={'headline':headline,'rows':rows,'groups':groups,'comparisons':a['comparisons'],'failure_counts':dict(Counter(r.get('failure_class','record_or_clock_error') for r in rows if not r['valid'])),'max_whole_seconds':max(r['process_wall_seconds'] for r in rows),'all_under600':all(r['process_wall_seconds']<=600 for r in rows),'no_probability_resampling':True,'no_retries':True,'no_automatic_full40':True,'first_failed_excel_row':next((i+5 for i,r in enumerate(rows) if not r['valid']),5)}
(R/'FINAL_COMPARISON_AND_DIAGNOSIS.json').write_text(json.dumps(diag,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in diag.items() if k not in ['rows','comparisons']},ensure_ascii=False))

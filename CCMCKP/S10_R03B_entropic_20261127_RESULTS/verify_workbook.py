from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET,math,statistics
from fractions import Fraction
R=Path(__file__).resolve().parent;d=json.loads((R/'FINAL_COMPARISON_AND_DIAGNOSIS.json').read_text());rows=d['rows'];checks=0
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(R/'delivery/R03b熵代理_四版本_三大算例30次_对比统计.xlsx') as z:
 sheets=[{c.attrib['r']:c for c in ET.fromstring(z.read('xl/worksheets/sheet%d.xml'%i)).findall('.//m:c',ns)} for i in [1,2]]
s,r=sheets
def value(cells,key):
 c=cells.get(key)
 if c is None:return None
 assert c.attrib.get('t')!='e',key
 v=c.find('m:v',ns)
 return float(v.text) if v is not None and v.text is not None and c.attrib.get('t') not in ['s','str','inlineStr'] else None
def compare(cells,key,target):
 global checks
 actual=value(cells,key)
 if target is None:assert actual is None,(key,actual,target)
 else:assert actual is not None and math.isclose(actual,target,rel_tol=1e-10,abs_tol=1e-8),(key,actual,target)
 checks+=1
for cell in list(s.values())+list(r.values()):assert cell.attrib.get('t')!='e'
for i,g in enumerate(d['groups']):
 rr=[x for x in rows if x['case_index']==g['case_index'] and x['arm']==g['arm']];vv=[x for x in rr if x['valid']];full=len(vv)==30
 for col,target in {'C':len(vv),'D':g['best_diagnostic'],'E':g['official_avg'],'F':g['official_std'],'G':g['official_std']/g['official_avg'] if full else None,'H':g['valid_whole_mean'],'I':g['whole_mean'],'J':g['whole_max'],'K':30-len(vv)}.items():compare(s,col+str(9+i),target)
 for col,target in {'C':g['first_found_mean'],'D':g['best_hits'],'E':g['best_conditional_found_mean'],'F':g['valid_search_mean'],'G':g['valid_LSS_mean'],'H':sum(x.get('search_seconds') is not None for x in rr)}.items():compare(s,col+str(25+i),target)
 model=[x['model_statistics']['preparation_seconds'] for x in rr if x.get('model_statistics')]
 for col,target in {'C':statistics.mean(x['active_certificate_calls'] for x in rr),'D':statistics.mean(x['active_certificate_seconds'] for x in rr),'E':statistics.mean(x['transport_exclusions_verified'] for x in rr),'F':statistics.mean(x['budget_proofs_verified']['proofs'] for x in rr),'G':statistics.mean(x['budget_proofs_verified']['qualified'] for x in rr),'H':statistics.mean(x['budget_proofs_verified']['subproblems'] for x in rr),'I':statistics.mean(x['budget_proofs_verified'].get('exact_cost_cuts',0) for x in rr),'J':statistics.mean(model) if model else None}.items():compare(s,col+str(63+i),target)
 for col,target in {'C':g['raw_best_avg'],'D':g['official_avg'],'E':sum(x.get('final_cost_minus_raw_best',0)>1e-8 for x in vv),'F':round(statistics.mean(x['final_cost_minus_raw_best'] for x in vv),9) if full else None,'G':statistics.mean(x['raw_pool_count'] for x in rr),'H':statistics.mean(x['shortlist_count'] for x in rr)}.items():compare(s,col+str(102+i),target)
for i,x in enumerate(rows):
 model=x.get('model_statistics') or {}
 expected={'A':x['case_index'],'C':x['rep'],'D':x['seed'],'E':int(x['valid']),'F':x['cost'],'G':x.get('LSS'),'H':x['process_wall_seconds'],'I':x.get('search_seconds'),'J':x.get('LSS_seconds'),'K':x.get('first_found_seconds'),'L':x.get('self_first_accepted_cost'),'M':x.get('raw_final_cost'),'N':x['peak_rss_bytes']/2**30,'O':x['rc'],'T':x['budget_proofs_verified']['proofs'],'U':x['budget_proofs_verified']['qualified'],'V':x['budget_proofs_verified']['subproblems'],'W':x['active_certificate_calls'],'X':x['active_certificate_seconds'],'Y':x['transport_exclusions_verified'],'Z':x['raw_pool_count'],'AA':x['shortlist_count'],'AB':x.get('final_cost_minus_raw_best'),'AE':x.get('final_budget_worst_load'),'AH':x.get('final_entropic_sum_upper'),'AI':model.get('preparation_seconds'),'AJ':model.get('MIP_seconds'),'AK':x['budget_proofs_verified'].get('exact_cost_cuts',0),'AL':x['query_count'],'AM':x.get('tables_prepared'),'AN':x.get('LSS_accepted_count'),'AQ':model.get('raw_solver_candidates')}
 for col,field in {'AC':'final_budget_gamma','AD':'final_budget_theta','AF':'final_entropic_t','AG':'final_entropic_eta','AO':'final_entropic_eta_max','AP':'gamma_max'}.items():expected[col]=float(Fraction(x[field])) if x.get(field) is not None else None
 for col,target in expected.items():compare(r,col+str(5+i),target)
for i,c in enumerate(d['comparisons']):
 for col,target in {'A':c['case_index'],'E':c['avg_diff'],'F':c['cost_p_raw'],'G':c['cost_p_holm18'] if c['complete30'] else None,'H':c['validity_p_holm18']}.items():compare(s,col+str(41+i),target)
result={'status':'PASS','numeric_cache_checks':checks,'rows':len(rows),'formula_errors_absent':True,'failed_costs_blank_verified':sum(not x['valid'] for x in rows)}
(R/'WORKBOOK_VERIFIED.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

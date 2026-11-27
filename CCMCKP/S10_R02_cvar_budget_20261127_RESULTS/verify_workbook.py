from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET,math,statistics
R=Path(__file__).resolve().parent;d=json.loads((R/'FINAL_COMPARISON_AND_DIAGNOSIS.json').read_text());rows=d['rows'];checks=0
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(R/'delivery/R02校准预算鲁棒_B01_D02_三大算例30次_对比统计.xlsx') as z:
 sc={c.attrib['r']:c for c in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//m:c',ns)};dc={c.attrib['r']:c for c in ET.fromstring(z.read('xl/worksheets/sheet2.xml')).findall('.//m:c',ns)}
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
for c in list(sc.values())+list(dc.values()):assert c.attrib.get('t')!='e','Exported formula error'
for i,g in enumerate(d['groups']):
 rr=[r for r in rows if r['case_index']==g['case_index'] and r['arm']==g['arm']];vv=[r for r in rr if r['valid']];complete=len(vv)==30
 expected={'C':len(vv),'D':g['best_diagnostic'],'E':g['official_avg'],'F':g['official_std'],'G':g['official_std']/g['official_avg'] if complete else None,'H':g['valid_whole_mean'],'I':g['whole_mean'],'J':g['whole_max'],'K':30-len(vv)}
 for col,target in expected.items():compare(sc,col+str(i+9),target)
 for col,target in {'C':g['first_found_mean'],'D':g['best_hits'],'E':g['best_conditional_found_mean'],'F':g['valid_search_mean'],'G':g['valid_LSS_mean'],'H':len(rr)}.items():compare(sc,col+str(i+22),target)
 for col,target in {'C':statistics.mean(r['active_certificate_calls'] for r in rr),'D':statistics.mean(r['active_certificate_seconds'] for r in rr),'E':statistics.mean(r['transport_exclusions_verified'] for r in rr),'F':statistics.mean(r['budget_proofs_verified']['proofs'] for r in rr),'G':statistics.mean(r['budget_proofs_verified']['qualified'] for r in rr),'H':statistics.mean(r['budget_proofs_verified']['subproblems'] for r in rr),'I':statistics.mean(r['budget_proofs_verified']['rejected'] for r in rr)}.items():compare(sc,col+str(i+48),target)
 for col,target in {'C':g['raw_best_avg'],'D':g['official_avg'],'E':sum(r.get('final_cost_minus_raw_best',0)>1e-8 for r in vv),'F':round(statistics.mean(r['final_cost_minus_raw_best'] for r in vv),9) if complete else None,'G':statistics.mean(r['raw_pool_count'] for r in rr),'H':statistics.mean(r['shortlist_count'] for r in rr)}.items():compare(sc,col+str(i+83),target)
for i,r in enumerate(rows):
 expected={'A':r['case_index'],'C':r['rep'],'D':r['seed'],'E':int(r['valid']),'F':r['cost'],'G':r.get('LSS'),'H':r['process_wall_seconds'],'I':r.get('search_seconds'),'J':r.get('LSS_seconds'),'K':r.get('first_found_seconds'),'L':r.get('self_first_accepted_cost'),'M':r.get('raw_final_cost'),'N':r['peak_rss_bytes']/2**30,'O':r['rc'],'S':r['budget_proofs_verified']['proofs'],'T':r['budget_proofs_verified']['qualified'],'U':r['budget_proofs_verified']['subproblems'],'V':r['active_certificate_calls'],'W':r['active_certificate_seconds'],'X':r['transport_exclusions_verified'],'Y':r['raw_pool_count'],'Z':r['shortlist_count'],'AA':r.get('final_cost_minus_raw_best'),'AD':r.get('final_budget_worst_load'),'AE':(r.get('budget_statistics') or {}).get('preparation_seconds',0),'AF':(r.get('budget_statistics') or {}).get('MIP_seconds',0),'AG':r['budget_proofs_verified']['rejected']}
 for col,target in expected.items():compare(dc,col+str(i+5),target)
 for col,target in {'AH':r['budget_proofs_verified'].get('exact_cost_cuts'), 'AJ':(r.get('funnel2') or {}).get('raw_solver_candidates'),'AK':(r.get('funnel3') or {}).get('ro_passed_native_cdf_count'),'AL':(r.get('funnel4') or {}).get('lss_accepted_count'),'AM':(r.get('funnel1') or {}).get('preparation_seconds'),'AN':(r.get('funnel2') or {}).get('MIP_seconds'),'AO':r['gamma_query_count'] if r.get('funnel1') else None}.items():compare(dc,col+str(i+5),target)
for i,c in enumerate(d['comparisons']):
 for col,target in {'A':c['case_index'],'E':c['avg_diff'],'F':c['cost_p_raw'],'G':c['cost_p_holm9'] if c['complete30'] else None,'H':c['validity_p_holm9']}.items():compare(sc,col+str(i+35),target)
result={'status':'PASS','numeric_cache_checks':checks,'rows':len(rows),'formula_errors_absent':True,'failed_costs_blank_verified':sum(not r['valid'] for r in rows)}
(R/'WORKBOOK_VERIFIED.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

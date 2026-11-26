from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET,math,statistics
R=Path(__file__).resolve().parent;D=R/'delivery';a=json.loads((R/'evidence/formal/FINAL_INDEPENDENT_AUDIT.json').read_text())
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};checks=0
with zipfile.ZipFile(D/'D01_WassersteinDRO_三大算例_统一LSS_对比结果.xlsx') as z:
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
 for i,g in enumerate(a['groups']):
  rr=[r for r in a['rows'] if r['case_index']==g['case_index'] and r['arm']==g['arm']];vv=[r for r in rr if r['valid']];complete=len(vv)==30
  best=min([r['cost'] for r in vv],default=None);hits=[r for r in vv if r['cost']==best]
  expected={'C':len(vv),'D':best,'E':g['official_avg'],'F':g['official_std'],'G':g['official_std']/g['official_avg'] if complete else None,'H':statistics.mean(r['first_found_seconds'] for r in vv) if complete else None,'I':len(hits),'J':statistics.mean(r['first_found_seconds'] for r in hits) if hits else None,'K':sum(r['final_cost_minus_raw_best']>1e-8 for r in vv),'L':statistics.mean(r['initialization_cost'] for r in vv) if complete else None}
  for col,target in expected.items():compare(sc,col+str(i+9),target)
  for col,target in {'C':g['whole_mean'],'D':statistics.stdev(r['process_wall_seconds'] for r in rr),'E':max(r['process_wall_seconds'] for r in rr),'F':statistics.mean(r['search_seconds'] for r in vv) if complete else None,'G':statistics.mean(r['LSS_seconds'] for r in vv) if complete else None,'H':sum(r['post_init_improved'] for r in vv)}.items():compare(sc,col+str(i+22),target)
 for i,r in enumerate(a['rows']):
  for col,target in {'A':r['case_index'],'C':r['rep'],'D':r['seed'],'E':int(r['valid']),'F':r['cost'],'H':r['process_wall_seconds']}.items():compare(dc,col+str(i+5),target)
 for i,c in enumerate(a['comparisons']):
  for col,target in {'A':c['case_index'],'E':c['avg_diff'],'F':c['cost_p_raw'],'G':c['cost_p_holm9'] if c['complete30'] else None,'H':c['validity_p_holm9']}.items():compare(sc,col+str(i+35),target)
data={'status':'PASS','numeric_cache_checks':checks,'rows':len(a['rows']),'formula_errors_absent':True}
(R/'WORKBOOK_VERIFIED.json').write_text(json.dumps(data,indent=2));print(json.dumps(data))

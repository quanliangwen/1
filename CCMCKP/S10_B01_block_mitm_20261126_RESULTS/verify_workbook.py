from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET,math,statistics
R=Path(__file__).resolve().parent;D=R/'delivery';a=json.loads((R/'evidence/formal/FINAL_INDEPENDENT_AUDIT.json').read_text());e=json.loads((R/'evidence/engineering/ENGINEERING_INDEPENDENT_AUDIT.json').read_text())
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
checks=0
with zipfile.ZipFile(D/'B01小块MITM_三大算例_统一LSS_对照结果.xlsx') as z:
 summary=ET.fromstring(z.read('xl/worksheets/sheet1.xml'));detail=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
 sc={c.attrib['r']:c for c in summary.findall('.//m:c',ns)};dc={c.attrib['r']:c for c in detail.findall('.//m:c',ns)}
 def value(cells,key):
  c=cells.get(key)
  if c is None:return None
  assert c.attrib.get('t')!='e',key
  v=c.find('m:v',ns)
  return float(v.text) if v is not None and v.text is not None and c.attrib.get('t') not in ['s','str','inlineStr'] else None
 for c in list(sc.values())+list(dc.values()):assert c.attrib.get('t')!='e','Exported formula error'
 for i,g in enumerate(a['groups']):
  rr=[r for r in a['rows'] if r['case_index']==g['case_index'] and r['arm']==g['arm']];vv=[r for r in rr if r['valid']]
  best=min([r['cost'] for r in vv],default=None);hits=[r for r in vv if r['cost']==best];row=i+8
  expected={'C':len(vv),'D':best,'E':g['official_avg'],'F':g['official_std'],'G':g['whole_mean'],'H':statistics.stdev(r['process_wall_seconds'] for r in rr),'I':max(r['process_wall_seconds'] for r in rr),'J':statistics.mean(r['first_found_seconds'] for r in vv) if len(vv)==30 else None,'K':len(hits),'L':statistics.mean(r['first_found_seconds'] for r in hits) if hits else None,'M':g['block_improvements']}
  for col,target in expected.items():
   actual=value(sc,col+str(row))
   if target is None:assert actual is None,(col,row,actual,target)
   else:assert actual is not None and math.isclose(actual,target,rel_tol=1e-10,abs_tol=1e-8),(col,row,actual,target)
   checks+=1
 combined=a['rows']+e['rows']
 for i,r in enumerate(combined):
  for col,target in {'B':r['case_index'],'D':r['rep'],'E':r['seed'],'F':int(r['valid']),'G':r['cost'],'I':r['process_wall_seconds']}.items():
   actual=value(dc,col+str(i+5))
   if target is None:assert actual is None
   else:assert math.isclose(actual,target,abs_tol=1e-9)
   checks+=1
data={'status':'PASS','numeric_cache_checks':checks,'rows':len(combined),'all_formula_error_types_absent':True}
(R/'WORKBOOK_VERIFIED.json').write_text(json.dumps(data,indent=2));print(json.dumps(data))

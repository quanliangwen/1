"""Read-only verification of exported XLSX cached numbers and text precision."""
from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET,hashlib,math
H=Path(__file__).parent;O=H/'outputs/F001_final';file=O/'F001_40cases_30runs.xlsx';data=json.load(open(H/'formal/F001_I002_40x30/FINAL_AUDIT_STATS.json'));ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
if not data['integrity_passed'] or len(data['details'])!=1200:raise RuntimeError('Complete audited cohort required')
with zipfile.ZipFile(file) as z:
 if z.testzip() is not None:raise RuntimeError('XLSX ZIP CRC failed')
 strings=[]
 if 'xl/sharedStrings.xml' in z.namelist():strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
 def cells(name):
  result={};root=ET.fromstring(z.read(name))
  for c in root.findall('.//s:sheetData/s:row/s:c',ns):
   t=c.get('t');v=c.find('s:v',ns);f=c.find('s:f',ns);s=v.text if v is not None else None
   if t=='e':raise RuntimeError('Exported formula error '+str(s))
   if t=='s':value=strings[int(s)]
   elif t=='inlineStr':value=''.join(c.find('s:is',ns).itertext())
   elif t in ['str','d']:value=s or ''
   elif t=='b':value=s=='1'
   else:value=float(s) if s is not None else None
   result[c.get('r')]=dict(value=value,formula=None if f is None else f.text,type=t)
  return result
 def close(actual,expected,label):
  if expected is None:
   if actual not in [None,'']:raise RuntimeError('Missing statistic exported as value '+label)
  elif not isinstance(actual,(int,float)) or not math.isclose(actual,expected,rel_tol=0,abs_tol=1e-7):raise RuntimeError('Cached result differs '+label+': '+str(actual)+' vs '+str(expected))
 sheets=[cells(f'xl/worksheets/sheet{i}.xml') for i in range(1,6)]
 sums=sorted(data['summary'],key=lambda r:(not r['instance'].startswith('APP'),r['index']))
 for r,s in enumerate(sums,5):
  if sheets[0][f'A{r}']['value']!=s['index']:raise RuntimeError('APP/LAB case order differs')
  expected=[s[k] for k in ['old_best','best','avg','std','avg_minus_own_best','avg_minus_old_best','mean_search_seconds','protocol_valid','minimum_independent_raw_lower','minimum_real_probability']]
  for k,e in enumerate(expected,ord('D')):close(sheets[0].get(f'{chr(k)}{r}',{}).get('value'),e,f'{chr(k)}{r}')
  for col in 'EFGHIJK':
   if not sheets[0][f'{col}{r}']['formula']:raise RuntimeError('Calculated statistic not exported as formula')
 ordered=sorted(data['details'],key=lambda r:(r['index'],r['seed']))
 for row,r in enumerate(ordered,5):
  for col,key in [('A','index'),('C','tmax'),('D','seed'),('E','joint_accepted'),('F','protocol_valid')]:close(sheets[1][f'{col}{row}']['value'],r[key],f'detail {col}{row}')
  close(sheets[1].get(f'G{row}',{}).get('value'),r.get('cost') if r['protocol_valid'] else None,f'detail cost{row}')
 for row,r in enumerate(data['independent_raw_recounts'],5):
  for col,key in [('G','numerator'),('H','denominator')]:
   c=sheets[3][f'{col}{row}']
   if c['type'] not in ['s','inlineStr','str'] or c['value']!=r[key]:raise RuntimeError('Exact integer lost text precision')
result=dict(passed=True,xlsx_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),summary_cases=40,registered_details=1200,cached_statistics_match_independent_audit=True,summary_formulas_preserved=True,exact_probability_integers_preserved_as_text=True,formula_error_cells=0,zip_CRC_passed=True,visual_review_still_required=True)
(O/'XLSX_CACHED_VALUE_CHECK.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

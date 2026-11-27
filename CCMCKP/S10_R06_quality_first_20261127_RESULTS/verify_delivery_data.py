from pathlib import Path
import json,csv,hashlib,statistics,zipfile,ast
R=Path(__file__).resolve().parent;D=R if (R/'CHECKSUMS_SHA256.json').exists() else R/'delivery'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
checks=read(D/'CHECKSUMS_SHA256.json')
for n,x in checks.items():assert sha(D/n)==x['sha256'] and (D/n).stat().st_size==x['bytes'],n
with (D/'R06_全40例3600次明细.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
assert len(rows)==3600 and len({r['identity'] for r in rows})==3600
assert sum(r['original_protocol_valid']=='True' for r in rows)==3592
assert all(r['LSS_passed']=='True' and float(r['LSS_diagnostic_probability'])>=.99 and float(r['process_wall_seconds'])<=600 for r in rows)
with (D/'R06_全40例120组统计.csv').open(encoding='utf-8-sig',newline='') as f:groups=list(csv.DictReader(f))
assert len(groups)==120 and sum(g['avg30']=='' for g in groups)==1
for g in groups:
 rr=[r for r in rows if r['case_index']==g['case_index'] and r['arm']==g['arm']];assert len(rr)==30
 values=[float(r['LSS_diagnostic_cost']) for r in rr]
 assert abs(statistics.mean(values)-float(g['LSS30_diagnostic_avg']))<1e-12
 assert abs(statistics.stdev(values)-float(g['LSS30_diagnostic_std']))<1e-12
 if int(g['valid'])==30:assert abs(statistics.mean(values)-float(g['avg30']))<1e-12
 else:assert g['case_index']=='18' and g['arm']=='D_R06_QUALITY_DUAL' and int(g['valid'])==22 and g['avg30']==g['sample_std30']==''
summary=read(D/'R06_全40例统计与检验.json');assert len(summary['primary_comparisons'])==120
lines=(D/'CCMCKP_R06_质量优先运行测试总结.md').read_text(encoding='utf-8').splitlines();last_columns=None;table_count=0
for line in lines:
 if line.startswith('|'):
  columns=len(line.split('|'))-2
  if last_columns is None:table_count+=1
  else:assert columns==last_columns,('table columns',line)
  last_columns=columns
 else:last_columns=None
with zipfile.ZipFile(D/'R06_冻结源码与验证.zip') as z:tree=ast.parse(z.read('build_full40_report.py').decode('utf-8'))
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['holm','pratt_exact']]
assert hashlib.sha256(ast.dump(ast.Module(body=nodes,type_ignores=[])).encode()).hexdigest()==read(D/'REPORT_STATISTICS_CHECKS.json')['function_AST_sha256']
parts=read(D/'证据分片清单.json');joined=hashlib.sha256();size=0
for q in parts['parts']:
 p=D/q['name'];assert sha(p)==q['sha256'] and p.stat().st_size==q['bytes']
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):joined.update(b);size+=len(b)
assert size==parts['joined_bytes'] and joined.hexdigest()==parts['joined_sha256']
out={'status':'PASS','CSV_rows':3600,'CSV_groups':120,'original_protocol_conformant':3592,'LSS_passed':3600,'all_actual_worker_times_within600':True,'official_avg_std_null_group_count':1,'all_diagnostic30_means_stds_recomputed':True,'primary_comparisons':120,'Markdown_tables_checked':table_count,'statistics_helper_matches_known_checks':True,'evidence_fragments_verified':len(parts['parts']),'joined_evidence_sha256':joined.hexdigest()}
if R!=D:
 (D/'DELIVERY_QA.json').write_text(json.dumps(out,indent=2),encoding='utf-8');(D/'verify_delivery_data.py').write_bytes(Path(__file__).read_bytes())
 for n in ['DELIVERY_QA.json','verify_delivery_data.py']:checks[n]={'sha256':sha(D/n),'bytes':(D/n).stat().st_size}
 (D/'CHECKSUMS_SHA256.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out))

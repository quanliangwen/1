"""Verify actual frozen-S10 subprocess lineage and original LSS CSV output."""
from pathlib import Path
import json,gzip,csv,hashlib,zipfile,time,shutil
H=Path(__file__).resolve().parent;D=H/'iterations/S10_LSS_mainflow_APP3_confirmation';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();out=D/'VERIFIED_S10_OUTPUTS.json'
if out.exists():raise RuntimeError('No verified S10 outcome overwrite')
if not all((D/('case_T'+str(c))/'CONFIRMATION.json').exists() for c in [21,27]):
 print(json.dumps(dict(ready=False,reason='actual original S10/LSS mainflow cases not both terminal')));raise SystemExit(0)
reg=json.load(open(D/'REGISTRATION.json'));base=json.load(open(H/'BASELINE_S10.json'));ref=json.load(open(H/'REFERENCE_SHA256.json'));rows=[]
if reg['S10_source_sha256']!=base['source_sha256'] or {p.name:sha(p) for p in (D/'S10_source').glob('*.py')}!=base['source_sha256']:raise RuntimeError('Search algorithm differs from actual S10 baseline')
for c,target in [(21,'9.034717'),(27,'7.250013')]:
 O=D/('case_T'+str(c));v=json.load(open(O/'CONFIRMATION.json'));meta=json.load(open(O/'S10_search.json.gz.run.json'));data=json.loads(gzip.decompress((O/'S10_search.json.gz').read_bytes()));csvfile=H/v['original_output_csv']
 with csvfile.open() as f:records=list(csv.DictReader(f))
 if len(records)!=1:raise RuntimeError('Not one actual original CSV record')
 r=records[0];q=json.loads(r['Solution']);pool={tuple(v['selection']):v for v in data['candidate_shortlist']}
 if meta['source_sha256']!=base['source_sha256'] or v['S10_source_sha256']!=base['source_sha256'] or meta['seed']!=reg['search_seed'] or data['seed']!=reg['search_seed'] or not meta['within_budget'] or data['schema']!='CCMCKP_S10_raw_constraint_portfolio' or data['instance']!='APP_3_5_30_' or data['capacity']!=c or not data['exhaustive']['complete'] or data['exhaustive']['checked']!=125:raise RuntimeError('Actual original S10 source/seed/input/exhaustive search lineage differs')
 for n,d in meta['input_sha256'].items():
  if sha(Path(reg['benchmark'])/n)!=d:raise RuntimeError('Actual original S10 input changed')
 if tuple(q) not in pool or abs(float(r['Cost'])-pool[tuple(q)]['cost'])>1e-9 or format(float(r['Cost']),'.6f')!=target or v['cost_6dp']!=target or float(r['Confidence Level'])<.99 or v['extra_real_probability_hard_filter'] or v['old_S10_real_probability_postselector_called'] or v['search_algorithm_replaced_by_I017'] or sha(csvfile)!=v['original_output_csv_sha256'] or sha(O/'S10_search.json.gz')!=v['S10_result_sha256'] or sha(O/'S10_search.json.gz.run.json')!=v['S10_runmeta_sha256']:raise RuntimeError('Original S10 origin or unfiltered LSS output mismatch')
 trace=json.load(open(O/'ORIGINAL_LSS_DECISION_TRACE.json'));seen={tuple(t['selection']) for t in trace if t['stage']=='S10_pool_original_LSS_decision'}
 if seen!=set(pool) or any(tuple(t['selection']) not in pool for t in trace):raise RuntimeError('Bridge introduced candidates outside fresh S10 pool or omitted its original LSS checks')
 passing=[t for t in trace if t['stage']=='S10_pool_original_LSS_decision' and t['probability']>=.99]
 if not passing or abs(min(pool[tuple(t['selection'])]['cost'] for t in passing)-float(r['Cost']))>1e-9 or v['original_LSS_output_tail_AST_sha256']!='00a03fc080f643b052d8b4bfda19cab87a3f8e82c323a937148e48395d3357ed':raise RuntimeError('Original LSS minimum-cost output/tail differs')
 if float(r['Real Confidence Level'])>=.985:raise RuntimeError('Regression fixture no longer demonstrates removal of external985rejection')
 rows.append(dict(instance='APP_3_5_30_',capacity=c,cost=float(r['Cost']),cost_6dp=target,original_LSS_confidence=float(r['Confidence Level']),recorded_real_probability=float(r['Real Confidence Level']),selection=q,S10_search_seconds=meta['elapsed'],original_mainflow_search_seconds=float(r['Running Time']),S10_candidates=len(pool),S10_complete_enumerated_choices=125,original_CSV=v['original_output_csv'],original_CSV_sha256=sha(csvfile),S10_result_sha256=v['S10_result_sha256'],new_runs=1))
for p in ref['files']:
 if sha(H/'reference'/p['path'])!=p['sha256']:raise RuntimeError('Original LSS code changed')
verified=dict(passed=True,time=time.time(),scope='APP_3_5_30 T21/T27 each one NEW original frozen S10 run, original LSS evaluator and output0 CSV; not40x30',S10_search_files_byte_identical=12,S10_source_sha256=base['source_sha256'],original_LSS_files_unmodified=21,original_LSS_output_tail_AST_unchanged=True,extra_real_probability_hard_filter=False,old_real_probability_postselector_invoked=False,I017_search_not_used=True,new_MC_calls_by_verifier=0,rows=rows)
with out.open('x') as f:json.dump(verified,f,indent=2)
csvout=D/'S10_CONFIRMED_OUTPUT.csv'
with csvout.open('x',newline='') as f:
 w=csv.writer(f);w.writerow(['Instance','T','S10 cost via original LSS output0','Original LSS confidence','Recorded real probability','S10 worker seconds','Original mainflow search seconds'])
 for r in rows:w.writerow([r['instance'],r['capacity'],r['cost_6dp'],r['original_LSS_confidence'],r['recorded_real_probability'],r['S10_search_seconds'],r['original_mainflow_search_seconds']])
files=[p for p in D.rglob('*') if p.is_file() and 'vendor313' not in p.parts and p.suffix not in ['.zip','.pyc']]+[H/n for n in reg['driver_sha256']]+[H/'verify_s10_lss_confirmation.py',H/'reference_loader.py',H/'REFERENCE_SHA256.json']+[H/'reference'/p['path'] for p in ref['files']];files=sorted(set(files));zfile=D/'S10_APP3_ACTUAL_EVIDENCE.zip'
with zipfile.ZipFile(zfile,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(H).as_posix())
with zipfile.ZipFile(zfile) as z:assert z.testzip() is None
m=dict(file=zfile.name,bytes=zfile.stat().st_size,sha256=sha(zfile),zip_CRC_passed=True,files=[dict(path=p.relative_to(H).as_posix(),sha256=sha(p)) for p in files])
with (D/'EVIDENCE_MANIFEST.json').open('x') as f:json.dump(m,f,indent=2)
T=H/'artifact'/D.relative_to(H);T.mkdir(parents=True,exist_ok=True)
for p in [out,csvout,zfile,D/'EVIDENCE_MANIFEST.json']:shutil.copy2(p,T/p.name)
for c in [21,27]:
 O=D/('case_T'+str(c));R=T/('case_T'+str(c));R.mkdir(exist_ok=True);shutil.copy2(O/'CONFIRMATION.json',R/'CONFIRMATION.json');(R/'result/Localsearch').mkdir(parents=True,exist_ok=True)
 for p in (O/'result/Localsearch').glob('*.csv'):shutil.copy2(p,R/'result/Localsearch'/p.name)
print(json.dumps(dict(passed=True,S10_search_files_byte_identical=12,rows=rows,evidence={k:v for k,v in m.items() if k!='files'})))

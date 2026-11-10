"""Read actual original LSS CSVs and verify two requested outputs; no search/MC."""
from pathlib import Path
import json,csv,hashlib,time,zipfile,shutil
H=Path(__file__).resolve().parent;D=H/'iterations/I017_LSS_mainflow_two_case_confirmation';out=D/'VERIFIED_TWO_OUTPUTS.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No verified confirmation overwrite')
if not all((D/('case_T'+str(c))/'CONFIRMATION.json').exists() for c in [21,27]):
 print(json.dumps(dict(ready=False,reason='actual original-mainflow case processes not both terminal')));raise SystemExit(0)
reg=json.load(open(D/'REGISTRATION.json'));m=json.load(open(D/'SOURCE_MANIFEST.json'));rawref=json.load(open(H/'RAW_REFERENCE.json'));truedata=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'];ref=json.load(open(H/'REFERENCE_SHA256.json'));bench=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_3_5_30_')
for r in m['files']:
 if sha(H/r['path'])!=r['sha256']:raise RuntimeError('Prepared original source/algo/driver changed')
for p in [bench/'cost.txt',bench/'node_to_factor.pkl']+list(bench.glob('*_sample.txt')):
 if p.name.endswith('_big_sample.txt'):continue
 if sha(p)!=rawref[str(p)]:raise RuntimeError('Original dataset input differs')
for p in bench.glob('*_dist.txt'):
 if sha(p)!=truedata[bench.name+'/'+p.name]:raise RuntimeError('Original true-data metadata changed')
rows=[]
for cap,expected in [(21,'9.034717'),(27,'7.250013')]:
 O=D/('case_T'+str(cap));v=json.load(open(O/'CONFIRMATION.json'));file=H/v['original_csv']
 with file.open() as f:csvrows=list(csv.DictReader(f))
 if len(csvrows)!=1:raise RuntimeError('Not one actual original CSV output')
 r=csvrows[0]
 if v['cost_6dp']!=expected or format(float(r['Cost']),'.6f')!=expected or float(r['Confidence Level'])<.99 or v['cost']!=float(r['Cost']) or v['real_confidence_level']!=float(r['Real Confidence Level']) or sha(file)!=v['original_csv_sha256'] or not v['original_param_test_and_writers_unmodified'] or not v['original_output_tail_AST_unchanged'] or v['original_tail_AST_sha256']!=reg['original_output_tail_AST_sha256'] or v['true_probability_hard_gate'] or v['independent_raw_integer_hard_gate'] or v['numpy']!='1.24.4' or v['scipy']!='1.10.1':raise RuntimeError('Actual requested value/original contract/source/environment mismatch')
 if float(r['Real Confidence Level'])>=.985:raise RuntimeError('Expected this regression fixture to demonstrate retention BELOW removed985 gate')
 for variant in range(3):
  p=O/'result/Localsearch'/f'LocalSearch_app_3_5_30_{cap}_{variant}.csv'
  with p.open() as f:originalrows=list(csv.DictReader(f))
  if len(originalrows)!=1:raise RuntimeError('Unmodified original variant recording missing')
 rows.append(dict(instance='APP_3_5_30_',capacity=cap,requested_cost=expected,actual_cost=v['cost'],actual_cost_6dp=v['cost_6dp'],original_confidence_level=float(r['Confidence Level']),original_real_confidence_level=float(r['Real Confidence Level']),selection=r['Solution'],running_time=float(r['Running Time']),original_csv=v['original_csv'],original_csv_sha256=sha(file),below_removed985_threshold_but_retained=True,new_runs=1,original_variants0_1_2_recorded=True))
for r in ref['files']:
 if sha(H/'reference'/r['path'])!=r['sha256']:raise RuntimeError('Original LSS source drifted')
result=dict(passed=True,time=time.time(),scope='exactly2 requested cases, one NEW actual original-mainflow run percase; original _0 minimumcost output; not40cases or30runAvg',original_reference_files_unchanged=len(ref['files']),original_decision_output_and_recording_reused=True,only_search_stage_replaced=True,extra_real_probability_hard_gate=False,extra_own_integer_hard_gate=False,new_search_or_MC_calls_by_verifier=0,rows=rows,source_zip_sha256=m['sha256'])
with out.open('x') as f:json.dump(result,f,indent=2)
table=D/'CONFIRMED_OUTPUT.csv'
with table.open('x',newline='') as f:
 w=csv.writer(f);w.writerow(['Instance','T','Original minimum-cost output','Original Confidence Level','Original Real Confidence Level','Output file'])
 for r in rows:w.writerow([r['instance'],r['capacity'],r['actual_cost_6dp'],r['original_confidence_level'],r['original_real_confidence_level'],r['original_csv']])
files=[p for p in D.rglob('*') if p.is_file() and p.suffix not in ['.zip','.pyc']]+[H/'reference'/r['path'] for r in ref['files']]+[H/n for n in ['run_lss_mainflow_confirmation.py','prepare_lss_mainflow_confirmation.py','verify_lss_mainflow_two_outputs.py','reference_loader.py','REFERENCE_SHA256.json']];files=sorted(set(files));archive=D/'I017_TWO_CASE_ACTUAL_MAINFLOW_EVIDENCE.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(H).as_posix())
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
e=dict(file=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),zip_CRC_passed=True,files=[dict(path=p.relative_to(H).as_posix(),sha256=sha(p)) for p in files])
with (D/'EVIDENCE_MANIFEST.json').open('x') as f:json.dump(e,f,indent=2)
T=H/'artifact'/D.relative_to(H);T.mkdir(parents=True,exist_ok=True)
for p in [archive,D/'EVIDENCE_MANIFEST.json',out,table]:shutil.copy2(p,T/p.name)
for cap in [21,27]:
 O=D/('case_T'+str(cap));R=T/O.relative_to(D);R.mkdir(exist_ok=True);shutil.copy2(O/'CONFIRMATION.json',R/'CONFIRMATION.json');(R/'result/Localsearch').mkdir(parents=True,exist_ok=True)
 for p in (O/'result/Localsearch').glob('*.csv'):shutil.copy2(p,R/'result/Localsearch'/p.name)
print(json.dumps(dict(passed=True,rows=rows,evidence={k:v for k,v in e.items() if k!='files'})))

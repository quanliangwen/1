import pathlib,json,hashlib,gzip,numpy as np
H=pathlib.Path(__file__).parent;B=pathlib.Path('/home/junhao/quan/parallel_test_solver/CCMKCP/work/codex_v50_dro_ablation_20261016');manifest=json.load(open(H/'frozen/SOURCE_MANIFEST.json'));result={}
for name,expected in manifest['original_source_sha256'].items():
 p=B/name
 if p.exists():result[name]=dict(expected=expected,observed=hashlib.sha256(p.read_bytes()).hexdigest(),match=hashlib.sha256(p.read_bytes()).hexdigest()==expected)
rows=[]
for c in json.load(open(H/'frozen/original_experiment/cases.json')):
 files=sorted((B/'results').glob('B_CDF_DRO_MITM_%02d_r*.json.gz'%c['index']));runs=[json.load(gzip.open(p,'rt')) for p in files];costs=[r['selected']['cost'] for r in runs]
 rows.append(dict(**c,n=len(runs),best=min(costs),avg=float(np.mean(costs)),std=float(np.std(costs,ddof=1)),mean_found=float(np.mean([r['selected']['found_seconds'] for r in runs])),mean_runtime=float(np.mean([r['runtime_before_save'] for r in runs])),records={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
reg=json.load(open(H/'frozen/original_experiment/source_inputs.json'));raw=[(k,v) for k,v in reg.items() if '/benchmark/' in k];bad=[k for k,v in raw if hashlib.sha256(pathlib.Path(k).read_bytes()).hexdigest()!=v]
out=dict(original_source_matches=result,raw_input_files=len(raw),raw_mismatches=bad,rows=rows);(H/'BASELINE_AUDIT.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(source_matches=all(d['match'] for d in result.values()),raw_input_files=len(raw),raw_mismatches=len(bad),cases=len(rows),runs=sum(r['n'] for r in rows),example_time_case39=rows[38]['mean_found'])))

from pathlib import Path
import json,hashlib,subprocess,time,argparse
H=Path(__file__).parent;I=H/'iterations/I005_exact_cdf_bound';ap=argparse.ArgumentParser();ap.add_argument('--index',type=int,required=True);ap.add_argument('--seconds',type=int,default=30);a=ap.parse_args();J=I/f'case{a.index}';J.mkdir(exist_ok=True);out=J/'probe_old_30.json'
if out.exists() or (J/'REGISTRATION.json').exists():raise RuntimeError('No duplicate case engineering probe')
manifest=json.load(open(I/'ARCHIVE_MANIFEST.json'));source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (I/'candidate').glob('*.py')}
if source!=manifest['source_sha256']:raise RuntimeError('Frozen source changed')
c=next(c for c in json.load(open(H/'CASES.json')) if c['index']==a.index);ref=next(r for r in json.load(open(H/'BASELINE_S10.json'))['rows'] if r['index']==a.index)
reg=dict(time=time.time(),source_sha256=source,index=a.index,instance=c['instance'],capacity=c['tmax'],cost_limit=str(ref['old_best']),bins=256,seconds=a.seconds,watchdog=a.seconds+50,purpose='bounded raw exact proof engineering trial, not formal30run; any unfinished/unresolved tree is not a global exclusion',only_scalar_cost_target=True,no_historical_vector=True,no_LSS_calls=True,formal_source_unchanged=True)
(J/'REGISTRATION.json').write_text(json.dumps(reg,indent=2));cmd=['/home/junhao/miniconda3/bin/python','-u',str(I/'candidate/run_bound.py'),'--instance','/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance'],'--capacity',str(c['tmax']),'--cost-limit',reg['cost_limit'],'--bins','256','--seconds',str(a.seconds),'--out',str(out)]
with (J/'probe.log').open('x') as f:start=time.monotonic();r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=reg['watchdog'])
(J/'TERMINAL.json').write_text(json.dumps(dict(exit=r.returncode,wall=time.monotonic()-start,source_sha256=source),indent=2))
if r.returncode:raise RuntimeError('Probe failed; retain records')
d=json.load(open(out));print(json.dumps({k:d[k] for k in ['status','cost_limit','total_combinations','visited_nodes','terminal_counts','covered_combinations','remaining_combinations','raw_cost_line_excluded','elapsed']}))

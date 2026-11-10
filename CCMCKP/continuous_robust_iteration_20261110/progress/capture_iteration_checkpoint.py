"""Actual narrow process/marker/progress observation, never optimizer input."""
from pathlib import Path
import json,time,datetime
H=Path(__file__).resolve().parent;F=H/'formal/F001_I002_40x30';D=H/'research/D003_paired_stability_prefix';J=H/'iterations/I016_cdf_pair_cover/engineering39';P=H/'progress';P.mkdir(exist_ok=True)
def read(path):
 return json.load(open(path)) if path.exists() else None
def live(pid,signature):
 p=Path('/proc')/str(pid)/'cmdline'
 return p.exists() and signature.encode() in p.read_bytes()
def task(root,launchfile,signature):
 d=read(root/launchfile)
 return None if not d else dict(pid=d['pid'],confirmed_live=live(d['pid'],signature))
fa=read(F/'AUDIT_PROGRESS.json');posts=[read(p) for p in (F/'validation').glob('*.post.json')];native=read(D/'RESULT.json') or read(D/'PROGRESS.json');nsummary=None
if native:
 a=native['accounting'];nsummary=dict(result_file='RESULT.json' if (D/'RESULT.json').exists() else 'PROGRESS.json',batches=native.get('batch',len(native.get('batches',[]))),physical_attempts=a['physical_new_attempts'],all_prefixes_complete=a['all_prefixes_complete'],controller_error=native.get('controller_error'),pools={name:dict(prefix_complete=r['prefix_complete'],accepted=r['accepted'],selected_cost=(r['selected'] or {}).get('cost'),known_upper_cost=(r['known_feasible_upper'] or {}).get('cost'),missing=len(r['missing_keys']),failures=len(r['failed_keys'])) for name,r in a['pools'].items()})
result=dict(time=time.time(),scope=__doc__,formal_F001=dict(controller=dict(pid=924526,confirmed_live=live(924526,'run_f001_stages.py')),stage=read(F/'STAGE.json'),search_progress=read(F/'SEARCH_PROGRESS.json'),last_independent_progress_audit=None if fa is None else {k:v for k,v in fa.items() if k!='rows'},search_finished=(F/'search/FINISHED').exists(),validation_finished=(F/'validation/FINISHED').exists(),actual_validation_records=len(posts),actual_validation_qualified=sum(p['accepted'] for p in posts),validation_errors=[p.get('error') for p in posts if p.get('error')],final_audit_exists=(F/'FINAL_AUDIT_STATS.json').exists()),D003=dict(controller=task(D,'LAUNCH.json','run_d003_stability_prefix.py'),postcontroller=task(D,'POSTPROCESS_LAUNCH.json','postprocess_d003_stability.py'),progress=nsummary,post_state=read(D/'POSTPROCESS_STATE.json'),post_terminal=read(D/'POSTPROCESS_TERMINAL.json'),three_seed_statistics_ready=(D/'DEVELOPMENT_3SEED_STATISTICS.json').exists()),I016=dict(controller=task(J,'LAUNCH.json','run_i016_engineering39.py'),postcontroller=task(J,'POSTPROCESS_LAUNCH.json','postprocess_i016_engineering39.py'),terminal=read(J/'TERMINAL.json'),post_state=read(J/'POSTPROCESS_STATE.json'),post_terminal=read(J/'POSTPROCESS_TERMINAL.json'),independent_raw_audit_exists=(J/'INDEPENDENT_RAW_AUDIT.json').exists()))
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=P/('LIVE_'+stamp+'.json')
with out.open('x') as f:json.dump(result,f,indent=2)
(P/'LATEST.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(snapshot=out.name,**result)))

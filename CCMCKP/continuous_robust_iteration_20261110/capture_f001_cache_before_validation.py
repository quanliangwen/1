from pathlib import Path
import json,hashlib,time
H=Path(__file__).parent;F=H/'formal/F001_I002_40x30';out=F/'CACHE_BEFORE_VALIDATION.json'
if out.exists():raise RuntimeError('Preserve the first inventory')
stage=json.load(open(F/'STAGE.json'))
if stage['stage']!='search':raise RuntimeError('Capture only before the formal native-MC phase')
launch=json.load(open(F/'LAUNCH.json'));reference=json.load(open(H/'REFERENCE_SHA256.json'))['files'];data_ref=json.load(open(H/'LSS_DATA_REFERENCE.json'))['dataset_sha256'];rows=[]
for p in sorted((H/'lss_cache').glob('*.json')):
 d=json.load(open(p));identity={k:d[k] for k in ['instance','capacity','selection','seed','draws','event']}
 if hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()!=p.stem or d['source_sha256']!=reference or d['seed']!=832273 or d['draws']!=10000000 or d['event']!='sum<=T' or d['passed']!=(d['real_probability']>=.985):raise RuntimeError('Bad existing native cache identity')
 for name,sha in d['distribution_sha256'].items():
  if data_ref[d['instance']+'/'+name]!=sha:raise RuntimeError('Distribution metadata identity drift')
 rows.append(dict(key=p.stem,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mtime=p.stat().st_mtime,seconds=d['seconds']))
before=all(r['mtime']<=launch['start_time'] for r in rows)
if not before:raise RuntimeError('Some native call postdates formal launch; investigate before claiming initial inventory')
result=dict(captured_time=time.time(),stage='search before any formal native validation',capture_is_after_launch=True,all_native_records_mtime_at_or_before_launch=before,launch_time=launch['start_time'],calls=len(rows),source_and_distribution_identities_verified=True,purpose='baseline for final physical-new native-call accounting; not optimizer input',files=rows)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='files'}))

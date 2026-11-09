"""Read-only forecast of unresolved original-LSS identities; no selection/MC."""
from pathlib import Path
import json,gzip,hashlib,collections,time
H=Path(__file__).parent;D=H/'formal/F001_I002_40x30';S=D/'search';cases={c['index']:c for c in json.load(open(H/'CASES.json'))};source=json.load(open(D/'REGISTRATION.json'))['source_sha256'];reference=json.load(open(H/'REFERENCE_SHA256.json'));before=json.load(open(D/'CACHE_BEFORE_VALIDATION.json'));inventory={r['key']:r for r in before['files']};cache={};unknown=set();summary=collections.defaultdict(collections.Counter);errors=[];snapshot=[]
for p in sorted(S.glob('*.terminal.json')):
 t=json.load(open(p));i=t['index'];c=cases[i];summary[i]['finished_searches']+=1
 if t['exit']!=0:summary[i]['search_errors']+=1;continue
 result=p.with_name(p.name[:-len('.terminal.json')]);meta=json.load(open(str(result)+'.run.json'));d=json.loads(gzip.decompress(result.read_bytes()))
 if meta['source_sha256']!=source or d['instance']!=c['instance'] or d['capacity']!=c['tmax'] or d['seed']!=t['seed']:raise RuntimeError('Frozen run identity mismatch')
 pending=[];known_pass=None;prefix_rejects=0
 for r in d['candidate_shortlist']:
  identity=dict(instance=c['instance'],capacity=float(c['tmax']),selection=r['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
  if key not in inventory:unknown.add(key);pending.append(key);continue
  if key not in cache:
   file=H/'lss_cache'/(key+'.json');v=json.load(open(file))
   if hashlib.sha256(file.read_bytes()).hexdigest()!=inventory[key]['sha256'] or any(v[k]!=x for k,x in identity.items()) or v['source_sha256']!=reference['files'] or v['reference_zip_sha256']!=reference['zip_sha256'] or v['passed']!=(v['real_probability']>=.985) or v['numpy']!='1.24.4' or v['scipy']!='1.10.1':raise RuntimeError('Cached original-call identity mismatch')
   cache[key]=v
  v=cache[key]
  if v['passed']:known_pass=key;break
  prefix_rejects+=1
 status='known_pass_after_unresolved' if known_pass and pending else 'complete_cached_prefix' if known_pass else 'unresolved_without_known_pass' if pending else 'known_pool_exhausted'
 summary[i][status]+=1;summary[i]['unknown_logical_before_known_pass']+=len(pending);snapshot.append(dict(index=i,seed=t['seed'],search_sha256=hashlib.sha256(result.read_bytes()).hexdigest(),classification=status,unknown_before_known_pass=pending,known_passing_upper_key=known_pass,known_rejects_before_upper=prefix_rejects))
out=dict(scope='diagnostic of already frozen searches against pre-formal original-LSS inventory only; no official postselection, MC calls, Avg or Std, no optimizer feedback',time=time.time(),searches_observed=len(snapshot),inventory_size=len(inventory),unique_unknown_before_known_upper=len(unknown),complete_cached_prefixes=sum(x['classification']=='complete_cached_prefix' for x in snapshot),all_cases=[dict(index=i,instance=cases[i]['instance'],tmax=cases[i]['tmax'],**summary[i]) for i in sorted(summary)],runs=snapshot,new_MC_calls=0)
(D/'FROZEN_PREFIX_DIAGNOSTIC.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['all_cases','runs']}));print(json.dumps(out['all_cases']))

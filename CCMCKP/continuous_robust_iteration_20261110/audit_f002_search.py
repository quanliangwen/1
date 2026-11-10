"""Whole1200 registered search/source/raw audit. Never run original native MC."""
from pathlib import Path
from fractions import Fraction as F
import json,gzip,hashlib,pickle,time,math
from f002_lineage import check as lineage
from independent_raw_recount import upward_grid_count,rational_joint_count
H=Path(__file__).resolve().parent;D=H/'formal/F002_I016_40x30';S=D/'search';out=D/'INDEPENDENT_SEARCH_RAW_AUDIT.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def audit():
 if out.exists():raise RuntimeError('No complete formal search audit overwrite')
 if not (D/'SEARCH_FINISHED').exists():raise RuntimeError('All1200 actual formal attempts must finish before raw audit')
 started=time.monotonic();reg=json.load(open(D/'REGISTRATION.json'));cases={r['index']:r for r in json.load(open(H/'CASES.json'))};source=H/reg['candidate'];vendor=(source.parent/'vendor313').resolve();models={};unique={};rows=[];protocol=[]
 if sha(H/'CASES.json')!=reg['casebook_sha256'] or {p.name:sha(p) for p in source.glob('*.py')}!=reg['source_sha256']:raise RuntimeError('Frozen source/casebook changed')
 for name,digest in {**reg['driver_sha256'],**reg['vendor_sha256']}.items():
  if sha(H/name)!=digest:raise RuntimeError('Frozen driver/dependency changed')
 for name,digest in reg['raw_input_sha256'].items():
  if sha(Path(name))!=digest:raise RuntimeError('Frozen original input changed')
 expected={f'cdf_pair_cover_{i:02d}_seed{seed}.json.gz':(i,seed) for i in reg['cases'] for seed in reg['seeds']}
 if len(expected)!=1200 or {p.name[:-len('.terminal.json')] for p in S.glob('*.terminal.json')}!=set(expected):raise RuntimeError('Exactly1200 unique registered terminal attempts required')
 dispatched=json.load(open(S/'DISPATCH_RESULTS.json'))
 if len(dispatched)!=1200 or {(r['index'],r['seed']) for r in dispatched}!=set(expected.values()):raise RuntimeError('Dispatcher omitted/replaced an original attempt')
 for c in cases.values():
  if c['instance'] in models:continue
  P=Path(reg['benchmark'])/c['instance'];ids={Path(p).name:d for p,d in reg['raw_input_sha256'].items() if Path(p).parent==P};cost=[F(x) for x in (P/'cost.txt').read_text().split()];groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;arrays={int(n.split('_')[0]):[F(x) for x in (P/n).read_text().split()] for n in ids if n.endswith('_sample.txt')};models[c['instance']]=dict(path=P,ids=ids,cost=cost,groups=groups,arrays=arrays)
 def collect(data,model,records):
  if records!=sorted(records,key=lambda r:(r['cost'],r['selection'])) or len({tuple(r['selection']) for r in records})!=len(records):raise RuntimeError('Frozen pool not unique canonical cost order')
  for r in records:
   q=r['selection'];cert=r['certificate'];groups=model['groups']
   if len(q)!=len(groups) or len(set(q))!=len(q) or any(j not in groups[g] for g,j in enumerate(q)) or cert['selection']!=q or cert['method'] not in ['exact_integer_upward_grid_count','outward_interval_integer_pair_count'] or cert['strict_event']!='sum<T' or not cert['all_original_samples'] or 100*int(cert['lower_numerator'])<99*int(cert['denominator']) or abs(r['cost']-float(sum((model['cost'][j] for j in q),F(0))))>1e-9:raise RuntimeError('Original canonical raw99 member/cost differs')
   key=(data['instance'],F(str(data['capacity'])),tuple(q),cert['method'],cert.get('bins'),cert['lower_numerator'],cert.get('upper_numerator'),cert['denominator']);unique[key]=cert
 for name,(i,seed) in sorted(expected.items(),key=lambda x:(x[1][0],x[1][1])):
  c=cases[i];model=models[c['instance']];P=model['path'];file=S/name;terminal=json.load(open(str(file)+'.terminal.json'));row=dict(index=i,seed=seed,instance=c['instance'],capacity=c['tmax'],result_file=file.relative_to(H).as_posix(),exit=terminal['exit'],error=terminal['error'],protocol_valid=False)
  if terminal['index']!=i or terminal['seed']!=seed or terminal['method']!='cdf_pair_cover' or terminal['registration_sha256']!=sha(D/'REGISTRATION.json'):raise RuntimeError('Original terminal namespace changed')
  if terminal['exit']!=0 or terminal['error'] is not None:
   protocol.append(dict(index=i,seed=seed,error=terminal['error'] or terminal['exit']));rows.append(row);continue
  data=json.loads(gzip.decompress(file.read_bytes()));meta=json.load(open(str(file)+'.run.json'))
  if terminal['result_sha256']!=sha(file) or terminal['meta_sha256']!=sha(Path(str(file)+'.run.json')) or meta['source_sha256']!=reg['source_sha256'] or meta['input_sha256']!=model['ids'] or meta['seed']!=seed or data['seed']!=seed or data['instance']!=c['instance'] or F(str(data['capacity']))!=F(str(c['tmax'])) or meta['risk_method']!='cdf_pair_cover' or meta['budget']!=600:raise RuntimeError('Actual result/meta/source/input/method identity differs')
  if meta['numpy']!='2.4.0' or meta['scipy']!='1.17.1' or meta['flint']!='0.8.0':raise RuntimeError('Actual numerical environment changed')
  cfg=data['config']
  if cfg['raw_threshold']!='.99' or cfg['external_real_P_threshold']!=.985 or cfg['external_MC_seed']!=832273 or cfg['external_MC_draws']!=10000000 or cfg['tail_hard_gate'] or not cfg['all_original_samples']:raise RuntimeError('Original acceptance rule changed')
  own={str(file),str(file)+'.tmp',str(file)+'.run.json',str(file)+'.run.json.tmp',str(file.parent)}
  for opened in meta['opened_task_paths']:
   path=Path(opened)
   if path.name.endswith('_dist.txt') or '/lss_cache/' in opened or path.name=='BASELINE_S10.json':raise RuntimeError('True/history/native cache input entered formal optimizer')
   if P in path.parents and path.name not in model['ids']:raise RuntimeError('Unregistered benchmark input read')
   if H.parent in path.parents and not (source in path.parents or path==source or vendor in path.parents or path==vendor or opened in own):raise RuntimeError('Another saved run/task read entered formal optimizer')
  pool=data['candidate_shortlist'];collect(data,model,pool)
  if data['raw_certified_pool_count']!=len(pool):raise RuntimeError('Complete raw candidate pool count differs')
  problem=None
  if meta['within_budget']!=(meta['elapsed']<=600):raise RuntimeError('Inconsistent actual global budget report')
  if data['status']!='completed' or not meta['within_budget']:problem='incomplete or global budget overrun'
  try:
   certificates,report=lineage(data,model['cost'],model['groups'])
   for (instance,capacity,q,bins,n,d),cert in certificates.items():
    key=(instance,F(str(capacity)),q,cert['method'],bins,n,cert.get('upper_numerator'),d);unique[key]=cert
  except Exception as ex:problem='lineage/shared-phase: '+str(ex)
  row.update(protocol_valid=problem is None,result_sha256=sha(file),meta_sha256=sha(Path(str(file)+'.run.json')),search_seconds=meta['elapsed'],phase_seconds=data['extension']['extension_seconds'],raw_candidates=len(pool),lineage_error=problem)
  if problem:protocol.append(dict(index=i,seed=seed,error=problem))
  rows.append(row)
  if len(rows)%50==0:(D/'RAW_AUDIT_PROGRESS.json').write_text(json.dumps(dict(stage='source/lineage',attempts=len(rows),required_attempts=1200,time=time.time())))
 proof=[];minimum=None
 for number,((instance,capacity,q,method,bins,oldn,oldu,oldd),cert) in enumerate(unique.items(),1):
  arrays=[models[instance]['arrays'][j] for j in q]
  if method=='exact_integer_upward_grid_count':
   n,d=upward_grid_count(arrays,capacity,bins)
   if str(n)!=oldn or str(d)!=oldd:raise RuntimeError('Independent formal original grid count differs')
  else:
   if len(arrays)>5:raise RuntimeError('Interval method used outside small scope')
   n,d=rational_joint_count(arrays,capacity)
   if d!=int(oldd) or not int(oldn)<=n<=int(oldu):raise RuntimeError('Small interval does not enclose independent rational count')
  if 100*n<99*d:raise RuntimeError('Independently recounted formal pool member fails original99')
  ratio=F(n,d);minimum=ratio if minimum is None else min(minimum,ratio);proof.append(dict(instance=instance,capacity=float(capacity),selection=list(q),method=method,bins=bins,original_lower_numerator=oldn,original_upper_numerator=oldu,numerator=str(n),denominator=str(d)))
  if number%50==0 or number==len(unique):
   progress=dict(stage='independent full original raw counts',done=number,required=len(unique),seconds=time.monotonic()-started);(D/'RAW_AUDIT_PROGRESS.json').write_text(json.dumps(progress));print(json.dumps(progress),flush=True)
 pf=D/'RAW_CERTIFICATE_RECOUNTS.json.gz'
 with pf.open('xb') as f:f.write(gzip.compress(json.dumps(proof).encode(),compresslevel=6))
 result=dict(integrity_passed=True,passed=not protocol,scope=__doc__+'; all attempts retained; no native qualification or30-run Avg',registered_attempts=1200,protocol_valid=sum(r['protocol_valid'] for r in rows),protocol_errors=protocol,pools=rows,unique_raw_certificates=len(proof),minimum_independent_raw_lower=float(minimum) if minimum is not None else None,raw_recounts_file=pf.relative_to(H).as_posix(),raw_recounts_sha256=sha(pf),registration_sha256=sha(D/'REGISTRATION.json'),new_original_MC_calls=0,seconds=time.monotonic()-started)
 with out.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ['pools','protocol_errors']}))
if __name__=='__main__':audit()

"""Completed original-native predicates only; deterministic aliases, no MC.

Capture and register a final catalogue only after its new search cohort freezes.
A separate read-only preflight may exercise this builder earlier, without being
the actual study catalogue. Invalid completed receipts fail before any native
attempt; concurrently incomplete new shared files are reported and omitted as
unknown, never treated as rejections.
"""
from pathlib import Path
import json,time,hashlib
from isolated_original_lss import IsolatedOriginalLSS,sha,identity_key

def build_completed_catalogue(root,private_dir):
 H=Path(root).resolve();started=time.time();catalogue={};aliases=[];inputs=[];orig=H/'formal/F001_I002_40x30/CACHE_BEFORE_VALIDATION.json';initial=json.load(open(orig));inputs.append(orig.relative_to(H).as_posix())
 if len(initial['files'])!=448:raise RuntimeError('Original448identity snapshot required')
 def add(key,path,digest,origin):
  record=dict(path=path,sha256=digest)
  if key in catalogue:
   if catalogue[key]!=record:aliases.append(dict(key=key,preferred=dict(catalogue[key]),alias=record,origin=origin))
  else:catalogue[key]=record
 for r in initial['files']:add(r['key'],'lss_cache/'+r['key']+'.json',r['sha256'],'original448')
 D1=H/'research/D001_isolated_precision_LSS';r=json.load(open(D1/'RESULT.json'));a=json.load(open(D1/'INDEPENDENT_RECEIPT_AUDIT.json'))
 if r['errors'] or len(r['rows'])!=6 or not a['passed'] or a['result_sha256']!=sha(D1/'RESULT.json') or a['registration_sha256']!=sha(D1/'REGISTRATION.json'):raise RuntimeError('Actual completed D001 proof differs')
 inputs.extend((D1/n).relative_to(H).as_posix() for n in ['RESULT.json','INDEPENDENT_RECEIPT_AUDIT.json','REGISTRATION.json'])
 for row in r['rows']:add(row['key'],row['private_receipt'],row['receipt_sha256'],'completed_D001')
 for name,count in [('D002_isolated_full_prefix',36),('D003_paired_stability_prefix',57),('D004_I016_full_prefix',31)]:
  D=H/'research'/name;r=json.load(open(D/'RESULT.json'));a=json.load(open(D/'INDEPENDENT_FINAL_AUDIT.json'))
  if r['controller_error'] or not r['accounting']['all_prefixes_complete'] or len(r['private_new_outcomes'])!=count or not a['passed'] or a['result_sha256']!=sha(D/'RESULT.json') or a['registration_sha256']!=sha(D/'REGISTRATION.json'):raise RuntimeError('Actual completed prior private proof differs '+name)
  inputs.extend((D/n).relative_to(H).as_posix() for n in ['RESULT.json','INDEPENDENT_FINAL_AUDIT.json','REGISTRATION.json'])
  for key,row in r['private_new_outcomes'].items():
   if row['error'] or not row['new_attempt']:raise RuntimeError('Prior private attempt failed')
   add(key,row['receipt_path'],row['receipt_sha256'],'completed_'+name)
 if len(catalogue)!=578 or aliases:raise RuntimeError('Expected578distinct original/private identities before shared aliases')
 fixed578_keys=set(catalogue);shared_files=sorted((H/'lss_cache').glob('*.json'));skipped=[]
 for file in shared_files:
  stable=None;error=None
  for attempt in range(3):
   try:
    data=file.read_bytes();value=json.loads(data)
    if file.read_bytes()!=data:raise ValueError('shared receipt still being written')
    stable=hashlib.sha256(data).hexdigest();break
   except (OSError,ValueError) as exception:error=str(exception);time.sleep(.05)
  if stable is None:
   if file.stem in fixed578_keys:raise RuntimeError('Pinned original/private identity not complete '+file.name)
   skipped.append(dict(path=file.relative_to(H).as_posix(),reason=error,classification='inflight_or_unavailable_shared_identity_not_used; remains unknown, not rejection'));continue
  add(file.stem,file.relative_to(H).as_posix(),stable,'completed_shared_snapshot')
 native=IsolatedOriginalLSS(H,private_dir,catalogue);outcomes={};validated=0
 for key,row in catalogue.items():
  v=json.load(open(H/row['path']));identity={k:v[k] for k in ['instance','capacity','selection','seed','draws','event']}
  if identity_key(identity)!=key or identity['seed']!=832273 or identity['draws']!=10000000 or identity['event']!='sum<=T':raise RuntimeError('Completed catalogue identity/seed/event differs')
  outcomes[key]=native.read_catalogue(key,identity);validated+=1
 for row in aliases:
  original=json.load(open(H/row['preferred']['path']));identity={k:original[k] for k in ['instance','capacity','selection','seed','draws','event']};alias=native.validate(H/row['alias']['path'],identity,row['alias']['sha256'])
  if alias['real_probability']!=original['real_probability'] or alias['passed']!=original['passed']:raise RuntimeError('Same exact native identity has inconsistent original point estimate')
  row['point_and_decision_identical']=True;validated+=1
 check=dict(passed=True,capture_started=started,capture_finished=time.time(),fixed_original_and_private_identities=578,checked_unique=len(catalogue),shared_snapshot_files_observed=len(shared_files),checked_aliases=len(aliases),validated_receipts_including_aliases=validated,aliases=aliases,skipped_shared_files=skipped,source_sha256=sha(Path(__file__)),helper_sha256=sha(H/'isolated_original_lss.py'),input_sha256={n:sha(H/n) for n in inputs},new_MC_calls=0,deterministic_priority='original448, completedD0016/D00236/D00357/D00431, then stable completed shared files sorted by key; retain earlier receipt on alias, validate both predicates exactly',scope='original full native source21/env/current true-data/identity/role validated by unchanged helper; no optimization inputs or new MC; previous physical executions/duplicates stay separately billed')
 return catalogue,outcomes,check

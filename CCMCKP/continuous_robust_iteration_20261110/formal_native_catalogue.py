"""Extend frozen completed-native builder with complete D005/D006 private ledgers.

This is read-only. Capture an actual formal catalogue after all1200searches and
their raw audit freeze. A separate earlier preflight never registers that final
catalogue and launches no native simulation.
"""
from pathlib import Path
import json,time
from frozen_native_catalogue import build_completed_catalogue
from isolated_original_lss import IsolatedOriginalLSS,identity_key,sha
def build(root,private_dir):
 H=Path(root).resolve();cat,outcomes,old=build_completed_catalogue(H,private_dir);native=IsolatedOriginalLSS(H,private_dir,cat);aliases=[];inputs=dict(old['input_sha256']);added=0;receipt_checks=0
 for study,attempts in [('D005_I016_pair_prefix',75),('D006_I016_breadth_prefix',14)]:
  D=H/'research'/study;r=json.load(open(D/'RESULT.json'));a=json.load(open(D/'INDEPENDENT_FINAL_AUDIT.json'));post=json.load(open(D/'POSTPROCESS_TERMINAL.json'))
  if not a['passed'] or not post['passed'] or r['controller_error'] or not r['accounting']['all_prefixes_complete'] or a['result_sha256']!=sha(D/'RESULT.json') or a['registration_sha256']!=sha(D/'REGISTRATION.json') or len(r['private_new_outcomes'])!=attempts:raise RuntimeError('Whole previous completed89 physical private receipts required')
  for n in ['REGISTRATION.json','RESULT.json','INDEPENDENT_FINAL_AUDIT.json','POSTPROCESS_TERMINAL.json','DEVELOPMENT_COMPARISON.json']:inputs[(D/n).relative_to(H).as_posix()]=sha(D/n)
  for key,row in sorted(r['private_new_outcomes'].items()):
   p=H/row['receipt_path'];v=json.load(open(p));identity={k:v[k] for k in ['instance','capacity','selection','seed','draws','event']}
   if row['error'] or not row['new_attempt'] or identity_key(identity)!=key:raise RuntimeError('Previous actual original native physical identity differs')
   value=native.validate(p,identity,row['receipt_sha256']);receipt_checks+=1
   if value['real_probability']!=row['probability'] or value['passed']!=row['passed']:raise RuntimeError('Previous independently completed ledger differs from receipt')
   record=dict(path=row['receipt_path'],sha256=row['receipt_sha256'])
   if key in cat:
    preferred=json.load(open(H/cat[key]['path']))
    if preferred['real_probability']!=value['real_probability'] or preferred['passed']!=value['passed']:raise RuntimeError('Same original fixed identity has inconsistent probability aliases')
    if record!=cat[key]:aliases.append(dict(key=key,preferred=dict(cat[key]),alias=record,origin='completed_'+study))
   else:
    cat[key]=record;outcomes[key]=dict(key=key,passed=value['passed'],probability=value['real_probability'],seconds=value['seconds'],origin='pinned_readonly_catalogue',receipt_path=record['path'],receipt_sha256=record['sha256'],new_attempt=False,attempt_wall=0.,error=None);added+=1
 result=dict(passed=True,time=time.time(),scope=__doc__,base_builder_source_sha256=sha(H/'frozen_native_catalogue.py'),source_sha256=sha(Path(__file__)),input_sha256=inputs,base_check=old,unique=len(cat),prior89_physical_receipts_checked=receipt_checks,added_unique=added,added_aliases=aliases,new_MC_calls=0)
 return cat,outcomes,result

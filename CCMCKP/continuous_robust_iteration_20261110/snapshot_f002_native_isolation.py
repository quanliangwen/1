"""Read-only shared-cache observations, allowing independently scheduled growth."""
from pathlib import Path
import argparse,json,time
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;D=H/'research/F002_I016_formal_native';F=H/'formal/F001_I002_40x30'
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['before','after'],required=True);phase=p.parse_args().phase
out=D/('FORMAL_ISOLATION_'+phase.upper()+'.json')
if out.exists():raise RuntimeError('No isolation observation overwrite')
files={};skipped=[]
for file in sorted((H/'lss_cache').glob('*.json')):
 try:
  raw=file.read_bytes();json.loads(raw)
  if file.read_bytes()!=raw:raise ValueError('concurrent incomplete shared write')
  import hashlib
  files[file.name]=hashlib.sha256(raw).hexdigest()
 except (OSError,ValueError) as error:skipped.append(dict(name=file.name,reason=str(error),scope='inflight shared receipt not asserted complete'))
logs=[p.name for p in sorted((H/'lss_cache').glob('*.log'))];old={r['key']+'.json':r['sha256'] for r in json.load(open(F/'CACHE_BEFORE_VALIDATION.json'))['files']}
if not all(files.get(k)==v for k,v in old.items()):raise RuntimeError('An original pinned receipt changed')
result=dict(time=time.time(),scope='read-only auditor never passed to optimizer/native; independently scheduled formal/shared cache may grow; F002 private paths enforced by helper/controller',formal_stage=json.load(open(F/'STAGE.json')),shared_receipt_sha256=files,shared_log_names=logs,original448_unchanged=True,shared_receipt_count=len(files),shared_log_count=len(logs),skipped_inflight_shared_files=skipped)
if phase=='after':
 before=json.load(open(D/'FORMAL_ISOLATION_BEFORE.json'));result.update(original_receipts_unchanged=all(files.get(k)==v for k,v in before['shared_receipt_sha256'].items()),inventory_identical_to_before=files==before['shared_receipt_sha256'],log_names_identical_to_before=logs==before['shared_log_names'],additional_shared_receipts=sorted(set(files)-set(before['shared_receipt_sha256'])))
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['shared_receipt_sha256','shared_log_names','additional_shared_receipts']}))

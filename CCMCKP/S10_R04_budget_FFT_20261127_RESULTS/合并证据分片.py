from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent
p=json.loads((R/'证据分片清单.json').read_text(encoding='utf-8'))
out=R/p['archive_name']
assert not out.exists(),'Refuse overwrite'
h=hashlib.sha256()
with out.open('xb') as f:
 for name in p['parts']:
  with (R/name).open('rb') as src:
   while True:
    b=src.read(2**20)
    if not b:break
    f.write(b);h.update(b)
assert h.hexdigest()==p['sha256'] and out.stat().st_size==p['bytes']
print('SHA256 verified',p['sha256'])

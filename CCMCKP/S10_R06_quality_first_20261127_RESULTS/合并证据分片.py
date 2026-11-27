from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent
p=json.loads((R/'证据分片清单.json').read_text(encoding='utf-8'))
out=R/p['joined_name']
assert not out.exists()
with out.open('xb') as f:
 for q in p['parts']:
  data=(R/q['name']).read_bytes();assert hashlib.sha256(data).hexdigest()==q['sha256'];f.write(data)
assert hashlib.sha256(out.read_bytes()).hexdigest()==p['joined_sha256']
print(out)

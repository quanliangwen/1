from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;P=json.loads((R/'证据分片清单.json').read_text(encoding='utf-8'));out=R/P['archive'];assert not out.exists()
h=hashlib.sha256()
with out.open('xb') as f:
 for q in P['parts']:
  b=(R/q['name']).read_bytes();assert len(b)==q['bytes'] and hashlib.sha256(b).hexdigest()==q['sha256'];f.write(b);h.update(b)
assert out.stat().st_size==P['archive_bytes'] and h.hexdigest()==P['archive_sha256'];print('SHA256 verified:',h.hexdigest())

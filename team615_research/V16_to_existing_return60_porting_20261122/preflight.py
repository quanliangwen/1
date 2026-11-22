"""Read-only version check for a migration destination; never writes source."""
from pathlib import Path
from hashlib import sha256
import json,sys
root=Path(__file__).resolve().parent
manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf8'))
target=Path(sys.argv[1]).resolve()
def norm(data):return data.replace(b'\r\n',b'\n')
rows=[]
for name,expected in manifest['files'].items():
    path=target/name
    if not path.is_file():state='MISSING'
    else:
        data=path.read_bytes();digest=sha256(data).hexdigest();normalized=sha256(norm(data)).hexdigest()
        if digest==expected['v16_sha256']==expected['return60_sha256']:state='UNCHANGED_SHARED'
        elif digest==expected['v16_sha256']:state='EXACT_V16'
        elif digest==expected['return60_sha256']:state='EXACT_RETURN60'
        elif normalized==expected['v16_lf_sha256']:state='TEXT_EQUIVALENT_V16_REVIEW_LINE_ENDINGS'
        elif normalized==expected['return60_lf_sha256']:state='TEXT_EQUIVALENT_RETURN60_REVIEW_LINE_ENDINGS'
        else:state='DIFFERENT_MANUAL_MERGE_REQUIRED'
    rows.append(dict(file=name,changed_by_migration=expected['changed'],state=state))
before=all(x['state'] in ('UNCHANGED_SHARED','EXACT_V16') for x in rows)
after=all(x['state'] in ('UNCHANGED_SHARED','EXACT_RETURN60') for x in rows)
result=dict(directory=str(target),read_only=True,files_written=0,
    classification='EXACT_V16' if before else 'EXACT_RETURN60' if after else 'REQUIRES_REVIEW',
    files=rows)
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(0 if before or after else 2)

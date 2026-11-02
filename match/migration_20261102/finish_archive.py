from pathlib import Path
import json,hashlib,zipfile,datetime,os
BASE=Path(__file__).resolve().parent;STAGE=BASE/'staged'
assert not (BASE/'PREPARATION.json').exists()
first=dict(stage='prepare_archive.py',error='FileNotFoundError: historical V06 path moved by user to 提交版本呢/正常版/team615_red_v06.zip',sdk_or_native_failure=False,existing_completed_archives_retained=True)
(BASE/'PREPARATION_FIRST_ERROR.json').write_text(json.dumps(first,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
game=Path('E:/10.12-10.26算法对抗赛')
v6=game/'提交版本呢/正常版/team615_red_v06.zip'
b=v6.read_bytes();assert hashlib.sha256(b).hexdigest()=='01c9b9de5caad8f280695852e8e0461a66d26feb689339d5de8047ed3e72008c'
dest=STAGE/'submissions/V06';dest.mkdir(parents=True,exist_ok=True);(dest/v6.name).write_bytes(b)
root=Path('E:/codex/PJ01_team615_red_v06_20261029')
for p in root.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(root)
 if len(rel.parts)>2 or '__pycache__' in rel.parts:continue
 if rel.parts[0]!='audit' and len(rel.parts)>1:continue
 if p.suffix.lower() not in {'.json','.txt','.py','.log','.zip','.sha256','.md'}:continue
 data=p.read_bytes()
 # All source/release files had already passed the first public snapshot filter.
 q=dest/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
archives=[];exclusions=[]
skipdirs={'.git','.venv','venv','__pycache__','node_modules','.pytest_cache','github_worktree','runtimes','bootstrap','system','wheels','wheelhouse','.ssh','.aws','.kube'}
for p in sorted(BASE.glob('*.zip')):
 with zipfile.ZipFile(p) as z:
  raw=json.loads(z.read('_ARCHIVE_MANIFEST.json'))
  if isinstance(raw,dict):members=raw['files'];source=Path(raw['source_root']);snap=raw['snapshot_utc']
  else:continue
  included={x['path'] for x in members}
  for d,dirs,names in os.walk(source):
   for sub in dirs:
    if sub.lower() in skipdirs:exclusions.append(dict(path=str(Path(d)/sub),reason='runtime/cache/git/credential directory excluded'))
   dirs[:]=[x for x in dirs if x.lower() not in skipdirs]
   for n in names:
    f=Path(d)/n
    if f.relative_to(source).as_posix() not in included:exclusions.append(dict(path=str(f),reason='excluded by public snapshot policy (raw/private/environment/credential/opaque nested archive)'))
  size=p.stat().st_size;name='archives/'+p.name
  record=dict(path=name,size=size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),member_count=len(members),uncompressed_bytes=sum(x['size'] for x in members),source_root=str(source),snapshot_utc=snap)
  if size>=90*1024**2:
   parts=sorted((STAGE/'archives').glob(p.name+'.part*'));assert sum(x.stat().st_size for x in parts)==size
   joined=hashlib.sha256()
   for part in parts:joined.update(part.read_bytes())
   assert joined.hexdigest()==record['sha256'];record.update(split=True,parts=['archives/'+x.name for x in parts])
  else:assert (STAGE/name).read_bytes()==p.read_bytes()
  archives.append(record)
for p in game.iterdir():
 if p.is_file() and not (STAGE/'reference_materials'/p.name).exists():exclusions.append(dict(path=str(p),reason='Original environment/runtime bundle excluded by public snapshot scan; original retained locally'))
files=[]
for p in sorted(STAGE.rglob('*')):
 if p.is_file():
  b=p.read_bytes();files.append(dict(path=p.relative_to(STAGE).as_posix(),size=len(b),sha256=hashlib.sha256(b).hexdigest()))
report=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,archives=archives,exclusions=exclusions,preparation_first_error=first,local_and_server_originals_retained=True,server_results_not_mass_archived=True,scope='Existing published tree plus filtered local competition reference, source/report histories, environment and submission records. No runtime relocation or server disk cleanup. Excluded private/raw payload, credentials, environments and caches. Historical source dates preserved inside archive manifests.')
(BASE/'PREPARATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='PREPARED',files=len(files),archive_roots=len(archives),excluded=len(exclusions),total_bytes=sum(x['size'] for x in files))))

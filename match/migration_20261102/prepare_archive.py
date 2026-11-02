from pathlib import Path
import os,sys,json,hashlib,zipfile,io,re,datetime

BASE=Path(__file__).resolve().parent
OUT=BASE/'staged'
OUT.mkdir(exist_ok=True)
assert not (BASE/'PREPARATION.json').exists(), 'first snapshot already prepared'
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
excluded=[]; files=[]; archives=[]
skipdirs={'.git','.venv','venv','__pycache__','node_modules','.pytest_cache','github_worktree','runtimes','bootstrap','system','wheels','wheelhouse','.ssh','.aws','.kube'}
badext={'.npz','.npy','.pkl','.pickle','.lic','.pyc','.pyo','.whl','.exe','.dll','.so','.pyd'}
secrets=[re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(rb'github_pat_[A-Za-z0-9_]{50,}'),re.compile(rb'\bAKIA[0-9A-Z]{16}\b'),re.compile(rb'sk-(?:proj-)?[A-Za-z0-9_-]{40,}')]
def forbidden(name):
 p=Path(name);parts=[x.lower() for x in p.parts]; n=p.name.lower()
 if any(x in skipdirs for x in parts):return 'runtime/cache/git/credential directory'
 if p.suffix.lower() in badext:return 'raw array/pickle, environment binary, or credential'
 if n in {'.env','id_rsa','id_ed25519','uv_linux','github_migration.lock'} or n.startswith('.env.'):return 'credential/runtime/publication lock'
 full=str(name).replace('\\','/').lower()
 if ('blue' in full and any(x in full for x in ['console','private','stdout','stderr'])) or ('raw_results' in full):return 'private/raw evaluation payload'
 if any(x in n for x in ['token.secret','credentials.json','service-account']):return 'credential filename'
 return None
def sensitive(data):return any(p.search(data) for p in secrets)
def inspect_zip(data, depth=0):
 try:
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   for m in z.infolist():
    if m.is_dir():continue
    # Original runtime bundle contains public CA certificates; never environment secrets.
    n=m.filename.lower();leaf=Path(n).name
    if leaf in {'.env','id_rsa','id_ed25519','gurobi.lic'} or leaf.endswith('.lic'):return 'archive credential entry'
    if Path(n).suffix in {'.npz','.npy','.pickle','.pkl'} or ('blue' in n and any(x in n for x in ['console','private','stdout','stderr'])) or 'raw_results' in n:return 'archive private/raw payload'
    if m.file_size>150*1024**2:return 'archive member exceeds inspection bound'
    b=z.read(m)
    if sensitive(b):return 'archive high-confidence secret pattern'
    if n.endswith('.zip'):
     if depth>=3:return 'nested archive beyond inspection bound'
     why=inspect_zip(b,depth+1)
     if why:return why
  return None
 except zipfile.BadZipFile:return 'invalid ZIP'
def include(p,rel):
 why=forbidden(rel)
 if why:excluded.append(dict(path=str(p),reason=why));return None
 if p.is_symlink():excluded.append(dict(path=str(p),reason='symlink'));return None
 b=p.read_bytes()
 if sensitive(b):excluded.append(dict(path=str(p),reason='high-confidence secret pattern'));return None
 if p.suffix.lower()=='.zip':
  why=inspect_zip(b)
  if why:excluded.append(dict(path=str(p),reason=why));return None
 # Arbitrary nested tar bundles are retained only locally: no private raw logs embedded in public snapshots.
 if p.name.lower().endswith(('.tar.gz','.tgz','.tar','.7z')):
  excluded.append(dict(path=str(p),reason='opaque nested archive; original retained locally'));return None
 return b
def stage_bytes(dest,b,source=None):
 p=OUT/dest;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 rec=dict(path=dest,size=len(b),sha256=hashlib.sha256(b).hexdigest())
 if source:rec['source']=str(source)
 files.append(rec);return rec
roots=['P48_Astar_iteration_20261102','P48_astar_five_20261102','P48_team615_red_v09_20261102','PJ01_rule_refinement_20261101','PJ01_rule_refinement_20261102','PJ01_environment_restore_20261101','swarm-eod-literature-analysis','UAV_rules_astar_restart_20261030','swarm-submission-guard','PJ01_team615_red_v06_20261029','J17_team615_red_v07_20261030','J17_gurobi_team615_red_v08_20261030']
for rootname in roots:
 root=Path('E:/codex')/rootname
 if not root.exists():excluded.append(dict(path=str(root),reason='not present'));continue
 members=[];dest='archives/'+rootname+'.zip';tmp=BASE/(rootname+'.zip')
 with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for directory,dirs,names in os.walk(root):
   dirs[:]=sorted(d for d in dirs if d.lower() not in skipdirs)
   for name in sorted(names):
    p=Path(directory)/name;rel=p.relative_to(root).as_posix();b=include(p,rel)
    if b is None:continue
    z.writestr(rel,b);members.append(dict(path=rel,size=len(b),sha256=hashlib.sha256(b).hexdigest()))
  z.writestr('_ARCHIVE_MANIFEST.json',json.dumps(dict(source_root=str(root),snapshot_utc=utc(),files=members,not_runtime_relocation=True),ensure_ascii=False,indent=2))
 size=tmp.stat().st_size
 if size<90*1024**2:rec=stage_bytes(dest,tmp.read_bytes(),root)
 else:
  parts=[]
  with tmp.open('rb') as f:
   number=0
   while b:=f.read(48*1024**2):
    number+=1;parts.append(stage_bytes(dest+f'.part{number:03}',b,root))
  rec=dict(path=dest,split=True,parts=[x['path'] for x in parts],size=size,sha256=hashlib.file_digest(tmp.open('rb'),'sha256').hexdigest())
 archives.append(dict(**rec,member_count=len(members),uncompressed_bytes=sum(x['size'] for x in members)))
 print(json.dumps(dict(archive=dest,members=len(members),compressed_bytes=size)),flush=True)

game=Path('E:/10.12-10.26算法对抗赛')
for p in sorted(game.iterdir()):
 if p.is_file():
  b=include(p,p.name)
  if b is not None:stage_bytes('reference_materials/'+p.name,b,p)
for name in ['提交版本呢','算法版本呢']:
 root=game/name;members=[];buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(root.rglob('*')):
   if not p.is_file():continue
   rel=p.relative_to(root).as_posix();b=include(p,rel)
   if b is not None:z.writestr(rel,b);members.append(dict(path=rel,size=len(b),sha256=hashlib.sha256(b).hexdigest()))
  z.writestr('_ARCHIVE_MANIFEST.json',json.dumps(members,ensure_ascii=False,indent=2))
 stage_bytes('archives/original_'+name+'.zip',buffer.getvalue(),root)

releases=[('V09',Path('E:/codex/P48_team615_red_v09_20261102'),Path('E:/codex/P48_team615_red_v09_20261102/team615_red_v09.zip'),'fcef716d6855e7c5048299048e8ebd8216c777663ed75faf2583155d1648abc9'),('V06',Path('E:/codex/PJ01_team615_red_v06_20261029'),game/'提交版本呢/team615_red_v06.zip','01c9b9de5caad8f280695852e8e0461a66d26feb689339d5de8047ed3e72008c')]
for version,root,zp,expected in releases:
 b=zp.read_bytes();assert hashlib.sha256(b).hexdigest()==expected
 stage_bytes('submissions/'+version+'/'+zp.name,b,zp)
 for p in sorted(root.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(root)
  if len(rel.parts)>2 or any(x.lower() in skipdirs for x in rel.parts):continue
  if p==zp:continue
  if rel.parts[0]!='audit' and len(rel.parts)>1:continue
  b=include(p,rel.as_posix())
  if b is not None:stage_bytes('submissions/'+version+'/'+rel.as_posix(),b,p)

report=dict(created_utc=utc(),files=files,archives=archives,exclusions=excluded,local_and_server_originals_retained=True,server_results_not_mass_archived=True,scope='Existing published tree plus filtered local competition references, source/report histories, environment and submission records. No runtime relocation or server disk cleanup.')
(BASE/'PREPARATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='PREPARED',files=len(files),excluded=len(excluded),bytes=sum(x['size'] for x in files)),ensure_ascii=False),flush=True)

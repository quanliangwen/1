from pathlib import Path
import json,hashlib,subprocess,sys,base64,tarfile
R=Path(__file__).resolve().parent;E=R/'evidence';E.mkdir(exist_ok=True)
receipt=json.loads((R/'COLLECTION_RECEIPT.json').read_text()) if (R/'COLLECTION_RECEIPT.json').exists() else {}
known={n:v['sha256'] for n,v in receipt.items()}
script='''from pathlib import Path
import json,hashlib,tarfile,io,time
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/d01_winf_product_20261126';assert Path.cwd()==B
known=KNOWN
C=H/'collection';C.mkdir(exist_ok=True);archive=C/('delta_%s.tar.gz'%time.time_ns())
manifest={};added=[]
with tarfile.open(archive,'w:gz') as tar:
 for p in H.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(H);top=rel.parts[0];name=rel.as_posix()
  if top in ['source','build','bin','fixtures','integration','collection']:continue
  if len(rel.parts)>2 and rel.parts[1]=='runs' and not (H/top/'outcomes'/(rel.parts[2]+'.json')).exists():continue
  if len(rel.parts)>2 and rel.parts[1]=='logs' and not (H/top/'outcomes'/(p.stem+'.json')).exists():continue
  if p.suffix not in ['.json','.jsonl','.log','.txt','.csv','.py']:continue
  data=p.read_bytes();sha=hashlib.sha256(data).hexdigest();manifest[name]={'sha256':sha,'bytes':len(data)}
  if known.get(name)==sha:continue
  info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data));added.append(name)
 raw=json.dumps(manifest,ensure_ascii=False,indent=2).encode();info=tarfile.TarInfo('SYNC_MANIFEST.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
print(json.dumps({'remote_path':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size,'files_added':len(added),'files_total':len(manifest)}))
'''.replace('KNOWN',repr(known))
(R/'collect_tar_remote.py').write_text(script,encoding='utf-8')
out=subprocess.run([sys.executable,'-X','utf8','E:/codex/S10_EGS_OA_20261123/remote.py',str(R/'collect_tar_remote.py')],stdout=subprocess.PIPE,check=True)
meta=json.loads(out.stdout);C=R/'sync';C.mkdir(exist_ok=True);archive=C/Path(meta['remote_path']).name
subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60:'+meta['remote_path'],str(archive)],check=True)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==meta['sha256']
with tarfile.open(archive) as tar:
 manifest=json.load(tar.extractfile('SYNC_MANIFEST.json'))
 for item in tar.getmembers():
  if item.name=='SYNC_MANIFEST.json':continue
  p=(E/item.name).resolve();assert E.resolve() in p.parents and item.isfile()
  data=tar.extractfile(item).read();assert hashlib.sha256(data).hexdigest()==manifest[item.name]['sha256']
  if '/runs/' in item.name or '/outcomes/' in item.name:
   if p.exists():assert p.read_bytes()==data,'Immutable file changed '+item.name
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
for n,v in manifest.items():assert (E/n).stat().st_size==v['bytes'] and hashlib.sha256((E/n).read_bytes()).hexdigest()==v['sha256'],n
(R/'COLLECTION_RECEIPT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(C/(archive.stem+'.receipt.json')).write_text(json.dumps(meta,indent=2))
print(json.dumps(meta))

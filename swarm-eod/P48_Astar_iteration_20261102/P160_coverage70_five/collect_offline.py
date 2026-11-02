"""Finite Windows byte review and final report; never starts a native game."""
from pathlib import Path
import base64,datetime,hashlib,json,subprocess,tarfile,time,traceback
F=Path(__file__).resolve().parent;C=F
R='/home/junhao/quan/parallel_test_solver/match';RF=R+'/solver_study/framework_screen_20261016/best87_independent_20261025/P160_coverage70_five_20261102';RC=RF
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60']
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,d):
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');t.replace(p)
def upload(p,d):subprocess.run(['scp','-q',str(p),'junhao@10.112.162.60:'+d],check=True)
def metadata():
    code='''from pathlib import Path
import json,base64
p=Path(ROOT)
names=[str(x.relative_to(p)) for x in p.glob('*.json')]+[str(x.relative_to(p)) for x in p.glob('*.txt')]
for q in p.iterdir():
 if q.is_dir() and (q.name in ['J17'] or (q/'RAW_ARCHIVE_RECEIPT.json').exists()):
  names += [str(x.relative_to(p)) for x in q.glob('*.json')]
print(json.dumps({n:base64.b64encode((p/n).read_bytes()).decode() for n in names}))
'''.replace('ROOT',repr(RC))
    bundle=json.loads(subprocess.check_output(ssh+[R+'/.venv/bin/python','-'],input=code.encode(),timeout=45))
    for n,v in bundle.items():
        p=C/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(v))
    return read(C/'STATUS.json') if(C/'STATUS.json').exists() else {'status':'STARTING','completed':[]}
def review(G):
    if(G/'CLIENT_FIRST_RAW_REVIEW.json').exists():return
    receipt=read(G/'RAW_ARCHIVE_RECEIPT.json');manifest=read(G/'RAW_SHA256.json')
    assert sha(G/'RAW_SHA256.json')==receipt['manifest_sha256']
    archive=G/'raw_results.tar.gz';assert not archive.exists(),'Unverified archive already exists: no automatic replacement'
    subprocess.run(['scp','-q','junhao@10.112.162.60:'+RC+'/'+G.name+'/raw_results.tar.gz',str(archive)],check=True)
    assert sha(archive)==receipt['sha256'];seen=set();public=[]
    with tarfile.open(archive,'r:gz') as tar:
        for e in tar:
            assert e.isfile() and e.name in manifest and e.name not in seen and '..' not in Path(e.name).parts
            selected=e.name.endswith(('/round1_public_visual.json','/round1_red_submitted.png','/round1_bombs.json','/summary.json'))
            h=hashlib.sha256();size=0;parts=[]
            with tar.extractfile(e) as f:
                for block in iter(lambda:f.read(1024*1024),b''):
                    h.update(block);size+=len(block)
                    if selected:parts.append(block)
            assert h.hexdigest()==manifest[e.name]['sha256'] and size==manifest[e.name]['bytes']
            if selected:
                p=G/e.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b''.join(parts));public.append(e.name)
            seen.add(e.name)
    assert seen==set(manifest) and len(seen)==receipt['files']
    out={'utc':utc(),'status':'PASS','group':G.name,'archive_sha256':receipt['sha256'],
         'manifest_sha256':receipt['manifest_sha256'],'files_first_verified':len(seen),
         'public_visual_files':public,'NPZ_or_pickle_loaded':False,'private_BLUE_console_read':False}
    p=G/'CLIENT_FIRST_RAW_REVIEW.json';save(p,out);upload(p,RC+'/'+G.name+'/'+p.name)
    print(json.dumps({'first_review':G.name,'files':len(seen)}),flush=True)

def finish_scoped(state):
 G=F/'P159_C70_ASTAR_A';assert read(G/'CLIENT_FIRST_RAW_REVIEW.json')['status']=='PASS'
 matrix=read(G/'RESULT.json');assert matrix['complete']and set(matrix['jobs'])=={'Map01','Map02','Map03','Map04','Map05'}
 result=read(G/'MECHANISM_REVIEW.json')
 out=dict(status='PASS',campaign_status=state['status'],utc=utc(),native_failure=state['first_native_failure'],result=result,
  scope='One requested coverage-guarded corner layout five-map group, no paired causal claim/control rerun/automatic promotion.')
 dest=F/'CAMPAIGN_CLIENT_REVIEW.json';save(dest,out);upload(dest,RC+'/'+dest.name)
 save(F/'LOCAL_COLLECTOR_RESULT.json',dict(status='COMPLETE',utc=utc(),starts_native_games=False))
 print(json.dumps(out),flush=True)

def main():
    started=time.monotonic()
    try:
        while time.monotonic()-started<14*3600:
            state=metadata()
            for name in ['P159_C70_ASTAR_A']:
                group=F/name
                if(group/'RAW_ARCHIVE_RECEIPT.json').exists():review(group)
            if state['status']=='COMPLETE_FINITE_STAGED_CAMPAIGN':
                state=metadata();finish_scoped(state);return
            if state['status'].startswith('STOPPED'):
                save(F/'LOCAL_COLLECTOR_RESULT.json',dict(status='STOPPED_KEEP_FIRST',server_status=state['status'],utc=utc(),starts_native_games=False));return
            time.sleep(3)
        raise TimeoutError('Finite14h collection window exhausted')
    except Exception:
        save(F/'LOCAL_COLLECTOR_RESULT.json',dict(status='FIRST_CLIENT_ERROR_KEEP',utc=utc(),traceback=traceback.format_exc(),starts_native_games=False));raise
if __name__=='__main__':main()

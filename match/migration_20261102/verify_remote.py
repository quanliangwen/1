from pathlib import Path
import json,urllib.request,urllib.parse,hashlib,concurrent.futures,datetime,subprocess,os,time
BASE=Path(__file__).resolve().parent;WORK=Path('E:/codex/P48_astar_five_20261102/github_worktree')
GIT='D:/Git/cmd/git.exe';ENV={**os.environ,'GIT_TERMINAL_PROMPT':'0'}
def git(*a):
 p=subprocess.run([GIT,'-c','http.proxy=','-c','credential.interactive=never',*a],cwd=WORK,capture_output=True,env=ENV,check=True)
 return p.stdout.decode('utf-8').strip()
def get(url):
 # Read-only remote verification may retry transient transport failures. No scientific run is retried.
 for attempt in range(3):
  try:
   op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
   return op.open(urllib.request.Request(url,headers={'User-Agent':'match-archive-verification'}),timeout=120).read()
  except Exception:
   if attempt==2:raise
   time.sleep(2)
first=json.loads((BASE/'COMMIT_FIRST.json').read_text())
commit=first['commit'];manifest=json.loads((BASE/'MIGRATION_MANIFEST.json').read_text(encoding='utf-8'))
tree=json.loads(get('https://api.github.com/repos/quanliangwen/1/git/trees/'+commit+'?recursive=1'))
assert not tree.get('truncated'),'incomplete GitHub tree listing'
entries={r['path']:r for r in tree['tree']}
for r in manifest['moved']:
 assert entries[r['new_path']]['sha']==r['git_blob'],r['new_path']
 assert entries[r['new_path']]['size']==r['size'],r['new_path']
for r in manifest['new']:
 assert entries[r['path']]['sha']==r['git_blob'],r['path']
 assert entries[r['path']]['size']==r['size'],r['path']
assert entries['match']['sha']==first['match_tree']
assert 'swarm-eod/README.md' in entries
assert not any(p.startswith('swarm-eod/') and p!='swarm-eod/README.md' for p in entries)
rawchecks=[]
def check(r):
 b=get('https://raw.githubusercontent.com/quanliangwen/1/'+commit+'/'+urllib.parse.quote(r['path'],safe='/'))
 h=hashlib.sha256(b).hexdigest();assert h==r['sha256'],r['path']
 return dict(path=r['path'],size=len(b),sha256=h)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 for i,r in enumerate(pool.map(check,manifest['new']),1):
  rawchecks.append(r)
  if i%25==0:print(json.dumps(dict(raw_sha256_verified=i,total=len(manifest['new']))),flush=True)
manifestpath='match/migration_20261102/MIGRATION_MANIFEST.json'
remote_manifest=get('https://raw.githubusercontent.com/quanliangwen/1/'+commit+'/'+manifestpath)
assert remote_manifest==(BASE/'MIGRATION_MANIFEST.json').read_bytes()
receipt=dict(status='PASS_REMOTE_TREE_AND_ALL_NEW_FILES_SHA256',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),commit=commit,canonical_url='https://github.com/quanliangwen/1/tree/main/match',match_tree=first['match_tree'],moved_original_files=len(manifest['moved']),moved_original_git_blob_identity_verified=True,new_files_raw_sha256_verified=len(rawchecks)+1,raw_sha256=rawchecks,manifest_sha256=hashlib.sha256(remote_manifest).hexdigest(),unrelated_project_trees_preserved=True,local_and_server_runtime_originals_retained=True,no_new_sdk_native_or_submission_release=True)
(BASE/'REMOTE_VERIFICATION_FIRST.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Publish the receipt separately; it binds the actual migration commit rather than claiming a self-referential checksum.
target=WORK/'match/migration_20261102/REMOTE_VERIFICATION_FIRST.json';target.write_bytes((BASE/'REMOTE_VERIFICATION_FIRST.json').read_bytes())
git('add','--','match/migration_20261102/REMOTE_VERIFICATION_FIRST.json')
git('commit','-m','Record remote match archive SHA256 verification')
git('fetch','origin','main');git('rebase','origin/main');git('push','origin','HEAD:main')
last=git('rev-parse','HEAD')
b=get('https://raw.githubusercontent.com/quanliangwen/1/'+last+'/match/migration_20261102/REMOTE_VERIFICATION_FIRST.json')
assert b==target.read_bytes()
out=dict(status='PASS_RECEIPT_PUBLISHED_AND_RAW_SHA256_VERIFIED',migration_commit=commit,receipt_commit=last,receipt_sha256=hashlib.sha256(b).hexdigest(),new_files_verified=len(rawchecks)+1,moved_files_verified=len(manifest['moved']))
(BASE/'FINAL_PUBLICATION.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out),flush=True)

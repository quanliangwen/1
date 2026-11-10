"""Read-only audit. Emits JSON to stdout; never deletes/moves/writes server files."""
from pathlib import Path
import os, stat, json, subprocess, datetime, re, collections
W=Path('/home/quanliangwen/work')
H=W/'ccmckp_robust_continuous_20261110'
O=Path('/home/quanliangwen/parallel_test/CCMCKP/work')
keep=[W/'cdf_lss_S10_20261109',H/'iterations/S10_LSS_mainflow_APP3_confirmation',
H/'iterations/I002_cdf_neighborhood',H/'formal/F001_I002_40x30',H/'stability/I002_case39',H/'stability/I002_case40',
H/'iterations/I016_cdf_pair_cover',H/'formal/F002_I016_40x30',H/'stability/I016_pair_cover_case39',H/'breadth/I016_priority_four',
H/'research/D004_I016_full_prefix',H/'research/D005_I016_pair_prefix',H/'research/D006_I016_breadth_prefix',
H/'artifact',H/'reference',H/'lss_cache',W/'cdf_lss_aligned_S9_20261109/vendor313']
def du(p):
 r=subprocess.run(['du','-x','-B1','--max-depth=1',str(p)],capture_output=True,text=True)
 return dict(root=str(p),complete=r.returncode==0,errors=r.stderr.splitlines(),rows=[dict(path=line.split('\t',1)[1],allocated_bytes=int(line.split('\t',1)[0])) for line in r.stdout.splitlines()])
groups=[O,W,H]+[H/n for n in ['iterations','research','formal','stability','breadth']]+[O/'rl_balanced_20261101',O/'rl_balanced_20261101/stages',O/'rl_balanced_20261101/stages/U18_FULL40',O/'rl_balanced_20261101/stages/U18_FULL40/results',W/'cdf_lss_aligned_S9_20261109']
sizes=[du(p) for p in groups]
links=[];hardlinks=[];large=[];errors=[];stats=collections.defaultdict(lambda:dict(files=0,allocated_bytes=0,logical_bytes=0))
for root in [W,O]:
 for base,dirs,files in os.walk(root,followlinks=False,onerror=lambda e:errors.append(str(e))):
  for name in dirs+files:
   p=Path(base)/name
   try:
    st=p.lstat()
    if stat.S_ISLNK(st.st_mode):links.append(dict(path=str(p),target=os.readlink(p),resolved=os.path.realpath(p),exists=p.exists()))
    elif stat.S_ISREG(st.st_mode):
     if st.st_nlink>1:hardlinks.append(dict(path=str(p),links=st.st_nlink,dev=st.st_dev,inode=st.st_ino,allocated_bytes=st.st_blocks*512))
     if st.st_size>=20*1024**2:large.append(dict(path=str(p),bytes=st.st_size,allocated_bytes=st.st_blocks*512))
     if str(p).startswith(str(O/'rl_balanced_20261101/stages/U18_FULL40')+'/'):
      k=p.suffix or '[no extension]';s=stats[k];s['files']+=1;s['allocated_bytes']+=st.st_blocks*512;s['logical_bytes']+=st.st_size
   except OSError as e:errors.append(str(e))
refs=[]
for root in keep[:13]:
 if not root.exists():continue
 for p in root.rglob('*'):
  if p.suffix not in ['.py','.sh'] or p.is_symlink() or not p.is_file():continue
  try:
   if p.stat().st_size>2*1024**2:continue
   for n,line in enumerate(p.read_text(errors='replace').splitlines(),1):
    if '/home/' in line or 'vendor313' in line or '../I0' in line:
     refs.append(dict(path=str(p),line=n,text=line[:600]))
  except OSError as e:errors.append(str(e))
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:
  if p.stat().st_uid!=os.getuid():continue
  cmd=p.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');cwd=os.readlink(p/'cwd');opened=[]
  try:
   for fd in (p/'fd').iterdir():
    try:
     target=os.readlink(fd)
     if any(target.startswith(str(x)+'/') for x in [W,O]):opened.append(target)
    except OSError:pass
  except OSError:pass
  if opened or any(str(x) in cwd or str(x) in cmd for x in [W,O]):
   processes.append(dict(pid=int(p.name),cwd=cwd,command=cmd,opened=sorted(set(opened))))
 except OSError:pass
print(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),account=subprocess.check_output(['whoami'],text=True).strip(),host=subprocess.check_output(['hostname'],text=True).strip(),measurement='du allocated bytes, -x, no symlink traversal; snapshot only; no deletion',roots=[str(W),str(O)],keep_roots=[str(x) for x in keep],sizes=sizes,symlinks=links,hardlinks=hardlinks,large_files=sorted(large,key=lambda x:-x['allocated_bytes']),U18_FULL40_extensions=dict(stats),retained_source_path_references=refs,processes=processes,walk_errors=errors),ensure_ascii=False,indent=2))

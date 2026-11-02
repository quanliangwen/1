from pathlib import Path
import subprocess,os,json,hashlib,datetime,urllib.request,urllib.parse,time
BASE=Path(__file__).resolve().parent;STAGE=BASE/'staged'
WORK=Path('E:/codex/P48_astar_five_20261102/github_worktree')
GIT='D:/Git/cmd/git.exe';ENV={**os.environ,'GIT_TERMINAL_PROMPT':'0'}
def git(*args,data=None):
 p=subprocess.run([GIT,'-c','http.proxy=','-c','credential.interactive=never',*args],cwd=WORK,input=data,capture_output=True,env=ENV)
 if p.returncode:raise RuntimeError(p.stderr.decode('utf-8','replace'))
 return p.stdout
def txt(*a):return git(*a).decode('utf-8').strip()
def blob(b):return git('hash-object','-w','--stdin',data=b).decode().strip()
def jsonbytes(obj):return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(dest,b):
 p=STAGE/dest;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)

assert not (BASE/'COMMIT_FIRST.json').exists()
prep=json.loads((BASE/'PREPARATION.json').read_text(encoding='utf-8'))
assert txt('status','--porcelain')=='','working tree must be clean'
git('fetch','origin','main');git('merge','--ff-only','origin/main')
parent=txt('rev-parse','HEAD')
root={}
for line in git('ls-tree','-z',parent).split(b'\0'):
 if not line:continue
 meta,path=line.split(b'\t',1);mode,kind,sha=meta.decode().split();root[path.decode()]=(mode,kind,sha)
assert 'match' not in root,'canonical target already exists: inspect rather than overwrite'
old=txt('rev-parse',parent+':swarm-eod')
records=[]
for line in git('ls-tree','-r','-l','-z',parent,'swarm-eod').split(b'\0'):
 if not line:continue
 meta,p=line.split(b'\t',1);mode,kind,sha,size=meta.decode().split();path=p.decode('utf-8');b=git('cat-file','blob',sha)
 records.append(dict(old_path=path,new_path='match/'+path[len('swarm-eod/'):],git_blob=sha,size=int(size),sha256=hashlib.sha256(b).hexdigest(),mode=mode))

readme='''# 无人机排雷对抗赛 · match

本目录是 `quanliangwen/1` 仓库中本比赛的统一保存入口。2026-11-02由原 `swarm-eod/` 整体迁入，已发布文件保持原始字节；后续结果统一写入 `match/`。

## 快速入口

| 内容 | 位置 | 说明 |
|---|---|---|
| 当前研究与交接 | [迭代入口](P48_Astar_iteration_20261102/LATEST.md) | 最近为P161多角落、每角2–3枚；真实SDK小测仍须看最新状态，非新参赛发布 |
| A*原版五图 | [P48 A*五图资料](P48_Astar_five_20261102/) | 完整均分74.255883，50枚；历史同组记录 |
| 多角落新候选 | [P161](P48_Astar_iteration_20261102/P161_multi_corner_pairs/) | 源码、依据、检查与后续实际结果；研究ZIP不能直接当正式提交包 |
| 正式P48旧发布包 | [V09](submissions/V09/) | 原包逐字节保存，依赖/SDK/整数615等原发布回执随附；不是A*新版本 |
| 原PJ01旧发布包 | [V06](submissions/V06/) | 原包和原回执，不代表官网镜像重新验证 |
| 官方规则、SDK及原始材料 | [reference_materials](reference_materials/) | 原始材料只作参考；原历史环境压缩包不等于可提交算法包 |
| 历史源码、报告和环境恢复 | [archives](archives/) | 分任务压缩保存，每包内含成员SHA256清单 |
| 本次迁移映射与检查 | [migration_20261102](migration_20261102/) | 旧新路径、文件SHA256、排除项及远端检查方法 |

## 如何理解这些文件

- 归档包含原始规则、代码、提交历史、环境恢复锁定依赖和历次实验分析。旧失败提交包、Gurobi研究版也保留在明确标记的历史归档中，**不是当前推荐的比赛包**。J17/Gurobi已经排除参赛。
- 旧自然随机五图观察：P154为76.256070/49枚；P159的70%覆盖组为72.719937/48枚。它们不是同种子稳定因果结论，不能只按单次最高分决定发布。
- 生产算法只能使用本机公共观测和实际收到的消息，不使用真图、蓝队私态、历史评测输入或地图坐标硬编码。NPZ/pickle、蓝队私态日志、许可证、凭据、虚拟环境及可再生缓存不进入新增公开历史快照。
- 本次是**GitHub目录迁移和资料归档**。本地/服务器运行路径和冻结源码不移动、不删除，未新建比赛包、未上传赛事官网、未恢复或并开测试，服务器磁盘空间不会因本次GitHub归档自动释放。
- Git历史中的旧 `swarm-eod/` 提交链接仍有效；主分支旧路径只保留指向本目录的说明，避免两份目录继续分叉。

各归档为迁移时点快照；如正在运行的任务之后产出结果，以迭代入口的新提交为准。此仓库不替代服务器当前活动评测所需依赖；运行端清理必须另查依赖与活动文件。
'''
save('README.md',readme.encode('utf-8'))
save('AGENTS.md',('''# 本比赛资料约定

用户2026-11-02明确指定本仓库 `match/` 为比赛资料统一位置。后续比赛源码、结果、交接和交付均按任务目录保存在此，不再向旧 `swarm-eod/` 新增同名资料。CCMCKP项目保持在根目录CCMCKP/，不得混入或修改。

不得移动/删除当前运行端依赖来配合GitHub整理；保留冻结源码、历史真实失败和完整共同五图。不要将研究ZIP或Gurobi版标成官网可用包。新正式包必须执行SUBMISSION_POLICY并绑定实际ZIP的整数615、依赖ABI、SDK入口和平铺布局。旧包归档不等于重新发布验证。

不上传凭据/完整许可证、虚拟环境、BLUE私态日志或原始NPZ/pickle。归档成员必须保持原字节并提供SHA256清单，远端文件核验后才称已上传。synced sources只读。
''').encode('utf-8'))
save('archives/README.md',('''# 历史归档

按原任务目录保存源码、分析、公开结果、检查回执和必要输入。每个ZIP内 `_ARCHIVE_MANIFEST.json` 给出所有成员的原始相对路径、字节数和SHA256；zip本身的SHA256见迁移清单。

这是资料快照，不是可直接运行的虚拟环境，也不是每个ZIP都可用于赛事提交。正式旧包单列在 `../submissions/`。归档中旧失败包、原J17含Gurobi依赖的历史版本均只用于追溯；不推荐上传官网。研究成绩需参照其完整结果与适用条件。

运行缓存、环境二进制、私态日志、原始NPZ/pickle和凭据被排除。没有批量搬走服务器原始results，本地/服务器原件均保留。

若ZIP被拆为 `.part001`、`.part002` 等，按编号二进制连接后，先核迁移清单中整个ZIP的SHA256再解压；不应将分片直接当ZIP打开。本次是否实际拆分以清单为准。
''').encode('utf-8'))
save('submissions/README.md',('''# 已有正式提交包的原样归档

- V09：P48原版（非A*），原ZIP SHA256 `fcef716d6855e7c5048299048e8ebd8216c777663ed75faf2583155d1648abc9`。
- V06：PJ01原版，原ZIP SHA256 `01c9b9de5caad8f280695852e8e0461a66d26feb689339d5de8047ed3e72008c`。

本次已重新核对这两份归档ZIP的原SHA256，原发布检查回执随包保存；未重跑SDK/比赛/官网检查，不构成新发布保证。当前P161为研究候选，不能使用V09的回执为它放行。旧V01/V03/V04/V05的队号及NumPy失败历史保存在历史归档，不能当兼容性修复版。
''').encode('utf-8'))
status=Path('E:/codex/P48_Astar_iteration_20261102/P161_multi_corner_pairs/STATUS.json')
save('migration_20261102/CURRENT_STATUS_SNAPSHOT.json',jsonbytes(dict(snapshot_utc=utc(),source=str(status),status=json.loads(status.read_text(encoding='utf-8-sig')),note='Migration snapshot only. Existing SDK queue and read-only result watcher retained; no new test started by migration.')))
save('migration_20261102/PREPARATION.json',jsonbytes(prep))
save('migration_20261102/PATH_MAPPING.json',jsonbytes(dict(parent_commit=parent,old_subtree_sha=old,moved_files=records)))
for name in ['prepare_archive.py','finish_archive.py','migrate_git.py','verify_remote.py','PREPARATION_FIRST_ERROR.json']:
 save('migration_20261102/'+name,(BASE/name).read_bytes())
save('migration_20261102/GITHUB_DESTINATION.json',Path('E:/codex/P48_Astar_iteration_20261102/GITHUB_DESTINATION.json').read_bytes())

tree={}
def add(path,mode,sha):
 parts=path.split('/');node=tree
 for p in parts[:-1]:node=node.setdefault(p,{})
 assert parts[-1] not in node,('duplicate',path)
 node[parts[-1]]=(mode,'blob',sha)
for r in records:add(r['new_path'][len('match/'):],r['mode'],r['git_blob'])
new=[]
for p in sorted(STAGE.rglob('*')):
 if not p.is_file():continue
 b=p.read_bytes();path=p.relative_to(STAGE).as_posix()
 assert len(b)<100*1024**2,('GitHub regular blob limit',path)
 sha=blob(b);add(path,'100644',sha)
 new.append(dict(path='match/'+path,size=len(b),sha256=hashlib.sha256(b).hexdigest(),git_blob=sha))
manifest=dict(created_utc=utc(),parent_commit=parent,moved_files=len(records),new_files=len(new),moved_bytes=sum(x['size'] for x in records),new_bytes=sum(x['size'] for x in new),moved=records,new=new,old_directory_redirect='swarm-eod/README.md',preserve_other_root_entries=True,server_and_local_runtime_files_untouched=True)
b=jsonbytes(manifest);add('migration_20261102/MIGRATION_MANIFEST.json','100644',blob(b));(BASE/'MIGRATION_MANIFEST.json').write_bytes(b)
def make_tree(node):
 entries=[]
 for name,value in node.items():
  if isinstance(value,dict):mode,kind,sha='040000','tree',make_tree(value)
  else:mode,kind,sha=value
  entries.append((name,mode,kind,sha))
 data=b''.join(f'{mode} {kind} {sha}\t'.encode()+name.encode('utf-8')+b'\0' for name,mode,kind,sha in sorted(entries,key=lambda x:x[0]+('/' if x[2]=='tree' else '')))
 return git('mktree','-z',data=data).decode().strip()
match=make_tree(tree)
redirect=blob('# 比赛资料已迁移\n\n2026-11-02起统一保存到 [match/](../match/)。已发布文件原字节迁移，旧历史提交链接仍可使用；后续结果只更新新目录。\n'.encode('utf-8'))
redirecttree=git('mktree','-z',data=f'100644 blob {redirect}\tREADME.md\0'.encode()).decode().strip()
newroot=dict(root);newroot['match']=('040000','tree',match);newroot['swarm-eod']=('040000','tree',redirecttree)
payload=b''.join(f'{mode} {kind} {sha}\t'.encode()+name.encode()+b'\0' for name,(mode,kind,sha) in sorted(newroot.items(),key=lambda x:x[0]+('/' if x[1][1]=='tree' else '')))
roottree=git('mktree','-z',data=payload).decode().strip()
commit=git('commit-tree',roottree,'-p',parent,data=b'Organize drone competition files under match and archive source, evidence and releases\n').decode().strip()
# Verify unrelated root entries, including CCMCKP, before changing branch or pushing.
for name,entry in root.items():
 if name!='swarm-eod':assert txt('rev-parse',commit+':'+name)==entry[2],name
git('merge','--ff-only',commit)
git('sparse-checkout','add','match')
assert txt('status','--porcelain')==''
(BASE/'COMMIT_FIRST.json').write_bytes(jsonbytes(dict(commit=commit,parent=parent,match_tree=match,moved=len(records),new=len(new)+1,utc=utc())))
print(json.dumps(dict(status='COMMITTED_LOCAL',commit=commit,moved=len(records),new=len(new)+1,bytes=manifest['new_bytes'])),flush=True)
git('push','origin','HEAD:main')
(BASE/'PUSH_FIRST.json').write_bytes(jsonbytes(dict(commit=commit,utc=utc(),status='PUSHED')))
print(json.dumps(dict(status='PUSHED',commit=commit)),flush=True)

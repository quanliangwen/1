from pathlib import Path
from hashlib import sha256
import json,shutil

ROOT=Path(__file__).resolve().parent
read=lambda n:json.loads((ROOT/n).read_text(encoding='utf8'))
b=read('BUILD.json');a=read('COUNTEREXAMPLES.json');r=read('BUDGET_REGRESSION.json')
assert b['status']==a['status']==r['status']=='PASS'
assert a['source_files']==r['source_files']==b['candidate_files']
assert a['candidate_zip_sha256']==r['candidate_zip_sha256']==b['candidate_zip_sha256']
assert a['total_checks']==95 and r['total_checks']==56
assert all(sha256((ROOT/'candidate'/n).read_bytes()).hexdigest()==h for n,h in b['candidate_files'].items())
assert all(x['full_matches']==x['physics_steps']==x['SDK_rounds']==0 for x in (a,r))
out=ROOT/'delivery';(out/'candidate').mkdir(parents=True,exist_ok=True)
for n in b['candidate_files']:shutil.copyfile(ROOT/'candidate'/n,out/'candidate'/n)
for n in ['BUILD.json','COUNTEREXAMPLES.json','BUDGET_REGRESSION.json','BASELINES_UNCHANGED.json','CHANGES.patch',
          'freeze.py','verify_finish.py','verify_budget_regression.py','counterexamples.log','budget_regression.log',
          'prepare_delivery.py']:
    shutil.copyfile(ROOT/n,out/n)
table='\n'.join(f"| {c['name']} | {c['checks']} | 通过 |" for c in a['categories'])
text=f'''# 93%预算候选：末弹完成、确认交接与正常提前交图

研究候选；V16继续作为比赛基线。仅完成反例验证，没有运行整场比赛、SDK轮次、控制器轨迹回放或物理推进，没有新增地图得分。不作为新的正式比赛提交包或官网兼容放行结果。

## 绑定与范围

- 基线：现有93%预算候选，内部冻结归档SHA256 `{b['baseline_zip_sha256']}`。
- 本候选内部冻结归档SHA256 `{b['candidate_zip_sha256']}`；本目录交付56项完整源码及逐文件校验和，不交付新的team615_red_vNN.zip。
- 仅修改group_exchange.py、placement_preferences.py、red_hooks.py、second_drop_site.py，其余52项逐字节不变。
- 拟合、扫描、导航几何、安全路径检查、原库存单调合并、投放成功确认函数、选图公式、0.003近分规则、竞价、共享6步槽、原93%预算和双时限硬兜底保持。V16及93%基线原件SHA另见BASELINES_UNCHANGED.json。
- 不增加300步低收益判定或5分收益预测。正常返航起点仍是60%。

## 末弹完成出口

仅初始2枚、实际仍剩1枚、首枚已确认、有可靠GPS、离开首枚动作已结束、无待确认投放，且达到60%步数后启用。Map05为4320步、Map06/07为3240步；不是地图或机号特判。

在当前经过的位置复用SecondDropSite.completion_checks：32px机载保守间距（SDK真实中心距离24px底线不变）、现有6px地图取点余量、空地证据、处置中心避让、实时窄口、现有离开通道检查、有效传感器与正新增覆盖（gain>1e-6且支持证据有效）。历史通道归属、密度、拒绝区域、深处留弹及前方更优不再否决此分支；这些旧逻辑本身保留。

选点和实投使用同一复核函数。高速时只对当前点刹停，不安装探索航点，最多30步；漂移超过8px、失去定位、危险或收益消失即退出。实投前仍要求现有速度不超过2.5。继承原投放脉冲及零脉冲间隔；只有原_sync_placement观察到库存下降才能生成第二枚记录，原finish_request随后确认；拒投不伪造成功。

入口在首枚离开和必要逃逸控制之后、旧接近/预约之前。仅合格的末弹分支可以替代旧投放预约；LocalEscape继续执行。_placement_spacing和导航目标筛选原样保留。

## 确认交接与一次原返航重试

原red_inventory已经支持转发，原地图快照也会合并库存；没有另造重复库存协议。接触时读取现有实时库存字段作为对方已持有零确认的回执，保留来源时间，不将接收时间改写为来源时间。旧正数、缺失、超时均不能变零。

本地交接使用原完整payload清单，额外要求本组成员已真实清零，以及另一位实际联系人持有相应数据与零确认；单成员组无需虚构另一位成员。原离开预算仍可结束等待，不能据此标记已交接成功。

本机已空、缺队友确认、原任务ABORT且冷却20步后，最多允许一次原返航预检/执行机会。仍用原目标、原trail、原grid.route和known_segment，保留原ETA/cutoff/安全检查。预检失败也消耗该重试机会；第二次中止不能继续启动。没有增加新目标、信使路线或复杂配送。该项只是给原任务一次机会，不保证中止路线能变得可达。

## 交互完成后提前交图

所有来源均为有效零库存、本机SDK库存为零且无待确认投放，并完成实际双向交接后，锁定early_finish_started。双向交接要求：本机确实持有自己和至少一名实际联系人的快照与图片；对方清单确认也持有相同payload；对方现有实时消息确认掌握全队零记录。不能只凭phase/manifest/“对方说有图”启动；无需额外凑五份地图。

交互完成后最多24步短刷新替代固定180+24探索留时。普通和分组提交均可绕过已完成任务的活动窗口、旧pre_submit_scan等待、额外final_maps等待及provisional_map阻挡。缺实投确认时不放行。

首轮30步让行（适用时）与24步刷新并行，重复广播不重启；共享6步槽仍锚定原绝对时钟，不因各机完成时间不同而各自重起。原竞价、候选摘要/选择租约和至少2帧选择校验继续执行。允许结束时使用原refresh_for_finish和原渲染/拟合方法重新比较已收到的最新证据一次，保留个人原图与旧胜出图。

原硬兜底仍先于预算和正常算法执行，1.5秒最小自适应墙钟预留、剩余4步硬出口、93%起30步预算窗口均未改。

## 反例结果

| 类别 | 检查数 | 结果 |
|---|---:|---|
{table}
| 新测试结束后的全部源码SHA核对 | 1 | 通过 |
| 原93%预算六类回归 | 56 | 通过 |

合计151项。反例夹具证明：

- 60%前、首枚、无GPS、首枚未离开、待确认、真实窄口/出口受阻/处置中心附近、无收益均不能通过新末弹出口；23.99/24/31.99px拒绝、32px通过保守机载间距夹具。
- 运动时不发脉冲，停稳重新复核；30步超时、避让漂移、新炸弹或失去GPS退出；指令后库存不变不登记成功，真实库存下降夹具才生成第二枚记录。
- Map06形式的1928步剩1旧记录被2393步真实零记录替代，来源时间不重写；缺失或未来记录不能放行。
- 一组双向真实交接可在旧3444步门槛前正常交图；低代理分原本会触发provisional_map，完成交接后可放行；重复消息不重启窗口；普通路径同样绕过旧活动窗口。
- 两机夹具中较高竞价的3号先于0号提交，只有一个提交者；0.003近分选新图保留。不是整图多机协调稳定性的实测证明。
- 原硬墙钟、步数、长帧自适应兜底优先以及93%预算56项原回归全部通过。

验证使用现有Linux/Python3.11.17、NumPy1.26.4、OpenCV4.11 SDK环境，只读复用依赖；没有安装或替换依赖。真实导入候选方法，传感器、库存、消息和提交API为可控夹具。完整control的验证使用原方法AST和惰性父类替身，不执行SDK物理控制器。

## 尚不能证明的实战结果

没有新比赛分数。Map05原轨迹存在长时间靠近首枚炸弹的区段，32px或实时通道不合格时仍不能强投；本分支不创造新逃逸路线。Map07末弹能否在93%前投出取决于当时机载复核。Map06一次返航重试仍可能被原安全检查拒绝或联系不到缺确认来源；绝不以超时清零强行结束。这些都需要后续明确授权的整场测试确认，本轮没有启动该测试。

## 复现与边界

freeze.py使用已有baseline_snapshot.zip（上列0ed2归档）进行字节/AST范围检查；verify_finish.py与verify_budget_regression.py需要BUILD.json、candidate/及只读官方SDK src参数。原预算回归还使用既有rowindex_baseline_snapshot.zip作窗口外旧竞价对照（SHA `{sha256((ROOT/'rowindex_baseline_snapshot.zip').read_bytes()).hexdigest()}`）。这两份既有归档只作工作区验证输入，不作为本次新的比赛包发布。发布目录包含最终源码、补丁、校验和、验证脚本和结果；没有官网发布或正式ABI发布检查回执。
'''
(out/'README.md').write_text(text,encoding='utf8',newline='\n')
notes='''# 验证过程中修正的测试基础设施问题

未启动仿真。初次静态冻结脚本误把req.txt当Python编译，随后改为只编译.py；之后修正CRLF与LF导致的文本范围对照定位问题。首次远端传输只包含.py导致缺req.txt/team_info.yml，改为完整冻结归档解包，并在导入后核对全部56项SHA。

新增测试第一轮已通过前六类，完整control夹具缺semantic_values字段而失败；只补齐夹具字段后通过。上述失败不是被略过的算法断言，最终全部测试在同一候选源码哈希下通过。Windows离线收尾读取中文JSON时显式设置UTF-8；远端原始UTF-8日志和JSON均保留。本轮没有因此修改SDK或依赖。
'''
(out/'VALIDATION_NOTES.md').write_text(notes,encoding='utf8',newline='\n')
manifest={p.relative_to(out).as_posix():sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='CHECKSUMS_SHA256.json'}
(out/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(files=len(manifest)+1,new_checks=95,budget_regression_checks=56,total_checks=151,candidate_zip_sha256=b['candidate_zip_sha256'],full_matches=0),indent=2))

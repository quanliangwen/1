# V16 → 已有60%返航研究版：移植说明

本说明按用户确认，“60%”指最大步数的60%开始具备返航资格，不是雷达有效比例改成60%。本轮只读源码、整理差异和历史结果，没有修改任何现有算法，没有运行仿真或目标代码测试。V16继续保留为比赛基线。

## 1. 先确认移植的究竟是哪一版

| 对象 | 冻结归档SHA256 | 定义 |
|---|---|---|
| V16正式比赛基线 | `e98990cfd9269ab521621bc97d7c9e81e21fa83bb83dafbfefb3943480dd6791` | 首轮30步让行版，原本就有60%返航 |
| 本次移植目标：已有60%返航研究版 | `c4b8513084ce114e6aae04b42489c995e73955ec545a64c5f9d999190004a562` | 按行索引＋93%预算出口＋末弹完成、确认交接、交互后提前交图 |
| 最近一次测试的50%＋单次首弹恢复候选 | `6207ff8df49e435dc988119f98c130673da3dc123620ef4d20f39afc170c2a23` | 不属于本次移植目标；Map07第1418步恢复选路失败 |

关键结论：V16与已有60%版都使用：

```python
def start(self):
    return self.limit * 3 // 5
```

5400步地图从3240步开始具备返航资格，7200步地图从4320步开始。原交互任务截止条件也相同：达到85%步数或剩余墙钟不超过8秒即截止；93%预算出口是另一个独立结束窗口。它不是“达到60%就强制5架飞机立刻返航”：本机必须投完且无待确认，集合点及原有安全路线、剩余预算也须通过检查。

若另一份代码只需要60%返航，而其他改动不需要，那么无需整套迁入后文6个文件。若另一份代码就是V16，返航比例已经符合要求。

## 2. 逐字节差异总览

两个归档均为56项文件，没有增加或删除文件；6项变化、50项完全一致。

| 文件 | 真正新增或改变的行为 | 应一起移植的部分 |
|---|---|---|
| `line_regularization.py` | regularized_walls取点使用按行索引 | 可独立移植；不依赖其他5项 |
| `deadline_submission.py` | 新增BudgetSubmission，93%开始的30步预算交图 | 与red_hooks预算字段、竞价及控制入口一起 |
| `second_drop_site.py` | 新增末弹在当前位置完成的统一复核/刹停/请求 | 与placement_preferences包装函数及red_hooks接口、接入一起 |
| `placement_preferences.py` | 新增complete_last包装，先处理真实投放反馈 | 不能单独只加此函数 |
| `group_exchange.py` | 零库存持有回执、一次返航重试、真实交互后提前交图 | 与red_hooks普通提交路径的等待旁路一起 |
| `red_hooks.py` | 连接以上新出口，保留旧硬兜底最高优先级 | 只按差异合并，不能只复制文件尾部几个函数 |

以下均不是新增改动：集合点发现、分组/父集合点、原路返航路线、安全导航、MapCandidates可用候选缓存、个人原图、0.003近分优先新图、6步时间槽、首轮30步让行、原始1.5秒自适应硬兜底。

`drop_departure.py`、`local_escape.py`、`rescue_shared.py`在V16和目标60%版中逐字节相同；不要迁入最近新增的62步/3秒首弹恢复及其90%雷达检查。`bearing_core.py`也没有变化，本目标只包含按行索引优化，不包含另一次bearing优化试验。依赖文件req.txt、队号配置team_info.yml相同，无新增第三方依赖。

## 3. 改动A：按行索引取点

位置：`line_regularization.regularized_walls()`。

V16每条霍夫候选线都对全部墙点执行包围框过滤。目标版利用`np.nonzero(hits >= 2)`按行排列的顺序，一次建立`row_offsets`；每条候选线先裁出可能涉及的行段，再执行原来的四个坐标比较。

必须整体保留：

1. `points`和`weights`的建立顺序，不对点重新排序。
2. `margin = float(fit_band) + 9.`。
3. 行边界向外取整、限制在图像高度范围内，保留原始y比较以剔除扩大的边界点。
4. `subset`加回`row_start`，保持全局取点编号，不能把局部下标直接用于weights。
5. 非有限边界回退到扫描全体点，保持原比较语义。

从`delta = points[subset] - start`开始的沿线/垂线过滤、加权拟合、协方差阈值、百分位端点和绘图公式不变。拟合缓存接口也不变。

这是运算优化，不是新的拟合策略。同一输入应输出相同取点编号、线段和图片；整场仍可能因墙钟相关出口改变而改变结束时机，不能从函数等价直接推出整场得分相同。

## 4. 改动B：93%预算交图出口

### deadline_submission.py

原`DeadlineSubmission`类完整保留，在文件末尾新增`BudgetSubmission`：

- `START_PERCENT = 93`。
- `FRESH_STOCK_STEPS = DeadlineSubmission.BACKUP_INTERVAL`，当前为360步。
- `score`保存本窗口的竞价代理分，`last_gate`只用于去重记录检查原因。
- `window(limit)`返回`ceil(limit * .93)`到起点加29步；不要改成93%的墙钟。
- `stock_status()`区分近期仍有库存与未知库存。
- `peer_ranks()/submit_due()`复用原有竞价时隙算法，只把终止参数换成预算窗口末步，不能移动真正的比赛末尾窗口。

| 最大步数 | 返航/末弹分支起点 | 预算窗口 | 原最后30步窗口 |
|---:|---:|---:|---:|
| 5400 | 3240 | 5022～5051 | 5371～5400 |
| 7200 | 4320 | 6696～6725 | 7171～7200 |

### red_hooks.py

新增导入BudgetSubmission，并在构造函数初始化：

```python
self.budget_submission = BudgetSubmission()
self.budget_submission_event = None
self.budget_submission_audit = []
```

新增三个方法：

- `_budget_submission_candidate()`：只读现成图片，依次使用group_cache、backup_cache、deadline_cache；这是固定缓存优先序，不是现场对所有图片重新评分找最高分。严禁在这条出口加入扫描、融合或拟合。
- `_budget_submission_gate(step)`：本机确认库存为0、传感器库存为0、没有pending_drop；有近期仍有弹的队友则拒绝；还需代理分和非空图片。
- `_try_budget_submission(step)`：记录有变化的拒绝原因，固定本窗口代理分，按既有竞价窗口提交缓存图片，记录提交事件。

`_own_map_bid()`也必须合并预算分支，让其他机收到的ready资格与本机预算出口一致。竞价结构仍是`(step, score, eligible)`。

控制入口的次序必须是：

```text
同步本机真实库存
→ 已提交/硬墙钟或硬步数兜底
→ 93%预算交图
→ 原导航、采集、投放及普通交图
```

**库存语义必须原样说明：**近期360步内的正库存会挡住预算交图；过旧正库存、缺失或非法记录归入unknown。unknown不是“确认已投完”，但不阻止这条有界预算出口。因此它可以在某台失联飞机仍有末弹时结束比赛。不能宣传为“全队10枚一定投完才结束”，也不要把未知记录在inventory_records里改写成0。

该预算策略需要根据移植目标是否允许这种取舍单独决定。只想解决真实确认传递或增加末弹机会，不一定要把预算出口一起带走。

## 5. 改动C：末弹当前位置完成

### second_drop_site.py

构造函数新增：

```python
self.completion_plan = None
self.completion_retry_at = 0
```

新增`completion_checks()`与`complete_last()`。移植时必须成组保留，不能只复制发出place_bomb的末尾几行。

进入条件：

- 已到最大步数60%，初始配额为2，当前确认库存与传感器库存都为1，无待确认投放，并有真实首弹记录。
- `gate()`继续要求首弹脱离模块不在执行、有可靠GPS/姿态、不是仅里程计定位、有探索路线、传感器可用、剩余步数与墙钟足够。
- 只利用当前已到达的位置，不生成新的探索航点，不主动前往墙角或首弹外另一个点。

统一复核：

1. 地图边界与有限传感器/里程计、可靠定位。
2. 当前栅格已知自由；`SITE_CLEARANCE=6`作为本分支的栅格clearance阈值。它不是改写官方无人机几何或允许机身穿墙；实时窄口/退出检查仍在。
3. `_placement_block(..., minimum_spacing=32.)`加现有`_spaced_from_bombs()`；SDK官方24px底线仍由实际布弹器执行。
4. 当前真实窄口、首弹后的退出通道，仍不合格就拒绝。
5. gain>1e-6、原始墙收益>0、三方向证据有限非负且总量>0。

新分支绕过原普通分支的一些质量偏好，如更高墙覆盖门槛、历史通道归属和历史局部拒绝区；不绕过上述实时安全复核。它仍可能因间距或无收益而投不出去。

动作次序：先复核当前位置，再刹停，再在停稳后复核并请求。沿用MAX_STEPS=30、ARRIVAL=8；漂离超过8px或30步到期退出；失败后10步再试，入口按`step % (2*team_size) == 2*identifier`错开请求。不能每次失败重置已启动的30步计时。

### placement_preferences.py

新增包装函数：

```python
def complete_last(self, drone, command, step, ranges, semantic):
    self.finish_request(drone, step)
    return drone.second_drop.complete_last(drone, step, command, ranges, semantic)
```

先finish_request是为了把上一帧真正接受/拒绝的反馈处理完。实际请求仍走原`place()`，写pending_drop，不直接减少库存。真正成功仍由`CoveragePlacementDrone._sync_placement()`观察到库存减少后登记drop_records。

### red_hooks.py

`_placement_block()`新增可选`minimum_spacing=None`参数：未传时保持V16的`max(32., self._placement_spacing(step))`；仅新末弹分支显式传32。不要把全局间距一律改成32。

`control()`在原首弹脱离/快收尾接管之后、旧approach/第二枚预约之前调用`placement.complete_last()`。若接管，仍允许现有local_escape处理后返回。不要把它放到硬交图出口之前。

## 6. 改动D：交互时真实确认交接＋一次返航重试

修改文件为group_exchange.py；消息发送格式继续沿用已有字段，不需要另创一种全局消息。

新增状态：`peer_zero_receipts`、`confirmation_retry_used`、`aborted_step`、`early_finish_started`。

### 零库存持有回执

`receive()`先保留原epoch、发送人及12步新鲜度检查，再从实际收到的`red_inventory`读取0库存来源集合，记录：

```python
peer_zero_receipts[peer] = (local_receive_step, frozenset(zero_origins))
```

这代表“这个对端确实发送了这些零记录”，不是“接近了队友就算收到”。库存来源时间戳仍保持原值，不能转发一次就刷新原记录时间。

新增`_confirmed_empty()`与`_exchange_acked()`。本地组交互完成不再只检查自己持有各机snapshot/image，还要求来源零库存及有效对端的载荷持有回执。单成员本地组有简化分支；全队提前结束的双向确认不能用这个简化分支代替。

在`tick_navigation()`的LOCAL_EXCHANGE阶段，把原`complete(self.group)`改为`_exchange_acked(...)`；原预算到点仍可离开等待，不新增无限期停留。

### 一次返航重试

`release(..., 'ABORT')`记录退出步数。退出返航至少20步、仍缺全队清零确认、还没用过重试时，可再做一次原目标的返航预检。

需要一起合并`prepare_return()`与`commit_return()`的状态判断。通过库存、退出动作、集合点确认及可达根检查之后，进入重试路线预检时即消耗机会；后续安全接入或预算检查失败，也不能每帧重新试。原路线构造、目标、已知自由区检查和ETA公式没有换成新导航算法。

## 7. 改动E：真实交互完成后，提前普通交图

新增`GroupExchange.exchange_finish_ready()`：

- 已到60%；本机库存真实为0、无pending；本地持有全队有效的0记录。
- 已有非空、选好的候选图。
- 与至少一个新鲜对端完成双向载荷持有回执，且对端也发送了全队零库存信息。
- 首次成立记录`early_finish_started`，重复广播不重启。

`can_finish()`新增条件：从该固定起点经过FinalMaps.COLLECTION_STEPS=24步后，库存仍满足，允许提前结束。**24步是收集期，不保证第24步必交**：原6步槽、竞价及适用时的首轮30步让行仍可能继续等待。时间槽继续锚定原绝对finish_floor，不能改成各机各自起表。

必须同时移植两条提交路径：

1. group_exchange里的`ordinary_submit_allowed()`、`yield_first_round()`、`can_finish()`、`try_submit()`。
2. red_hooks.control里的普通全队清零提交分支。

只有`exchange_ready=True`时，才绕过：

- 原返航交互活动期的普通提交阻挡；
- pre_submit_scan的剩余180步扫描等待；
- final_maps的额外收集等待；
- provisional_map的暂缓交图判断。

仍保留全队真实零库存、本机无待确认、非空图、选图、原竞价/让行/时隙和硬兜底。非exchange_ready路径继续走原等待，不能全局删除这些保护。

原有refresh_for_finish、保留旧胜出图与个人原图、最新证据重新比较继续使用；这些函数主体不是本次相对V16新增的改动。

## 8. 向另一份代码移植时的接口前提

| 接口/数据 | 必须满足的含义 |
|---|---|
| inventory_records[owner]=(origin_step,count) | 源时间戳不被转发刷新；有效0来自真实库存；不能直接清掉旧正记录 |
| pending_drop=(before,point,request_step) | 只是请求；只有之后库存下降才成功 |
| drop_records[(owner,ordinal)] | 已确认投放点；不能用预约点冒充 |
| group_best_image=(image,cache,versions) | 已经存在的候选图片及来源；预算出口不现场重新渲染 |
| map_quality/final_maps.rank() | 在线代理分，不是官方地图分；不能把两个概念混用 |
| red_map_bid=(step,score,eligible) | ready资格要与预算和普通出口一致 |
| red_group_exchange.epoch/step/receipts/payload | 真实快照/图片摘要及版本持有证明，不是只广播一个阶段标志 |
| red_inventory | 应先被_receive_team_coordination正常合并，再由GroupExchange.receive记录持有回执 |
| grid/memory/route/local_escape | 沿用目标已有的可靠定位、自由区、实时避障和退出检查；不能用假True占位移植 |

若另一份代码不是V16同族，只复制6个文件很可能破坏这些接口。此时应按功能分组适配，不能假定“只加complete_last就能工作”。特别要检查配额是否仍为2、时间单位是否仍是SDK步数、消息是否支持tuple键/摘要及bool字段。

## 9. 建议移植顺序

1. 确认返航比例确为60%。V16无需修改；若从50%或40%分支来，统一实际prepare_return调用的启动函数，别只改一个未被调用的常量。
2. 单独合并按行索引，比较同输入取点/线段/图片等价。
3. 成组迁入末弹完成的3文件改动，验证拒绝、刹停、请求、库存确认四阶段。
4. 迁入GroupExchange真实回执与一次返航重试，再同步两条普通交图路径的等待旁路。
5. 最后单独决定是否迁入93%预算出口；它是允许未知库存提前结束的取舍，不能当作确认交接的必需依赖。

若目标目录逐文件匹配V16，可以直接用source60_reference中的6个变化文件替换对应文件，得到相同payload；若不匹配，应人工按方法合并。本目录preflight.py只读核对，绝不覆盖文件：

```sh
python preflight.py /path/to/your/solutions
```

文本patch按LF规范化供审阅，原文件字节以MANIFEST.json和source60_reference为准。不要对不匹配的其他版本强行套补丁。

## 10. 已知收益和未修复边界

正式V16发布记录只有Map06/08/09；本次目标60%末弹完成版已有Map05/06/07结果。这里只能给两组历史记录共有的Map06作参考，不是同负载新对照：

| Map06 seed615 | V16发布所绑定历史结果 | 目标60%版历史结果 |
|---|---:|---:|
| 本地得分/80 | 53.913950 | 53.902672 |
| 地图分 | 89.156880 | 87.537202 |
| 采用交图 | 0号5082步 | 0号4678步 |
| 探索率 | 99.374431% | 99.374431% |
| 实投 | 10 | 10 |
| 掉血 | 7 | 4 |
| 最终墙钟 | 178.604001秒 | 178.605011秒 |

即少404步，但仍是墙钟兜底，未省墙钟；本地分约低0.011278，地图分约低1.619678。不能称为相对V16全面升级。

目标60%版Map05/Map07分别为本地59.838796/54.928766，地图95.047382/90.212008，均10枚；这不是V16两图的分差，不能用之前50%版的低分冒充V16成绩。

需保留的边界：

- 交互缓存仍受全员集合点确认与截止条件影响，360步备份冷却与晚接触可能造成旧图提交；本目标没有包含后续Map05缓存修复。
- 不包含一次性首弹恢复。Map07旧60%版2971步成功离开依靠原局部脱困；不能保证每次都能恢复。
- 93%预算可在未知库存时结束；不保证全队10枚。
- 预算/硬兜底仍可能多人同帧提交；Map07旧60%版1/2/3号5039步同帧，SDK采用1号。
- 虽然分组try_submit有choice创建后等2帧的判断，外层普通交图仍可能在它返回False后继续提交。Map05旧60%版5844步提议并同帧提交，是已有日志中的反例；不能宣称全路径具备两帧提交协调。这是移植时应明确保留还是另立修复项的问题，本次没有静默修正。

## 11. 移植后应验证什么

这是后续验证清单，本轮没有执行目标代码测试或仿真：

- 行索引：逐条取点编号、拟合端点、最终图片相同，含非有限边界和空点集。
- 末弹：60%之前不进入；无GPS、无路线、待确认、真窄口、距离小于32px、零收益应拒绝；速度过大先刹停；请求不登记成功，真实库存下降才登记。
- 回执：缺字段/未来时间/错误epoch不放行；消息重发不伪造持有；转发不改来源时间；ABORT后只一次有界重试。
- 提前普通交图：真实双向交互＋全队零后，24步收集能走通两条出口；原30步让行与6步槽不被无意取消，重复广播不重起计时。
- 预算：本机仍有弹/待确认和近期队友正库存必须挡住；过旧正库存仅为unknown，不能改成0；不能把普通全队确认要求整体删掉。
- 双时限：长帧墙钟、剩余4步和已提交状态必须在任何新导航/拟合/投放之前退出。

目录中的METHOD_DIFF.json列出所有变化方法及前后行号，patches/给出逐文件差异，V16_TO_RETURN60.patch给出完整6文件差异。完整参考源码只用于移植与核对，不是新的正式比赛放行包。

# Map09种子615：按行索引与93%预算候选同组8CPU各一次

本轮只新增两场Map09，按行索引候选与93%预算候选各一场。未改算法、依赖或比赛参数，未跑其他地图，V16继续作为比赛提交基线。两版使用相同的稀疏时间锚点观察器和配置，原始源码归档保持冻结。

## 结论

本次结果支持：此前Map09大幅退分主要与运行环境、CPU分配/争用及原墙钟收尾的耦合有关，未见93%预算候选本身产生同等级持续退化的证据。按行索引和预算候选在同一组8CPU下小计分别42.902419、42.926742，只差+0.024323；同一份预算源码相对此前高干扰场次恢复+4.952158分。

这不是严格整机低负载实验：用户在等待后明确改为8CPU空闲即可启动。两场CPU亲和性实际一致，各自开跑前的目标8CPU空闲检查通过；全局背景负载仍存在且不同，未单独隔离CPU数量、频率、缓存和争用各自的贡献，不能给出纯负载因果比例。

两场均由0号机在约178.5秒触发原墙钟兜底，预算事件和审计全部为空，均实投10枚。最终墙钟接近并不表示运行性能相同：高干扰场次仅完成3990步，本轮预算候选完成4944步。两场均有5架同帧提交调用，SDK采用0号图；唯一提交协调未因此解决。V16继续作为比赛基线。

## 在共同物理记录区间内的累计耗时

| 比赛步数 | 此前高干扰预算候选/秒 | 本轮按行索引8CPU/秒 | 本轮预算8CPU/秒 |
|---:|---:|---:|---:|
| 1001 | 36.749822 | 28.053442 | 25.027698 |
| 2001 | 80.099832 | 63.514522 | 59.127982 |
| 3001 | 124.987039 | 98.350026 | 93.634222 |
| 3501 | 154.999697 | 122.007840 | 116.855343 |

三场的五机和炸弹物理记录均可匹配到3503步。预算候选同为3501步时，累计少用38.144353秒，且算法归档与高干扰场次相同。此前在3503步便已用155.034秒，触发原剩余25秒收尾；本轮两版分别到4341、4444步才进入对应收尾，末弹位置随之改变。新预算规则没有参与这些差异。

本轮最后一枚实投分别在4343、4446步，前9次实际投放完全相同；两版0号均采用4590版缓存，但最终图像不同。该差异与原墙钟流程和后续地图证据/制图过程的变化同时出现，不应将小计0.024323分差包装为预算策略的稳定收益。Map09在超过5022步时的新预算出口表现，本轮仍未实际覆盖。

## 本轮结果及此前高负载参考

| 指标 | 本轮按行索引 | 本轮93%预算 | 此前高负载93%预算 |
|---|---:|---:|---:|
| 交图者 | 0 | 0 | 0 |
| 交图步数 | 4848 | 4944 | 3990 |
| 得分小计/80 | 42.902419 | 42.926742 | 37.974583 |
| 地图分 | 66.030348 | 67.085366 | 55.315074 |
| 墙覆盖分 | 42.134636 | 40.888547 | 32.934439 |
| 时间分 | 14.603175 | 12.063492 | 37.301587 |
| 实投数 | 10 | 10 | 10 |
| 最终墙钟/秒 | 178.595214 | 178.600203 | 178.611344 |
| 探索率/% | 92.022125 | 92.022125 | 91.140944 |
| 掉血 | 5 | 4 | 5 |

得分小计=0.5×地图分＋0.2×墙覆盖分＋0.1×时间分。未将未输出的炸弹项冒称为完整总分。

## 8CPU配置及负载记录

用户后续明确要求直接启动，以8个CPU是否空闲为主，取消整机低负载门槛。首场从同一socket的8个不同空闲物理核各选择1个逻辑CPU，合计恰好8CPU；两场固定同组，线程设置相同。初次选核时检查SMT兄弟，之后同组8个指定CPU按每2秒采样、3次均≤5%占用后启动。整机及兄弟线程负载仍记录，CPU亲和性不构成独占预约。共享评测锁继续遵守，不影响别的评测，不自动重跑。此前严格等待队列未启动任何比赛，停止的只有等待进程；变更凭据见USER_8CPU_OVERRIDE.json。

同组逻辑CPU：`[111, 112, 115, 116, 119, 121, 125, 126]`。

| 监控项 | 按行索引 | 93%预算 | 高负载参考 |
|---|---:|---:|---:|
| 整机CPU占用均值/% | 39.629548 | 36.673064 | 54.536198 |
| load1均值 | 122.078919 | 104.683730 | 180.336702 |
| CPU池其他任务估计等效核均值（含兄弟线程） | 2.480284 | 2.617412 | 15.705854 |

全阶段运行监控（含初始化和导出）超出旧整机参考线的样本：`{"rowindex": 185, "budget93": 185}`。旧参考线为CPU≤15%、load1≤32，现仅用于描述，已不作为通过/失败门槛。分段统计按SDK/主机时钟锚点把一秒资源采样归类，边界附近为近似。本轮监控8物理核及其兄弟线程，历史高负载参考监控16物理核；池内等效核均值不能当作同大小池直接比较。

## 分段耗时与负载

| 版本 | 起步 | 止步 | SDK控制入口累计秒差 | 主机秒差 | CPU均值/% | load1均值 | 超出旧参考线样本 |
|---|---:|---:|---:|---:|---:|---:|---:|
| rowindex | 1001 | 2001 | 35.441385 | 35.441334 | 40.377186540394845 | 124.44777777777777 | 36 |
| rowindex | 2001 | 3001 | 34.849456 | 34.850142 | 40.03488399439406 | 124.64558823529411 | 34 |
| rowindex | 3001 | 4001 | 43.397590 | 43.398191 | 38.98571141739573 | 119.67704545454545 | 44 |
| rowindex | 4001 | 4340 | 16.212021 | 16.210928 | 38.50728006913462 | 121.405 | 16 |
| rowindex | 4340 | 4501 | 7.071973 | 7.072526 | 38.183178346633376 | 120.36857142857143 | 7 |
| rowindex | 4501 | 4590 | 3.440131 | 3.439441 | 37.69668936197381 | 118.42 | 3 |
| budget93 | 1001 | 2001 | 34.078805 | 34.079025 | 36.93847521237158 | 105.62058823529412 | 34 |
| budget93 | 2001 | 3001 | 34.519035 | 34.519401 | 36.61936719209877 | 101.9557142857143 | 35 |
| budget93 | 3001 | 4001 | 43.276973 | 43.276878 | 36.522213047485735 | 103.39488372093024 | 43 |
| budget93 | 4001 | 4340 | 15.754405 | 15.754525 | 36.4021328196713 | 105.39933333333333 | 15 |
| budget93 | 4340 | 4501 | 7.788055 | 7.788324 | 36.17903985790458 | 103.89 | 8 |
| budget93 | 4501 | 4590 | 3.380402 | 3.380014 | 36.16462028022899 | 103.2325 | 4 |

## 同工作量对照与结束路径

物理记录、已识别制图安排及末弹审计同时匹配至4340步：按行索引用时157.967177秒，预算候选152.669503秒，实测差5.297674秒。更晚区间可能已涉及不同决策，不能继续当作相同工作量的纯计算比较。
同一步数记录末尾耗时：`{"1001": {"rowindex_seconds": 28.053442001342773, "candidate_seconds": 25.027697801589966, "candidate_saved_seconds": 3.0257441997528076, "within_same_physical_prefix": true}, "2001": {"rowindex_seconds": 63.5145218372345, "candidate_seconds": 59.12798190116882, "candidate_saved_seconds": 4.386539936065674, "within_same_physical_prefix": true}, "3001": {"rowindex_seconds": 98.35002613067627, "candidate_seconds": 93.63422226905823, "candidate_saved_seconds": 4.715803861618042, "within_same_physical_prefix": true}, "3240": {"rowindex_seconds": 109.12415313720703, "candidate_seconds": 103.63898611068726, "candidate_saved_seconds": 5.485167026519775, "within_same_physical_prefix": true}, "3444": {"rowindex_seconds": 119.81016492843628, "candidate_seconds": 114.41763973236084, "candidate_saved_seconds": 5.3925251960754395, "within_same_physical_prefix": true}, "3501": {"rowindex_seconds": 122.00783967971802, "candidate_seconds": 116.85534334182739, "candidate_saved_seconds": 5.152496337890625, "within_same_physical_prefix": true}, "4001": {"rowindex_seconds": 141.76255583763123, "candidate_seconds": 136.9227921962738, "candidate_saved_seconds": 4.839763641357422, "within_same_physical_prefix": true}, "4343": {"rowindex_seconds": 158.05793476104736, "candidate_seconds": 152.74410605430603, "candidate_saved_seconds": 5.313828706741333, "within_same_physical_prefix": true}, "4501": {"rowindex_seconds": 165.02573895454407, "candidate_seconds": 160.45000195503235, "candidate_saved_seconds": 4.575736999511719, "within_same_physical_prefix": false}, "4590": {"rowindex_seconds": 169.43149185180664, "candidate_seconds": 164.75887441635132, "candidate_saved_seconds": 4.672617435455322, "within_same_physical_prefix": false}, "4848": {"rowindex_seconds": 178.51797032356262, "candidate_seconds": 174.728342294693, "candidate_saved_seconds": 3.789628028869629, "within_same_physical_prefix": false}, "4342": {"rowindex_seconds": 158.02731490135193, "candidate_seconds": 152.72205233573914, "candidate_saved_seconds": 5.305262565612793, "within_same_physical_prefix": true, "within_same_drone_and_bomb_prefix": true}, "4340": {"rowindex_seconds": 157.96717739105225, "budget_seconds": 152.6695032119751, "budget_saved_seconds": 5.297674179077148, "within_matching_physics_render_closeout": true}}`。

末弹收尾审计：`{"rowindex": {"0": [], "1": [[4341, "stall_enter", [-272.1413872319977, 268.3581467875526]], [4341, "direction_picked", 1.6867, 36.07, 0], [4342, "separation_open", 733.03], [4343, "pulse_sent", [-274.1798221504944, 268.07089105436467]], [4344, "drop_confirmed", 0]], "2": [], "3": [], "4": []}, "budget93": {"0": [], "1": [[4444, "stall_enter", [-132.77483327734348, 280.9767164452561]], [4444, "direction_picked", 1.4972, 43.13, 0], [4445, "separation_open", 742.46], [4446, "pulse_sent", [-134.84729990870002, 281.06011205362546]], [4447, "drop_confirmed", 0]], "2": [], "3": [], "4": []}}`。

实际投放事件：`{"rowindex": [{"drone": 0, "step": 1230, "event": "sdk_placement", "accepted": true, "physical_xy": [239.89115390460066, 73.86635924699272]}, {"drone": 2, "step": 1434, "event": "sdk_placement", "accepted": true, "physical_xy": [360.04064085137003, -347.7957589645059]}, {"drone": 4, "step": 1548, "event": "sdk_placement", "accepted": true, "physical_xy": [477.65441487370197, -423.2778235243954]}, {"drone": 1, "step": 1732, "event": "sdk_placement", "accepted": true, "physical_xy": [-194.00496872313937, -460.6640921991087]}, {"drone": 3, "step": 1911, "event": "sdk_placement", "accepted": true, "physical_xy": [397.9115976550885, 264.25414839006964]}, {"drone": 4, "step": 1912, "event": "sdk_placement", "accepted": true, "physical_xy": [523.3873405246047, -409.4783528570513]}, {"drone": 0, "step": 2028, "event": "sdk_placement", "accepted": true, "physical_xy": [268.6496386240605, 39.12458434597419]}, {"drone": 2, "step": 2030, "event": "sdk_placement", "accepted": true, "physical_xy": [-168.9070104971254, -129.3399260986701]}, {"drone": 3, "step": 3276, "event": "sdk_placement", "accepted": true, "physical_xy": [-715.4723141210321, -480.89137790894694]}, {"drone": 1, "step": 4343, "event": "sdk_placement", "accepted": true, "physical_xy": [-276.74785070327226, 273.18018949968064]}], "budget93": [{"drone": 0, "step": 1230, "event": "sdk_placement", "accepted": true, "physical_xy": [239.89115390460066, 73.86635924699272]}, {"drone": 2, "step": 1434, "event": "sdk_placement", "accepted": true, "physical_xy": [360.04064085137003, -347.7957589645059]}, {"drone": 4, "step": 1548, "event": "sdk_placement", "accepted": true, "physical_xy": [477.65441487370197, -423.2778235243954]}, {"drone": 1, "step": 1732, "event": "sdk_placement", "accepted": true, "physical_xy": [-194.00496872313937, -460.6640921991087]}, {"drone": 3, "step": 1911, "event": "sdk_placement", "accepted": true, "physical_xy": [397.9115976550885, 264.25414839006964]}, {"drone": 4, "step": 1912, "event": "sdk_placement", "accepted": true, "physical_xy": [523.3873405246047, -409.4783528570513]}, {"drone": 0, "step": 2028, "event": "sdk_placement", "accepted": true, "physical_xy": [268.6496386240605, 39.12458434597419]}, {"drone": 2, "step": 2030, "event": "sdk_placement", "accepted": true, "physical_xy": [-168.9070104971254, -129.3399260986701]}, {"drone": 3, "step": 3276, "event": "sdk_placement", "accepted": true, "physical_xy": [-715.4723141210321, -480.89137790894694]}, {"drone": 1, "step": 4446, "event": "sdk_placement", "accepted": true, "physical_xy": [-127.84902948974629, 276.5330030886988]}]}`。

rowindex预算出口：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；预算门槛审计：`{"0": [], "1": [], "2": [], "3": [], "4": []}`。
硬兜底：`{"0": {"step": 4848, "fallback": "walltime", "remaining_steps": 552, "remaining_walltime": 1.4940850734710693, "local_inventory": 0, "team_confirmed": false, "backup_step": 4590}, "1": {"step": 4848, "fallback": "walltime", "remaining_steps": 552, "remaining_walltime": 1.4940850734710693, "local_inventory": 0, "team_confirmed": false, "backup_step": 4726}, "2": {"step": 4848, "fallback": "walltime", "remaining_steps": 552, "remaining_walltime": 1.4940850734710693, "local_inventory": 0, "team_confirmed": false, "backup_step": 4592}, "3": {"step": 4848, "fallback": "walltime", "remaining_steps": 552, "remaining_walltime": 1.4940850734710693, "local_inventory": 0, "team_confirmed": false, "backup_step": 4728}, "4": {"step": 4848, "fallback": "walltime", "remaining_steps": 552, "remaining_walltime": 1.4940850734710693, "local_inventory": 0, "team_confirmed": false, "backup_step": 4549}}`；最终缓存：`{"owner": 5, "version": 4590, "digest": "87388a174eec6a7a700f9e422751c1141d84ced67d1a5d18970ae82dcd8e1b8b", "precision": 0.907753184122666, "recall": 0.975934065934066, "score": 0.9406097066471591}`；提交调用：`[{"drone": 0, "step": 4848, "walltime_seconds": 178.50591492652893, "image_sha256": "082dc9e2f5f479fdb343c7da0feea0b9f3dea2f56c26d22d155e769efea17807"}, {"drone": 1, "step": 4848, "walltime_seconds": 178.50591492652893, "image_sha256": "21560e6ae94d897eb08bc8a425fcd748a8db7f31b7272b144fa5f2e25f1ac8fd"}, {"drone": 2, "step": 4848, "walltime_seconds": 178.50591492652893, "image_sha256": "0545f1d1449264561dba5cb028d4411d6ef13cc4494c6f33bcd6d1b22f196ae3"}, {"drone": 3, "step": 4848, "walltime_seconds": 178.50591492652893, "image_sha256": "2c8763df02cb5cb70056352809f8493e4a9fdef7b6e1bcc6a212312f8f22295d"}, {"drone": 4, "step": 4848, "walltime_seconds": 178.50591492652893, "image_sha256": "5f3e2b454ac6a28bb1bd54ac0efcf1ee39a76bc1616829aabff022b9d5eac833"}]`。

budget93预算出口：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；预算门槛审计：`{"0": [], "1": [], "2": [], "3": [], "4": []}`。
硬兜底：`{"0": {"step": 4944, "fallback": "walltime", "remaining_steps": 456, "remaining_walltime": 1.4927136898040771, "local_inventory": 0, "team_confirmed": false, "backup_step": 4590}, "1": {"step": 4944, "fallback": "walltime", "remaining_steps": 456, "remaining_walltime": 1.4927136898040771, "local_inventory": 0, "team_confirmed": false, "backup_step": 4816}, "2": {"step": 4944, "fallback": "walltime", "remaining_steps": 456, "remaining_walltime": 1.4927136898040771, "local_inventory": 0, "team_confirmed": false, "backup_step": 4592}, "3": {"step": 4944, "fallback": "walltime", "remaining_steps": 456, "remaining_walltime": 1.4927136898040771, "local_inventory": 0, "team_confirmed": false, "backup_step": 4728}, "4": {"step": 4944, "fallback": "walltime", "remaining_steps": 456, "remaining_walltime": 1.4927136898040771, "local_inventory": 0, "team_confirmed": false, "backup_step": 4909}}`；最终缓存：`{"owner": 5, "version": 4590, "digest": "e79d48bc810d2b53728b40a9f6a3865929f41d63635c374be6ccdf99e4d32e5e", "precision": 0.9077853572316275, "recall": 0.968761572813419, "score": 0.937282789327941}`；提交调用：`[{"drone": 0, "step": 4944, "walltime_seconds": 178.50728631019592, "image_sha256": "114ce13e83e1d2f7a3cfd5910320cc7a1dcbbe08118b3353e5ab693405406514"}, {"drone": 1, "step": 4944, "walltime_seconds": 178.50728631019592, "image_sha256": "b07e855026965dd2b664349be544674f0517315a86a8e32baa2582e20485583c"}, {"drone": 2, "step": 4944, "walltime_seconds": 178.50728631019592, "image_sha256": "43ef89b56fc0982688cabb19146ed797aa03d21d16b93b1dd8b15dd9064f2f77"}, {"drone": 3, "step": 4944, "walltime_seconds": 178.50728631019592, "image_sha256": "dd57079b14226603d0999154bfbc741b640fb08922cf31b7271e0c08091399cb"}, {"drone": 4, "step": 4944, "walltime_seconds": 178.50728631019592, "image_sha256": "4b0849d432830ae9679a8e0e857a11fe2a54f8b5ef1ce30032a6b22b818a6ac2"}]`。

## 相对高负载场次的恢复

差值：`{"rowindex": {"score_out_of_80": 4.927835204163642, "map_score": 10.715273900965855, "wall_score": 9.20019761760993, "submission_step": 858, "placed": 0, "final_walltime_seconds": -0.016129732131958008}, "budget93": {"score_out_of_80": 4.952158284931798, "map_score": 11.770292097693428, "wall_score": 7.954108799473019, "submission_step": 954, "placed": 0, "final_walltime_seconds": -0.011141061782836914}}`。

在共同无人机和炸弹物理记录区间内的同一步数耗时：`{"rowindex": {"last_same_drone_and_bomb_step": 3503, "same_step_times": {"1001": {"heavy_seconds": 36.74982166290283, "this_run_seconds": 28.053442001342773, "observed_saved_seconds": 8.696379661560059}, "2001": {"heavy_seconds": 80.09983229637146, "this_run_seconds": 63.5145218372345, "observed_saved_seconds": 16.585310459136963}, "3001": {"heavy_seconds": 124.98703932762146, "this_run_seconds": 98.35002613067627, "observed_saved_seconds": 26.63701319694519}, "3501": {"heavy_seconds": 154.99969673156738, "this_run_seconds": 122.00783967971802, "observed_saved_seconds": 32.991857051849365}, "3503": {"heavy_seconds": 155.06619024276733, "this_run_seconds": 122.05175757408142, "observed_saved_seconds": 33.01443266868591}}}, "budget93": {"last_same_drone_and_bomb_step": 3503, "same_step_times": {"1001": {"heavy_seconds": 36.74982166290283, "this_run_seconds": 25.027697801589966, "observed_saved_seconds": 11.722123861312866}, "2001": {"heavy_seconds": 80.09983229637146, "this_run_seconds": 59.12798190116882, "observed_saved_seconds": 20.971850395202637}, "3001": {"heavy_seconds": 124.98703932762146, "this_run_seconds": 93.63422226905823, "observed_saved_seconds": 31.352817058563232}, "3501": {"heavy_seconds": 154.99969673156738, "this_run_seconds": 116.85534334182739, "observed_saved_seconds": 38.14435338973999}, "3503": {"heavy_seconds": 155.06619024276733, "this_run_seconds": 116.90610074996948, "observed_saved_seconds": 38.16008949279785}}}}`。

本轮只有一组配对，仍需结合全程负载、末弹落点、最终缓存及得分解释环境影响，不能凭单个分数保证其他种子或负载下完全无差异。本轮已按用户要求改为同组8CPU、带全局负载记录的对照，不能称全程整机低负载或复刻官网具体硬件。正式比赛基线仍为V16。

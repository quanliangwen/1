# 50%返航最后一轮：Map05、Map06、Map07种子615，与40%/60%对照

只新跑50%候选，每图一场、共三场红队。40%和60%均引用既有记录，未重跑；没有运行其他地图。测试期间未再修改算法、SDK、导航、拟合、投放、依赖。V16继续作为比赛基线。

相对40%源码只把GroupExchange.return_start从limit*2//5改为limit//2，其他55项文件和其他方法保持不变。50%门槛：Map05=3600步，Map06/07=2700步；末弹完成和普通交图共享门槛仍60%，原安全、实投确认、协调、93%预算和1.5秒墙钟硬兜底均保持。携弹或路线不安全时不会强行返航。

50%冻结归档SHA256 `e69ea77adb25b9ecbb8bd3a38f34f2241c35ad788c147aff67bc6d83e7c227e8`，源代码在candidate/，它是研究候选，不是新正式比赛提交包；43+95+56=194项反例通过不等于实战稳定提升。三场输入及运行时56项源码前后核对通过，V16原件哈希未变。

官方封存SDK6557940dc18549ffc7a945db887da5b05b7ed2f1；Map05=7200步/240秒，Map06/07=5400步/180秒；5机、每机2枚。各图种子、出生点/朝向、实际区域、墙几何和评分配置均与40%/60%记录核对一致。实际无GPS/禁通信区域：Map05/07为0/0，Map06为0/1。

## 主要结果

| 地图 | 返航门槛 | SDK采用者/步数 | 得分小计/80 | 地图分 | 墙覆盖分 | 探索率/% | 实投 | 掉血 | 最终墙钟/秒 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Map05 | 40% | 0 / 5385 | 61.7560 | 96.3008 | 50.0222 | 100.0000 | 10/10 | 17 | 238.6529 |
| Map05 | 50% | 0 / 5405 | 36.2480 | 46.6198 | 46.8833 | 100.0000 | 10/10 | 9 | 238.6671 |
| Map05 | 60% | 0 / 5844 | 59.8388 | 95.0474 | 48.1231 | 100.0000 | 10/10 | 7 | 230.4730 |
| Map06 | 40% | 3 / 3972 | 51.7078 | 80.0646 | 39.4887 | 99.3744 | 10/10 | 5 | 177.8811 |
| Map06 | 50% | 0 / 4840 | 48.3295 | 77.3753 | 40.8021 | 99.3744 | 10/10 | 2 | 178.6464 |
| Map06 | 60% | 0 / 4678 | 53.9027 | 87.5372 | 41.1201 | 99.3744 | 10/10 | 4 | 178.6050 |
| Map07 | 40% | 0 / 4561 | 31.8949 | 45.2315 | 35.2979 | 98.3632 | 10/10 | 4 | 178.6376 |
| Map07 | 50% | 0 / 5040 | 32.1649 | 44.9092 | 43.7894 | 76.4587 | 9/10 | 2 | 144.6210 |
| Map07 | 60% | 1 / 5039 | 54.9288 | 90.2120 | 44.3387 | 99.9429 | 10/10 | 4 | 158.5508 |

得分小计沿用历史口径，核对官方0.5×地图分＋0.2×墙覆盖分＋0.1×时间分；不冒称完整100分。时间配置按步数计算，步数较少不等于墙钟更短；SDK采用者也不等于唯一提交调用者。

## 本轮结论

50%不是40%与60%之间更好的折中。本次Map05和Map06均低于另外两版，Map07仍严重退分并新增漏投末弹。建议停止用全队统一返航比例作为当前的主要改进方向；不替换V16。本轮不再修改算法或扩展地图测试。

### 三版得分小计/80

| 地图 | 40% | 50% | 60% | 50%相对60% |
|---|---:|---:|---:|---:|
| Map05 | 61.7560 | 36.2480 | 59.8388 | -23.5907 |
| Map06 | 51.7078 | 48.3295 | 53.9027 | -5.5731 |
| Map07 | 31.8949 | 32.1649 | 54.9288 | -22.7639 |

### Map05：探索100%，但最终提交图严重不完整

- 1/2/3号首次接管返航为3600/3600/3643步，比60%版4365/4332/4320提前。0号仍未接管，4号5073步才接管。
- 0号末弹5015实投、5016确认；4号4984/4985，均来自原墙钟收尾；1/2/3号末弹2112/2113、3314/3315、3007/3008。
- 没有任何飞机收齐全队清零确认，正常提前交图入口未启动。0号仍保留4号4740步剩1的记录，最终5405步五机同帧硬兜底，SDK采用0号。
- 0号结束时group_best_metadata=None，分组候选清单为空；实际提交图地图分46.6198，而60%版95.0474、40%版96.3008。可确认“全队探索完成”不代表最终提交机持有合格的全队图；本轮没有对其他未采用图逐张计算官方分，不能虚构其真实得分。
- 探索率三版均100%；50%墙覆盖46.8833、掉血9、墙钟238.667秒。比60%多8.194秒，没有形成实际加速。

### Map06：返航提前，确认仍没闭合

- 0/1/2/4号在2700/2700/2702/2700步接管返航；3号未接管。末弹3号3617实投、3618确认，比60%晚371步，比40%早47步；其余各机末弹步数与60%一致。
- 10枚投完，但没有任何飞机收齐全队清零，early_finish_started均为空。0号仍持有1号1928步剩1、3号3032步剩1的旧记录；最终4840步五机硬兜底，SDK采用0号。
- 地图分77.3753，低于40%80.0646、60%87.5372；得分48.3295，低于40%51.7078、60%53.9027。探索率均99.3744%，墙钟178.646秒基本仍耗到硬兜底，掉血2。

### Map07：4号未离开首弹，9枚就预算结束

- 0/1/2/3号都在2700步接管返航；4号一直携弹，未返航。
- 前9枚投放步数与60%一致，4号仅1355步投出首枚、1356确认，第二枚始终未实投。40%与60%版则都在3250/3251完成4号末弹。
- 新末弹完成分支对4号累计180次spacing拒绝。既有轨迹离线核对表明：3240到5040步，4号真实中心与首枚炸弹中心的距离约3.644—10.108px；不是只差我们保留的32px余量，连官方24px底线也未满足，不能靠强投解决。核对使用已有录像，不执行控制器或物理步。
- 0号仍持有4号1915步剩1的旧记录，本地预算判断把它列为过期未知；此时4号真实仍剩1枚。0/1/2/3号在5040步同帧预算提交，SDK采用0号。提交墙钟144.525秒，距离180秒上限仍35秒，尚未进入原25秒墙钟末弹收尾，比赛便已结束。
- 探索率76.4587%，相比60%99.9429%少23.4842个百分点、相比40%98.3632%少21.9045个百分点。这里确有显著少探索，不能沿用Map05“探索100%但提交图差”的单一解释。
- 实际采用图地图分44.9092，得分32.1649。虽比40%小计略高0.2700，但漏了一枚且探索率大降，不构成更优结果。50%墙覆盖43.7894，掉血2，最终墙钟144.621秒；不能把带着未完成任务的预算结束当作成功加速。

### 可确认与不能确认的边界

- 三图50%均没有启动交互完成后的正常提前出口。Map05/06靠硬兜底，Map07靠允许过期剩弹信息未知的93%预算出口；旧确认和真实携弹必须区分，不能为了放行改成零。
- 已确认的回归涉及实际返航/接触时机、地图缓存或最终采用图、投弹位置或末弹完成以及真实探索范围；不是参数只改变了一个时间戳。
- 未改导航、拟合、投放或兜底公式；源码仅return_start一行变化。为何50%轨迹下4号卡在首弹附近需要另做日志源码诊断，本轮不猜测唯一根因。
- 三版是不同历史时段的单种子单次记录，8CPU分配口径相同但背景负载与SMT干扰不同。墙钟差不能全部算成算法计算差；地图分、实投、探索范围与采用图的上述事实也不能全推给环境。


## 首次实际返航任务接管

取原group_audit的return_owned事件；不是比例门槛本身，也不是到达交互点。—表示没有接管；完整任务/重试、预检、中止和到达见RESULTS.json。

| 地图 | 门槛 | 0号 | 1号 | 2号 | 3号 | 4号 |
|---|---|---:|---:|---:|---:|---:|
| Map05 | 40% | — | 3049 | 3375 | 3009 | 5079 |
| Map05 | 50% | — | 3600 | 3600 | 3643 | 5073 |
| Map05 | 60% | — | 4365 | 4332 | 4320 | 5229 |
| Map06 | 40% | 2408 | 2393 | 2167 | — | 2200 |
| Map06 | 50% | 2700 | 2700 | 2702 | — | 2700 |
| Map06 | 60% | 3242 | 3299 | 3324 | 3247 | 3255 |
| Map07 | 40% | 2160 | 2518 | 2160 | 2160 | 3251 |
| Map07 | 50% | 2700 | 2700 | 2700 | 2700 | — |
| Map07 | 60% | 3240 | 3240 | 3240 | 3240 | 3251 |

## 第二枚实投/库存确认步数

| 地图 | 门槛 | 0号 | 1号 | 2号 | 3号 | 4号 |
|---|---|---|---|---|---|---|
| Map05 | 40% | 5038/5039 | 2112/2113 | 3374/3375 | 3007/3008 | 5066/5067 |
| Map05 | 50% | 5015/5016 | 2112/2113 | 3314/3315 | 3007/3008 | 4984/4985 |
| Map05 | 60% | 5660/5661 | 2112/2113 | 3314/3315 | 3007/3008 | 5228/5229 |
| Map06 | 40% | 2080/2081 | 2392/2393 | 1414/1415 | 3664/3665 | 2020/2021 |
| Map06 | 50% | 2080/2081 | 2392/2393 | 1414/1415 | 3617/3618 | 2020/2021 |
| Map06 | 60% | 2080/2081 | 2392/2393 | 1414/1415 | 3246/3247 | 2020/2021 |
| Map07 | 40% | 1640/1641 | 2517/2518 | 2054/2055 | 2146/2147 | 3250/3251 |
| Map07 | 50% | 1640/1641 | 2382/2383 | 2054/2055 | 2146/2147 | 未投完，剩1 |
| Map07 | 60% | 1640/1641 | 2382/2383 | 2054/2055 | 2146/2147 | 3250/3251 |

实投来自SDK返回成功，库存下降才确认；不能将发指令当实投。各次实投中心、请求分支及对应墙钟时间已保存。

## 确认缺口与实际终局

### Map05
40%：路径 `hard_fallback`；全部提交 `[{"drone": 0, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "8e16c64b0b3b9520d5d94cbb3bbb8823f6982537bdf1f2364dc69ccb09c1688e"}, {"drone": 1, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "e2e4cb2b245678e04076823e2208c213117de1eebfeee4eecc1a70aa55e3679e"}, {"drone": 2, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "74a19cf90558b7fb562a8fe7d9bc2ff1cfadfc5b45b0ea2e515581e29af81845"}, {"drone": 3, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "6ae995c854393c8e1cc2e38a75873904ed2175f11342eb9b4f866fb8c3498740"}, {"drone": 4, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "a54ca3151dec91adfa848fd35885e7dd4787bc057ec0033faaa2e20a00317fe3"}]`。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的记录：`{"0": {"3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3820, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"0": {"origin_step": 4528, "count": 1, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3820, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3820, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "1": {"origin_step": 1689, "count": 2, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 2415, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 3244, "count": 1, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`；stale_positive=True表示实际已投空但此机仍持有旧正数。
同帧多机提交=True；choice后等待步数=None；观察到2步等待=None（无choice不适用）。

50%：路径 `hard_fallback`；全部提交 `[{"drone": 0, "step": 5405, "walltime_seconds": 238.5209093093872, "image_sha256": "aeac9c1ff08c8c605b5823e98795e0ffcb14b84d57e0a4455f83855fcb648c94"}, {"drone": 1, "step": 5405, "walltime_seconds": 238.5209093093872, "image_sha256": "7098d4fcf4f086822f3ae5f7994eac5bda65e1f31601fcb4b2fc1ed6fdec13be"}, {"drone": 2, "step": 5405, "walltime_seconds": 238.5209093093872, "image_sha256": "f0320c82c1cc7618d752ac7bac187a40e708ad949e95196f88f8e41b3504a01d"}, {"drone": 3, "step": 5405, "walltime_seconds": 238.5209093093872, "image_sha256": "7012c0a1dbc68a1efe21919b51bfac5d581bb5898819d2d234965110a38d53c9"}, {"drone": 4, "step": 5405, "walltime_seconds": 238.5209093093872, "image_sha256": "aee4fc960c389af6faafbd5fb8a5db98f03e99309e84c0e3192bcf47d0abcba3"}]`。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的记录：`{"0": {"4": {"origin_step": 4740, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"4": {"origin_step": 4740, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 4278, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"4": {"origin_step": 4740, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`；stale_positive=True表示实际已投空但此机仍持有旧正数。
同帧多机提交=True；choice后等待步数=None；观察到2步等待=None（无choice不适用）。

60%：路径 `ordinary_direct_after_exchange`；全部提交 `[{"drone": 0, "step": 5844, "walltime_seconds": 230.35423183441162, "image_sha256": "9cf39bb334926ab1927b677a46b54ce583339a16558668af3a182b8d4600112b"}]`。
首次全队零确认：`{"0": 5818, "1": null, "2": 5818, "3": null, "4": null}`；普通就绪：`{"0": 5818, "1": null, "2": 5818, "3": null, "4": null}`；交互提前出口启动：`{"0": 5830, "1": null, "2": 5828, "3": null, "4": null}`。
结束时仍为正库存的记录：`{"0": {}, "1": {"0": {"origin_step": 5082, "count": 1, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3503, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {}, "3": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3820, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}}}`；stale_positive=True表示实际已投空但此机仍持有旧正数。
同帧多机提交=False；choice后等待步数=0；观察到2步等待=False（无choice不适用）。

### Map06
40%：路径 `group_submit`；全部提交 `[{"drone": 3, "step": 3972, "walltime_seconds": 177.77454590797424, "image_sha256": "180a0a96d73f86336a1966f530992a73e5f311f87eed528ac21ac33c822955ff"}]`。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": 3968, "4": 3968}`；普通就绪：`{"0": null, "1": null, "2": null, "3": 3968, "4": 3968}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的记录：`{"0": {"3": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"3": {"origin_step": 3450, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"3": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {}, "4": {}}`；stale_positive=True表示实际已投空但此机仍持有旧正数。
同帧多机提交=False；choice后等待步数=None；观察到2步等待=None（无choice不适用）。

50%：路径 `hard_fallback`；全部提交 `[{"drone": 0, "step": 4840, "walltime_seconds": 178.56026649475098, "image_sha256": "3820ccf6bc04f548ad1e7d68e9ba9c718b95b10a891384f53ce8c617ab1cfe88"}, {"drone": 1, "step": 4840, "walltime_seconds": 178.56026649475098, "image_sha256": "ef3c752fca00e6a1bf0154773f77110d25ee0e345985e15a6851288d18fc230e"}, {"drone": 2, "step": 4840, "walltime_seconds": 178.56026649475098, "image_sha256": "d490706f8340d4f23790a43e6301b8beb69c499c2091206bf4c4ca6370eacedb"}, {"drone": 3, "step": 4840, "walltime_seconds": 178.56026649475098, "image_sha256": "23d9f3fcd7edfc1b614c1d758f1b18ecfaf0bcae5c0ebc6c2b929846c43c93a6"}, {"drone": 4, "step": 4840, "walltime_seconds": 178.56026649475098, "image_sha256": "794cf843899ef3c1157951862e1cb4c4b0383e501e8c22377e6ed2dcb678fec7"}]`。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的记录：`{"0": {"1": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 3032, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"0": {"origin_step": 899, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"0": {"origin_step": 899, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"1": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"1": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 3032, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`；stale_positive=True表示实际已投空但此机仍持有旧正数。
同帧多机提交=True；choice后等待步数=None；观察到2步等待=None（无choice不适用）。

60%：路径 `hard_fallback`；全部提交 `[{"drone": 0, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "2d44903c259e96aeaf65ee1cfc10ca08296af3ff7bf58c50a93708bf976d60cb"}, {"drone": 1, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "3adb8fc2296c1e304c61ceb4fa2ad1742137c5f31a755a8d8f80c4f33af65407"}, {"drone": 2, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "3fda68ee2922abc82bed0d6ba03deb41a72dea00c5b1750367667f6dd6adf28b"}, {"drone": 3, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "6e1f70bfc9374eb85b21cf9fcb7c89890751023e06fa05563df3d0b9f884783d"}, {"drone": 4, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "dde55b5770b7fe667592d5c7dd821a6fc23cf168a150fb9b5ce627d59140c8c1"}]`。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的记录：`{"0": {"3": {"origin_step": 2678, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"3": {"origin_step": 2678, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"0": {"origin_step": 899, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"1": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"1": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`；stale_positive=True表示实际已投空但此机仍持有旧正数。
同帧多机提交=True；choice后等待步数=None；观察到2步等待=None（无choice不适用）。

### Map07
40%：路径 `hard_fallback`；全部提交 `[{"drone": 0, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "b91f52bdaffb50ed3327ee849b4e3bb3146f4964b305b44fa0ffc96605c699df"}, {"drone": 1, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "330033bf7021bb403378eb41046c8594a51a49e7a21cd14765e12843594157f7"}, {"drone": 2, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "34a500660febdad316a438c4e8594e4d1b2dc28bb84650b6ffc08c82ff3ce120"}, {"drone": 3, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "4a0a8bccef30c2f67cb1f270e13d7f9452a18ca924630ae508c074a80cc398d5"}, {"drone": 4, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "bf261c52f7ffb2ee2f1ff84a2c268ce879ce4a7538b383abf0323bae6aa5f918"}]`。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的记录：`{"0": {"1": {"origin_step": 2314, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1455, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1578, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"1": {"origin_step": 2314, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1455, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1578, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`；stale_positive=True表示实际已投空但此机仍持有旧正数。
同帧多机提交=True；choice后等待步数=None；观察到2步等待=None（无choice不适用）。

50%：路径 `budget93`；全部提交 `[{"drone": 0, "step": 5040, "walltime_seconds": 144.52459192276, "image_sha256": "2c8079acce2a7edf425bd3449b7fd2ea5815d28102aefc8360da53ae42e528b6"}, {"drone": 1, "step": 5040, "walltime_seconds": 144.52459192276, "image_sha256": "2e8791ba6fe05ffc6463b05934cee1a90f0c1bbceb8e092e161a741002c71dbb"}, {"drone": 2, "step": 5040, "walltime_seconds": 144.52459192276, "image_sha256": "2e8791ba6fe05ffc6463b05934cee1a90f0c1bbceb8e092e161a741002c71dbb"}, {"drone": 3, "step": 5040, "walltime_seconds": 144.52459192276, "image_sha256": "8912bc85bed00d25406752b1c612e9ce5d536ba86af6dd5c75f05dce281d7ae7"}]`。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的记录：`{"0": {"1": {"origin_step": 2309, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1455, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1578, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1915, "count": 1, "actual_remaining": 1, "stale_positive": false}}, "1": {"3": {"origin_step": 1783, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1915, "count": 1, "actual_remaining": 1, "stale_positive": false}}, "2": {"3": {"origin_step": 1783, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1915, "count": 1, "actual_remaining": 1, "stale_positive": false}}, "3": {"0": {"origin_step": 1578, "count": 1, "actual_remaining": 0, "stale_positive": true}, "1": {"origin_step": 831, "count": 2, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1783, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1366, "count": 1, "actual_remaining": 1, "stale_positive": false}}, "4": {"4": {"origin_step": 5040, "count": 1, "actual_remaining": 1, "stale_positive": false}, "0": {"origin_step": 1303, "count": 2, "actual_remaining": 0, "stale_positive": true}, "1": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1305, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1366, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`；stale_positive=True表示实际已投空但此机仍持有旧正数。
同帧多机提交=True；choice后等待步数=None；观察到2步等待=None（无choice不适用）。

60%：路径 `budget93`；全部提交 `[{"drone": 1, "step": 5039, "walltime_seconds": 158.44769930839539, "image_sha256": "5af831b4cc32345f53b0bed0c9cb8dd7dcc89fc7acb739ef35e5527c7234f8a8"}, {"drone": 2, "step": 5039, "walltime_seconds": 158.44769930839539, "image_sha256": "a2f65ff114860b2128b96d9fb2b6b0cc3094debfac3eea80c062d1d482732bf9"}, {"drone": 3, "step": 5039, "walltime_seconds": 158.44769930839539, "image_sha256": "0aafee35f46da085507900100257ff8da9107619dbf6110633f22524a8dfbe85"}]`。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的记录：`{"0": {"1": {"origin_step": 2309, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1455, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1578, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"0": {"origin_step": 1303, "count": 2, "actual_remaining": 0, "stale_positive": true}, "1": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1305, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1366, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`；stale_positive=True表示实际已投空但此机仍持有旧正数。
同帧多机提交=True；choice后等待步数=None；观察到2步等待=None（无choice不适用）。

## 同一步数耗时与环境

三版都按8个空闲逻辑CPU、来自8个物理核的口径启动；SMT兄弟线程可能忙。历史CPU池/负载不同，不是独占、同时同核或严格同负载实验。诊断观察器与40%版相同，库存日志从40%采样但不参与控制。资源和队列等待保留，不将墙钟差全归因于返航参数。

| 地图 | 步数 | 60%累计秒 | 50%累计秒 | 50%−60%秒 |
|---|---:|---:|---:|---:|
| Map05 | 1001 | 25.5839 | 26.1183 | +0.5344 |
| Map05 | 2001 | 58.0175 | 62.0144 | +3.9969 |
| Map05 | 2160 | 62.9678 | 68.2926 | +5.3248 |
| Map05 | 2700 | 84.5714 | 93.8581 | +9.2867 |
| Map05 | 2880 | 91.2243 | 101.4800 | +10.2557 |
| Map05 | 3001 | 97.5045 | 109.9398 | +12.4353 |
| Map05 | 3240 | 105.5248 | 120.4661 | +14.9414 |
| Map05 | 3600 | 120.0767 | 139.9677 | +19.8910 |
| Map05 | 4001 | 135.8162 | 162.2808 | +26.4646 |
| Map05 | 4320 | 149.6949 | 179.3583 | +29.6634 |
| Map05 | 5001 | 185.0233 | 219.2156 | +34.1923 |
| Map06 | 1001 | 28.1682 | 31.4017 | +3.2335 |
| Map06 | 2001 | 67.9979 | 71.2831 | +3.2852 |
| Map06 | 2160 | 74.9019 | 76.4572 | +1.5553 |
| Map06 | 2700 | 96.5512 | 97.9491 | +1.3979 |
| Map06 | 2880 | 102.9333 | 105.1078 | +2.1745 |
| Map06 | 3001 | 107.6392 | 109.2717 | +1.6325 |
| Map06 | 3240 | 117.3151 | 117.4476 | +0.1325 |
| Map06 | 3600 | 135.2511 | 130.8057 | -4.4454 |
| Map06 | 4001 | 152.5930 | 148.2048 | -4.3882 |
| Map06 | 4320 | 164.9525 | 158.6884 | -6.2641 |
| Map07 | 1001 | 24.1005 | 21.6703 | -2.4302 |
| Map07 | 2001 | 54.5733 | 50.7447 | -3.8286 |
| Map07 | 2160 | 59.5621 | 55.6422 | -3.9199 |
| Map07 | 2700 | 77.0503 | 72.5602 | -4.4900 |
| Map07 | 2880 | 82.9998 | 78.7848 | -4.2151 |
| Map07 | 3001 | 87.0059 | 82.4191 | -4.5868 |
| Map07 | 3240 | 94.9692 | 89.4927 | -5.4765 |
| Map07 | 3600 | 109.7631 | 100.5779 | -9.1852 |
| Map07 | 4001 | 124.1560 | 112.9166 | -11.2395 |
| Map07 | 4320 | 134.4763 | 122.2122 | -12.2642 |
| Map07 | 5001 | 157.4166 | 143.4876 | -13.9290 |

与40%的同一步数耗时、轨迹首次差异、落点变化、漏墙和误画详见RESULTS.json。50%沿用原候选已知的确认和普通提交回落问题，本轮没有连带修复；不因为分数变化声称已解决。没有官网验证、官网上传或新的正式比赛ZIP。

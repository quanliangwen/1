# 40%返航与60%返航候选：Map05、Map06、Map07，种子615

本轮40%候选每图只完成一场，共3场红队；60%候选仅引用既有记录，未重跑。没有测试其他地图、没有在测试中修改算法、SDK、依赖、导航或拟合。V16继续作为比赛基线。

新旧56项源码仅group_exchange.py的返航入口差异；新40%门槛为Map05=2880步、Map06/07=2160步，末弹普通完成和交图相关共享60%门槛保持。携弹、待确认、安全路径和剩余预算仍限制实际返航，不是到40%就强制飞回。

40%冻结归档SHA256 `849714c8438fc9ec35b2327807b907133dc7c93bcd4b17a56d1dd0e47dafd8c4`；60%归档 `c4b8513084ce114e6aae04b42489c995e73955ec545a64c5f9d999190004a562`。三场输入及运行时56项源码前后核对通过，正式V16归档哈希未变。

SDK6557940dc18549ffc7a945db887da5b05b7ed2f1；Map05原生7200步/240秒，Map06/07为5400步/180秒。每图5机、每机2枚；种子、出生点/朝向、地图几何、SDK归档、原生时限、区域和评分配置与各自60%旧记录核对一致。实际无GPS/禁通信区域：Map05与Map07为0/0，Map06为0/1。

## 总体结果

| 地图 | 版本 | SDK采用提交者/步数 | 得分小计/80 | 地图分 | 墙覆盖分 | 探索率/% | 实投 | 掉血 | 最终墙钟/秒 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Map05 | 60% | 0 / 5844 | 59.8388 | 95.0474 | 48.1231 | 100.0000 | 10/10 | 7 | 230.4730 |
| Map05 | 40% | 0 / 5385 | 61.7560 | 96.3008 | 50.0222 | 100.0000 | 10/10 | 17 | 238.6529 |
| Map06 | 60% | 0 / 4678 | 53.9027 | 87.5372 | 41.1201 | 99.3744 | 10/10 | 4 | 178.6050 |
| Map06 | 40% | 3 / 3972 | 51.7078 | 80.0646 | 39.4887 | 99.3744 | 10/10 | 5 | 177.8811 |
| Map07 | 60% | 1 / 5039 | 54.9288 | 90.2120 | 44.3387 | 99.9429 | 10/10 | 4 | 158.5508 |
| Map07 | 40% | 0 / 4561 | 31.8949 | 45.2315 | 35.2979 | 98.3632 | 10/10 | 4 | 178.6376 |

小计沿用历史口径，并核对官方0.5×地图分＋0.2×墙覆盖分＋0.1×时间分；不把未输出的炸弹项当成完整100分。提交者为SDK所采用图片的来源，不代表同帧只有该机调用提交。

## 本轮判断

40%门槛确实让部分飞机更早接管返航，但未带来稳定的提前结束。本轮不建议以40%替换60%设置，V16继续保留。单种子历史对照不能证明稳定因果收益，下面将已确认的行为与需要后续研究的问题分开。

### Map05：分数升了，结束反而更晚

- 1/2/3号首次返航从4365/4332/4320提前到3049/3375/3009步；4号从5229到5079步，0号两版都未接管返航。
- 末弹：0号5660→5661变5038→5039；2号3314→3315变3374→3375；4号5228→5229变5066→5067。0、4号本轮都由原墙钟收尾投出，4号没有重复60%版普通完成分支的成功。
- 60%版0/2号5818步曾收齐全队零确认；40%版没有任何飞机收齐。0号结束仍认为3/4号有剩弹，普通提交被挡住，五机5385步硬兜底，SDK采用0号。
- 得分小计+1.917、地图分+1.253、墙覆盖+1.899、探索率仍100%；但掉血7→17，墙钟230.473→238.653秒。步数少459不等于实际省时：配置时间分按步数计，时间分本身提高9.107贡献约0.911小计，其余来自地图与墙覆盖。
- 3号原返航ETA136步，本轮1384步，随后仍因no_safe_join中止。说明改变触发时刻会改变原规则在轨迹上选中的接入点和返程长度，并非把同一条短路线简单提前。

### Map06：局部补齐确认，但代价较大

- 0/1/2/4号接管返航提前到2408/2393/2167/2200步，3号未接管。60%版对应3242/3299/3324/3255，3号3247步接管。
- 3号末弹从3246→3247推迟为3664→3665，来自原墙钟收尾；其余各机第二枚实投/确认步数相同。
- 3/4号3968步收齐全队零确认，说明信息交接有局部改善；0/1/2号仍缺旧确认。3号3972步走group soft_cutoff_submit，未依赖硬兜底，但交互提前出口early_finish_started仍为空，且只比60%版少0.724秒墙钟。
- 得分小计-2.195，地图分-7.473，墙覆盖-1.631，探索率均99.3744%，掉血4→5。
- “投放步数没变”不代表位置没变：1号第二枚均2392步，但真实中心移动622.285px；3号第二枚移动160.187px。其余8枚实投中心未变。不能把墙覆盖退分笼统归为CPU负载。

### Map07：明显回归，早返航未闭合确认与提交

- 0/2/3号从3240提前到2160步；1号3240→2518步；4号仍3251步。
- 1号末弹2382→2383变2517→2518，晚135步；4号两版均3250→3251，10枚均投完。但1号末弹中心移动231.248px，4号移动110.743px；其余8枚实投中心未变。墙覆盖44.339→35.298，下降9.041分。
- 0号结束时仍持有1/2/3号旧正库存，1/2/3号仍持有4号1915步剩1的旧记录；没有任何飞机收齐全队清零，正常提前交图入口未启动。
- 60%版由1/2/3号5039步预算出口同帧提交，SDK采用1号，地图分90.212；40%版五机4561步硬兜底同帧提交，SDK采用0号，所提交图地图分45.231。得分小计54.929→31.895，下降23.034。
- 探索率99.9429%→98.3632%，只下降1.5797个百分点，不能仅用“少探索了一些”解释地图分下降44.981。可确认提交者和结束路径改变、实际提交的0号图得分很低；本轮未对其他未采用图片逐张计算官方分，不能声称另一架必然能提交多少分。
- 掉血均4，最终墙钟158.551→178.638秒，增加20.087秒。

### 共同边界

40%版三图early_finish_started均为空；更早接管返航不等于交互任务完成。早触发后仍有多次no_safe_join中止，携弹者仍不能返航，通信缺口仍可能持续到终局。

源码仅返航入口变化，但协同飞行会连带改变路径、接触时机、地图证据、投放位置和最终提交者。这些实际变化有轨迹及事件日志支持，不是改了导航或投放公式。

墙钟和同一步数耗时还受到历史负载、SMT及流程计算量影响；例如Map05在2880步以前、两版轨迹尚未分歧时，新场累计已慢约9.420秒。不能把墙钟差全部算成40%参数的计算退化，也不能忽略已确认的落点、确认和终局路径变化而全推给环境。


## 实际返航接管步数

以下取原group_audit中首次return_owned：表示通过预检并接管返航任务，不是达到比例门槛，也不是已经到达交互点。—表示截至比赛结束未实际接管。重试、到达和中止另列于RESULTS.json。

| 地图 | 版本 | 0号 | 1号 | 2号 | 3号 | 4号 |
|---|---|---:|---:|---:|---:|---:|
| Map05 | 60% | — | 4365 | 4332 | 4320 | 5229 |
| Map05 | 40% | — | 3049 | 3375 | 3009 | 5079 |
| Map06 | 60% | 3242 | 3299 | 3324 | 3247 | 3255 |
| Map06 | 40% | 2408 | 2393 | 2167 | — | 2200 |
| Map07 | 60% | 3240 | 3240 | 3240 | 3240 | 3251 |
| Map07 | 40% | 2160 | 2518 | 2160 | 2160 | 3251 |

## 第二枚实投→库存确认

| 地图 | 版本 | 0号 | 1号 | 2号 | 3号 | 4号 |
|---|---|---|---|---|---|---|
| Map05 | 60% | 5660→5661 | 2112→2113 | 3314→3315 | 3007→3008 | 5228→5229 |
| Map05 | 40% | 5038→5039 | 2112→2113 | 3374→3375 | 3007→3008 | 5066→5067 |
| Map06 | 60% | 2080→2081 | 2392→2393 | 1414→1415 | 3246→3247 | 2020→2021 |
| Map06 | 40% | 2080→2081 | 2392→2393 | 1414→1415 | 3664→3665 | 2020→2021 |
| Map07 | 60% | 1640→1641 | 2382→2383 | 2054→2055 | 2146→2147 | 3250→3251 |
| Map07 | 40% | 1640→1641 | 2517→2518 | 2054→2055 | 2146→2147 | 3250→3251 |

实投来自SDK _try_place_bomb成功；确认来自库存下降，发指令不算投成。分支、实际中心坐标与墙钟时间均见RESULTS.json。

## 确认与终局路径

### Map05
60%：结束路径 `ordinary_direct_after_exchange`；全部提交 `[{"drone": 0, "step": 5844, "walltime_seconds": 230.35423183441162, "image_sha256": "9cf39bb334926ab1927b677a46b54ce583339a16558668af3a182b8d4600112b"}]`；同帧多机提交=False。
首次全队零确认：`{"0": 5818, "1": null, "2": 5818, "3": null, "4": null}`；普通就绪：`{"0": 5818, "1": null, "2": 5818, "3": null, "4": null}`；交互提前出口启动：`{"0": 5830, "1": null, "2": 5828, "3": null, "4": null}`。
结束时仍为正库存的来源：`{"0": {}, "1": {"0": {"origin_step": 5082, "count": 1, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3503, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {}, "3": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3820, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}}}`。stale_positive=True表示该机仍持有旧正数，而对应飞机实际已空。
选择提案后等待步数=0；观察到至少2步等待=False（无choice为不适用）。
返航任务：`{"0": [], "1": [{"step": 4365, "group": [1, 2], "target": [54.65463216924157, 491.99472347126573], "estimated_steps": 79}, {"step": 4442, "group": [1, 2], "target": [54.65463216924157, 491.99472347126573], "estimated_steps": 95}], "2": [{"step": 4332, "group": [1, 2], "target": [-116.29763486901436, 408.64761634926873], "estimated_steps": 870}, {"step": 4605, "group": [1, 2], "target": [-116.29763486901436, 408.64761634926873], "estimated_steps": 1004}], "3": [{"step": 4320, "group": [3], "target": [136.49224751752342, -129.2771484311561], "estimated_steps": 136}, {"step": 4429, "group": [3], "target": [136.49224751752342, -129.2771484311561], "estimated_steps": 140}], "4": [{"step": 5229, "group": [0, 4], "target": [-37.368781315011816, -287.6571624399563], "estimated_steps": 383}, {"step": 5366, "group": [0, 4], "target": [-37.368781315011816, -287.6571624399563], "estimated_steps": 381}]}`；返航中止：`{"0": [], "1": [[4422, "route_abort", "no_safe_join"], [4505, "route_abort", "no_safe_join"]], "2": [[4585, "route_abort", "no_safe_join"], [4838, "route_abort", "no_safe_join"]], "3": [[4409, "route_abort", "no_safe_join"]], "4": [[5346, "route_abort", "no_safe_join"], [5644, "route_abort", "no_safe_join"]]}`。

40%：结束路径 `hard_fallback`；全部提交 `[{"drone": 0, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "8e16c64b0b3b9520d5d94cbb3bbb8823f6982537bdf1f2364dc69ccb09c1688e"}, {"drone": 1, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "e2e4cb2b245678e04076823e2208c213117de1eebfeee4eecc1a70aa55e3679e"}, {"drone": 2, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "74a19cf90558b7fb562a8fe7d9bc2ff1cfadfc5b45b0ea2e515581e29af81845"}, {"drone": 3, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "6ae995c854393c8e1cc2e38a75873904ed2175f11342eb9b4f866fb8c3498740"}, {"drone": 4, "step": 5385, "walltime_seconds": 238.52475762367249, "image_sha256": "a54ca3151dec91adfa848fd35885e7dd4787bc057ec0033faaa2e20a00317fe3"}]`；同帧多机提交=True。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的来源：`{"0": {"3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3820, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"0": {"origin_step": 4528, "count": 1, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3820, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 3820, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "1": {"origin_step": 1689, "count": 2, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 2415, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"0": {"origin_step": 1399, "count": 2, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 3244, "count": 1, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 2877, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`。stale_positive=True表示该机仍持有旧正数，而对应飞机实际已空。
选择提案后等待步数=None；观察到至少2步等待=None（无choice为不适用）。
返航任务：`{"0": [], "1": [{"step": 3049, "group": [1, 2], "target": [-12.551353762349095, 483.0301442583525], "estimated_steps": 774}], "2": [{"step": 3375, "group": [1, 2], "target": [-116.29763486901436, 408.64761634926873], "estimated_steps": 1223}], "3": [{"step": 3009, "group": [3], "target": [26.132140011719382, -15.528218813414087], "estimated_steps": 1384}, {"step": 3149, "group": [3], "target": [26.132140011719382, -15.528218813414087], "estimated_steps": 1398}], "4": [{"step": 5079, "group": [0, 4], "target": [-37.368781315011816, -287.6571624399563], "estimated_steps": 319}]}`；返航中止：`{"0": [], "1": [[3122, "route_abort", "no_safe_join"]], "2": [[3585, "route_abort", "no_safe_join"]], "3": [[3129, "route_abort", "no_safe_join"], [3770, "route_abort", "no_safe_join"]], "4": []}`。

### Map06
60%：结束路径 `hard_fallback`；全部提交 `[{"drone": 0, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "2d44903c259e96aeaf65ee1cfc10ca08296af3ff7bf58c50a93708bf976d60cb"}, {"drone": 1, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "3adb8fc2296c1e304c61ceb4fa2ad1742137c5f31a755a8d8f80c4f33af65407"}, {"drone": 2, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "3fda68ee2922abc82bed0d6ba03deb41a72dea00c5b1750367667f6dd6adf28b"}, {"drone": 3, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "6e1f70bfc9374eb85b21cf9fcb7c89890751023e06fa05563df3d0b9f884783d"}, {"drone": 4, "step": 4678, "walltime_seconds": 178.51376485824585, "image_sha256": "dde55b5770b7fe667592d5c7dd821a6fc23cf168a150fb9b5ce627d59140c8c1"}]`；同帧多机提交=True。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的来源：`{"0": {"3": {"origin_step": 2678, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"3": {"origin_step": 2678, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"0": {"origin_step": 899, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"1": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"1": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`。stale_positive=True表示该机仍持有旧正数，而对应飞机实际已空。
选择提案后等待步数=None；观察到至少2步等待=None（无choice为不适用）。
返航任务：`{"0": [{"step": 3242, "group": [0], "target": [507.3337573509359, 34.43239326048233], "estimated_steps": 737}], "1": [{"step": 3299, "group": [1], "target": [612.1523169604726, -3.3714162253558935], "estimated_steps": 1078}], "2": [{"step": 3324, "group": [1, 2, 4], "target": [597.2762815492972, -199.6866652883096], "estimated_steps": 1012}, {"step": 3432, "group": [1, 2, 4], "target": [597.2762815492972, -199.6866652883096], "estimated_steps": 1029}], "3": [{"step": 3247, "group": [3], "target": [507.74936358318115, 50.55666352202038], "estimated_steps": 1194}], "4": [{"step": 3255, "group": [1, 2, 4], "target": [667.9335394226515, -351.09873218275163], "estimated_steps": 838}]}`；返航中止：`{"0": [[3348, "route_abort", "no_safe_join"]], "1": [[3456, "route_abort", "no_safe_join"]], "2": [[3412, "route_abort", "no_safe_join"], [3507, "route_abort", "no_safe_join"]], "3": [[3901, "route_abort", "no_safe_join"]], "4": [[3307, "route_abort", "no_safe_join"]]}`。

40%：结束路径 `group_submit`；全部提交 `[{"drone": 3, "step": 3972, "walltime_seconds": 177.77454590797424, "image_sha256": "180a0a96d73f86336a1966f530992a73e5f311f87eed528ac21ac33c822955ff"}]`；同帧多机提交=False。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": 3968, "4": 3968}`；普通就绪：`{"0": null, "1": null, "2": null, "3": 3968, "4": 3968}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的来源：`{"0": {"3": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"3": {"origin_step": 3450, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"3": {"origin_step": 1928, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1791, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {}, "4": {}}`。stale_positive=True表示该机仍持有旧正数，而对应飞机实际已空。
选择提案后等待步数=None；观察到至少2步等待=None（无choice为不适用）。
返航任务：`{"0": [{"step": 2408, "group": [0, 1, 4], "target": [-520.6006464328132, 478.765877835742], "estimated_steps": 1034}, {"step": 2477, "group": [0, 1, 4], "target": [-520.6006464328132, 478.765877835742], "estimated_steps": 1041}], "1": [{"step": 2393, "group": [1], "target": [612.1523169604726, -3.3714162253558935], "estimated_steps": 726}], "2": [{"step": 2167, "group": [1, 2, 4], "target": [597.2762815492972, -199.6866652883096], "estimated_steps": 393}], "3": [], "4": [{"step": 2200, "group": [1, 2, 4], "target": [667.9335394226515, -351.09873218275163], "estimated_steps": 794}, {"step": 2277, "group": [1, 2, 4], "target": [667.9335394226515, -351.09873218275163], "estimated_steps": 810}]}`；返航中止：`{"0": [[2457, "route_abort", "no_safe_join"], [2534, "route_abort", "no_safe_join"]], "1": [[3254, "route_abort", "no_safe_join"]], "2": [[2217, "route_abort", "no_safe_join"]], "3": [], "4": [[2257, "route_abort", "no_safe_join"], [2444, "route_abort", "no_safe_join"]]}`。

### Map07
60%：结束路径 `budget93`；全部提交 `[{"drone": 1, "step": 5039, "walltime_seconds": 158.44769930839539, "image_sha256": "5af831b4cc32345f53b0bed0c9cb8dd7dcc89fc7acb739ef35e5527c7234f8a8"}, {"drone": 2, "step": 5039, "walltime_seconds": 158.44769930839539, "image_sha256": "a2f65ff114860b2128b96d9fb2b6b0cc3094debfac3eea80c062d1d482732bf9"}, {"drone": 3, "step": 5039, "walltime_seconds": 158.44769930839539, "image_sha256": "0aafee35f46da085507900100257ff8da9107619dbf6110633f22524a8dfbe85"}]`；同帧多机提交=True。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的来源：`{"0": {"1": {"origin_step": 2309, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1455, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1578, "count": 1, "actual_remaining": 0, "stale_positive": true}, "4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"0": {"origin_step": 1303, "count": 2, "actual_remaining": 0, "stale_positive": true}, "1": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1305, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1366, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`。stale_positive=True表示该机仍持有旧正数，而对应飞机实际已空。
选择提案后等待步数=None；观察到至少2步等待=None（无choice为不适用）。
返航任务：`{"0": [{"step": 3240, "group": [0, 3], "target": [397.83708923739476, -251.08243055395462], "estimated_steps": 102}, {"step": 3336, "group": [0, 3], "target": [397.83708923739476, -251.08243055395462], "estimated_steps": 103}], "1": [{"step": 3240, "group": [0, 1, 2, 4], "target": [-26.98624200395031, 121.61758240138009], "estimated_steps": 545}, {"step": 3340, "group": [0, 1, 2, 4], "target": [-26.98624200395031, 121.61758240138009], "estimated_steps": 575}], "2": [{"step": 3240, "group": [0, 2, 3], "target": [542.3874558548303, -158.36211933712667], "estimated_steps": 1202}], "3": [{"step": 3240, "group": [0, 3], "target": [432.98420594059655, -377.3803886655963], "estimated_steps": 866}], "4": [{"step": 3251, "group": [3, 4], "target": [751.0938042875916, -35.794660481259655], "estimated_steps": 294}]}`；返航中止：`{"0": [[3316, "route_abort", "no_safe_join"], [3410, "route_abort", "no_safe_join"]], "1": [[3320, "route_abort", "no_safe_join"], [3423, "route_abort", "no_safe_join"]], "2": [[3414, "route_abort", "no_safe_join"]], "3": [], "4": []}`。

40%：结束路径 `hard_fallback`；全部提交 `[{"drone": 0, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "b91f52bdaffb50ed3327ee849b4e3bb3146f4964b305b44fa0ffc96605c699df"}, {"drone": 1, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "330033bf7021bb403378eb41046c8594a51a49e7a21cd14765e12843594157f7"}, {"drone": 2, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "34a500660febdad316a438c4e8594e4d1b2dc28bb84650b6ffc08c82ff3ce120"}, {"drone": 3, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "4a0a8bccef30c2f67cb1f270e13d7f9452a18ca924630ae508c074a80cc398d5"}, {"drone": 4, "step": 4561, "walltime_seconds": 178.5091381072998, "image_sha256": "bf261c52f7ffb2ee2f1ff84a2c268ce879ce4a7538b383abf0323bae6aa5f918"}]`；同帧多机提交=True。
首次全队零确认：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；普通就绪：`{"0": null, "1": null, "2": null, "3": null, "4": null}`；交互提前出口启动：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。
结束时仍为正库存的来源：`{"0": {"1": {"origin_step": 2314, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1455, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1578, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "1": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "2": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "3": {"4": {"origin_step": 1915, "count": 1, "actual_remaining": 0, "stale_positive": true}}, "4": {"1": {"origin_step": 2314, "count": 1, "actual_remaining": 0, "stale_positive": true}, "2": {"origin_step": 1455, "count": 2, "actual_remaining": 0, "stale_positive": true}, "3": {"origin_step": 1578, "count": 1, "actual_remaining": 0, "stale_positive": true}}}`。stale_positive=True表示该机仍持有旧正数，而对应飞机实际已空。
选择提案后等待步数=None；观察到至少2步等待=None（无choice为不适用）。
返航任务：`{"0": [{"step": 2160, "group": [0, 3], "target": [397.83708923739476, -251.08243055395462], "estimated_steps": 100}, {"step": 3077, "group": [0, 3], "target": [397.83708923739476, -251.08243055395462], "estimated_steps": 143}], "1": [{"step": 2518, "group": [0, 1, 2, 4], "target": [49.815901979955456, 70.27204342435104], "estimated_steps": 40}], "2": [{"step": 2160, "group": [0, 2, 3], "target": [542.3874558548303, -158.36211933712667], "estimated_steps": 861}, {"step": 2324, "group": [0, 2, 3], "target": [542.3874558548303, -158.36211933712667], "estimated_steps": 924}], "3": [{"step": 2160, "group": [0, 3], "target": [432.98420594059655, -377.3803886655963], "estimated_steps": 863}, {"step": 2632, "group": [0, 3], "target": [432.98420594059655, -377.3803886655963], "estimated_steps": 864}], "4": [{"step": 3251, "group": [3, 4], "target": [722.6886982668399, -35.31772886244785], "estimated_steps": 223}]}`；返航中止：`{"0": [[3057, "route_abort", "no_safe_join"], [4047, "route_abort", "no_safe_join"]], "1": [[2939, "route_abort", "no_safe_join"]], "2": [[2304, "route_abort", "no_safe_join"], [2507, "route_abort", "no_safe_join"]], "3": [[2612, "route_abort", "no_safe_join"], [2743, "route_abort", "no_safe_join"]], "4": [[4002, "route_abort", "no_safe_join"]]}`。

## 同一步数耗时及环境

两版均分配8个逻辑CPU，来自8个不同物理核；启动前对实际分配CPU按3次2秒采样、最大忙碌不超过5%选取，SMT兄弟线程可能忙。不是独占、整机低负载或同时同核对照。不同历史时段负载不能完全控制，墙钟差不作为纯算法加速因果结论。CPU采样和运行队列等待统计保留。
40%观察器仅将库存状态变化日志起点提前到40%，其余原观察、计分和控制调用顺序不变；实际返航审计本身是原算法日志。该诊断差异仍需披露。

| 地图 | 步数 | 60%累计秒 | 40%累计秒 | 40%−60%秒 |
|---|---:|---:|---:|---:|
| Map05 | 1001 | 25.5839 | 29.2664 | +3.6825 |
| Map05 | 2001 | 58.0175 | 64.2200 | +6.2025 |
| Map05 | 2160 | 62.9678 | 70.6725 | +7.7047 |
| Map05 | 2880 | 91.2243 | 100.6448 | +9.4205 |
| Map05 | 3001 | 97.5045 | 109.1980 | +11.6935 |
| Map05 | 3240 | 105.5248 | 122.2275 | +16.7027 |
| Map05 | 4001 | 135.8162 | 163.6607 | +27.8445 |
| Map05 | 4320 | 149.6949 | 180.9670 | +31.2722 |
| Map05 | 5001 | 185.0233 | 218.2889 | +33.2655 |
| Map06 | 1001 | 28.1682 | 30.2302 | +2.0620 |
| Map06 | 2001 | 67.9979 | 75.0063 | +7.0084 |
| Map06 | 2160 | 74.9019 | 82.5054 | +7.6036 |
| Map06 | 2880 | 102.9333 | 121.7162 | +18.7829 |
| Map06 | 3001 | 107.6392 | 128.8808 | +21.2416 |
| Map06 | 3240 | 117.3151 | 140.4268 | +23.1118 |
| Map07 | 1001 | 24.1005 | 31.0641 | +6.9635 |
| Map07 | 2001 | 54.5733 | 69.5124 | +14.9391 |
| Map07 | 2160 | 59.5621 | 76.3823 | +16.8202 |
| Map07 | 2880 | 82.9998 | 105.5744 | +22.5745 |
| Map07 | 3001 | 87.0059 | 111.1602 | +24.1543 |
| Map07 | 3240 | 94.9692 | 120.4138 | +25.4446 |
| Map07 | 4001 | 124.1560 | 156.7449 | +32.5889 |
| Map07 | 4320 | 134.4763 | 168.5177 | +34.0414 |

首个记录轨迹差异步数：`{"Map05": 3009, "Map06": 2167, "Map07": 2160}`。详细资源统计、漏墙、误画和原始审计见RESULTS.json与RUN_EVIDENCE.zip。

这是单种子每图单次观察。40%候选按“其他均不变”继承60%候选的既有问题，包括普通出口可能绕过choice两帧等待；本轮未修，也不因分数变化推定已经修复。未发布新的正式比赛提交包，V16保持不变。

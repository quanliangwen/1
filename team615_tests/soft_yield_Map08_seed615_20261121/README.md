# 软应急让行候选：Map08，种子615，单次对照

本次只新跑1场当前候选Map08，不重跑V17/V16、不跑其他地图、不修改算法或SDK。

| 指标 | 已有V16 | 已有V17 | 当前候选 |
|---|---:|---:|---:|
| 交图者 | 1号 | 0号 | 1号 |
| 交图步数 | 3452 | 3445 | 3452 |
| 调用交图墙钟 | 128.325019秒 | 172.373912秒 | 154.260755秒 |
| 最终墙钟 | 128.395622秒 | 172.482176秒 | 154.378795秒 |
| 红队小计/80 | 52.641344 | 50.665605 | 52.641344 |
| 地图分 | 77.189215 | 73.200699 | 77.189215 |
| 实投数 | 10 | 10 | 10 |

本次结果：0号让行且未提交，1号在3452步交图，实际图片与V16逐字节相同；红队小计恢复至52.641344。但本次结束于154.378795秒，仍余25.621205秒，未进入不足12秒的软应急阶段。因此这次实测确认正常交图路径没有回退，不能单凭本次对照声称新软应急条件已经实战验证或导致提分；该特定条件目前仍由139组反例中的相关用例提供证据。

## 交图协调核对

`{"zero_ordinary_ready": true, "zero_guard_yielding_at_end": true, "zero_submitted": false, "one_submitted": true, "one_holds_bitmap_identical_to_V16": true, "actual_selected_bitmap_identical_to_V16": true, "actual_selected_bitmap_identical_to_V17": false, "low_walltime_yield_condition_exercised": false, "soft_cutoff_exit_used": false, "hard_fallback_used": false}`

0号末帧最终快照1份，普通交图就绪=True，首轮让行=True，实际提交=False。1号最终快照2份，实际提交=True，其缓存是否与V16成功提交图相同=True。

最终采用1号，方式为`ordinary`，结算后距离180秒上限仍有25.621205秒。提交记录：`[{"drone": 1, "step": 3452, "walltime_seconds": 154.2607548236847, "image_sha256": "a2b13dd8af95eb2165a021c903a0885ec0abd73641c09739deed482d008169c4"}]`。

相比V17小计变化+1.975739，地图变化+3.988516；相比V16小计变化+0.000000，地图变化+0.000000。实际提交图是否逐字节相同：`{"V16": true, "V17": false}`。

候选改动仅删除不足12秒取消首轮让行的条件，其他55个成员不变，5秒硬兜底保留。运行前后56成员及实际ZIP均校验；SDK/种子/出生点/区域/时限/线程与历史一致，观测脚本逐字节相同。历史和本次的每步耗时可能不同，不能把墙钟差异全部算作算法加速。数据中的低墙钟触发标记区分是否真正覆盖该应急条件，避免仅凭1号交好图就声称已经覆盖软应急。

得分为红队小计/80，不含蓝队炸弹难度校准，不是官网校准总分。调用交图墙钟为SDK采样，最终墙钟包含收尾；离线时间核对只读取已有回放，没有追加控制/物理仿真。

候选原件：[软应急让行研究候选](https://github.com/quanliangwen/1/tree/4dcedba1cfa3db5b303377c3af47ddde857d7b1b/team615_research/V17_soft_emergency_yield_20261121)。历史：[V17 Map08](https://github.com/quanliangwen/1/tree/8a34bd46c5a846b0da22621c41b16ca5248b0e88/team615_tests/V17_Map06_Map08_seed615_20261121)、[V16 Map08](https://github.com/quanliangwen/1/tree/cb079a122091ddee1f14e5bba4327260e91e82b3/team615_red_v15/first_round_yield_maps_20261121)。

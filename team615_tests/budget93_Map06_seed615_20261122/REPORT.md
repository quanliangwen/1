# 93%预算交图候选：Map06种子615单次测试

本轮只新增当前候选的一场Map06红队比赛；未重跑V16或按行索引基线，未跑其他地图。算法归档与六类反例通过版本逐字节一致，仍保留V16为比赛提交基线。

本次预算出口达到提前结束目标：SDK采用0号机第5039步提交，最终墙钟165.660309秒。相比已有按行索引候选，提前318步、实测少用12.967554秒，得分小计增加0.841270；地图图片、地图分、墙覆盖、全部10次实际投放相同。相比已有V16，实测少用12.946779秒，但步数仍多47步，小计仍低0.043881分。V16仍为比赛基线。

旧确认没有被补齐或清零：0号仍记录3号2678步剩1枚、4号1791步剩1枚；team_confirmed=false。普通提交未就绪，独立预算出口从5022步获得资格，在5039步按计划提交。实际场内五机库存均为零，共10枚实际投出，本次未牺牲实投数。

需要保留的风险：五机均在5039步调用提交，预算事件中均没有同窗对手估计。SDK最终采用0号图。本次只证明预算出口解除旧确认阻塞，不能称唯一提交协调或断联情况下最优地图选举已经解决。没有修改代码补救，也没有安排重跑。

## 三版本结果

| 指标 | 已有V16 | 已有按行索引 | 本轮93%预算出口 |
|---|---:|---:|---:|
| 交图者 | 0 | 0 | 0 |
| 交图步数 | 4992 | 5357 | 5039 |
| 得分小计/80 | 54.071588 | 53.186437 | 54.027707 |
| 地图分 | 88.995964 | 89.156880 | 89.156880 |
| 墙覆盖分 | 42.471203 | 42.471203 | 42.471203 |
| 时间分 | 10.793651 | 1.137566 | 9.550265 |
| 实投数 | 10 | 10 | 10 |
| 最终墙钟/秒 | 178.607089 | 178.627864 | 165.660309 |
| 交图指令墙钟/秒 | 178.521136 | 178.529991 | 165.569519 |
| 探索率/% | 99.374431 | 99.374431 | 99.374431 |
| 掉血 | 7 | 7 | 7 |
| 漏墙像素 | 8569 | 8453 | 8453 |
| 计入扣分误画像素 | 19793 | 20040 | 20040 |

得分小计按原SDK权重0.5×地图分＋0.2×墙覆盖分＋0.1×时间分，未将未输出的炸弹项冒称为完整总分。墙覆盖使用官方coverage字段。

## 提交原因

实际提交事件：`{"budget_exit_used": true, "selected_budget_event": {"step": 5039, "reason": "step_budget", "window": [5022, 5051], "local_inventory": 0, "team_confirmed": false, "unconfirmed_peers": [3, 4], "inventory_records": {"0": [5039, 0], "1": [2782, 0], "2": [2397, 0], "3": [2678, 1], "4": [1791, 1]}, "image_source": "group_cache", "in_window_peer_estimates": {}}, "stale_confirmation_bypassed": true, "old_confirmation_still_blocks_ordinary": {"0": true, "1": true, "2": true, "3": true, "4": true}, "drone_zero_budget_audit": [[5022, "gate", null, [3, 4], []]]}`。

各机预算出口事件：`{"0": {"step": 5039, "reason": "step_budget", "window": [5022, 5051], "local_inventory": 0, "team_confirmed": false, "unconfirmed_peers": [3, 4], "inventory_records": {"0": [5039, 0], "1": [2782, 0], "2": [2397, 0], "3": [2678, 1], "4": [1791, 1]}, "image_source": "group_cache", "in_window_peer_estimates": {}}, "1": {"step": 5039, "reason": "step_budget", "window": [5022, 5051], "local_inventory": 0, "team_confirmed": false, "unconfirmed_peers": [3, 4], "inventory_records": {"1": [5039, 0], "0": [2782, 0], "2": [2397, 0], "3": [2678, 1], "4": [1791, 1]}, "image_source": "group_cache", "in_window_peer_estimates": {}}, "2": {"step": 5039, "reason": "step_budget", "window": [5022, 5051], "local_inventory": 0, "team_confirmed": false, "unconfirmed_peers": [0, 3, 4], "inventory_records": {"2": [5039, 0], "0": [899, 2], "1": [2397, 0], "3": [1928, 1], "4": [1791, 1]}, "image_source": "group_cache", "in_window_peer_estimates": {}}, "3": {"step": 5039, "reason": "step_budget", "window": [5022, 5051], "local_inventory": 0, "team_confirmed": false, "unconfirmed_peers": [1], "inventory_records": {"3": [5039, 0], "0": [2678, 0], "1": [1928, 1], "2": [1926, 0], "4": [4763, 0]}, "image_source": "group_cache", "in_window_peer_estimates": {}}, "4": {"step": 5039, "reason": "step_budget", "window": [5022, 5051], "local_inventory": 0, "team_confirmed": false, "unconfirmed_peers": [1], "inventory_records": {"4": [5039, 0], "0": [2678, 0], "1": [1928, 1], "2": [1926, 0], "3": [4763, 0]}, "image_source": "group_cache", "in_window_peer_estimates": {}}}`。

各机预算门槛审计：`{"0": [[5022, "gate", null, [3, 4], []]], "1": [[5022, "gate", null, [3, 4], []]], "2": [[5022, "gate", null, [0, 3, 4], []]], "3": [[5022, "gate", null, [1], []]], "4": [[5022, "gate", null, [1], []]]}`。

各机最终库存认知：`{"0": {"0": [5039, 0], "1": [2782, 0], "2": [2397, 0], "3": [2678, 1], "4": [1791, 1]}, "1": {"1": [5039, 0], "0": [2782, 0], "2": [2397, 0], "3": [2678, 1], "4": [1791, 1]}, "2": {"2": [5039, 0], "0": [899, 2], "1": [2397, 0], "3": [1928, 1], "4": [1791, 1]}, "3": {"3": [5039, 0], "0": [2678, 0], "1": [1928, 1], "2": [1926, 0], "4": [4763, 0]}, "4": {"4": [5039, 0], "0": [2678, 0], "1": [1928, 1], "2": [1926, 0], "3": [4763, 0]}}`。

全部提交调用：`[{"drone": 0, "step": 5039, "walltime_seconds": 165.56951904296875, "image_sha256": "c710c5bdc5b0bc96596701e75ee28639e26176a1259ddad3b655db4c04731212"}, {"drone": 1, "step": 5039, "walltime_seconds": 165.56951904296875, "image_sha256": "9ca5fdbb7adeeaa36877d982c6ccca0595e0b92ab93db830c38e06aa976d22c6"}, {"drone": 2, "step": 5039, "walltime_seconds": 165.56951904296875, "image_sha256": "46a8f1698f463c440a460ded486084837a08ae8a08453f5238ca937142ca8b1f"}, {"drone": 3, "step": 5039, "walltime_seconds": 165.56951904296875, "image_sha256": "755e7399f01baa8631f375c5081cf735cad1cf85067c21ce7a71da7f40d4b994"}, {"drone": 4, "step": 5039, "walltime_seconds": 165.56951904296875, "image_sha256": "74a2f0604ec8fdf56cd09cd569ca676b93502f682ee970fc8a6d67d350c2b4ef"}]`。

硬兜底事件：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。

## 与历史结果的差值和证据

V16：`{"budget_minus_reference": {"score_out_of_80": -0.04388055485279807, "map_score": 0.16091613897165757, "wall_score": 0.0, "time_score": -1.2433862433862437, "placed": 0, "submission_step": 47, "final_walltime_seconds": -12.946779251098633, "total_health_lost": 0, "exploration_percent": 0.0, "missed_wall_pixels": -116, "charged_misdraw_pixels": 247}, "same_all_accepted_placements": true, "first_different_drone_step": 4992, "first_different_bomb_step": 4992, "same_selected_map": false, "score_contribution": {"map": 0.08045806948582879, "wall": 0.0, "time": -0.12433862433862437}}`。

同一步数累计耗时：`{"1001": {"reference_seconds": 23.18400740623474, "budget_seconds": 22.48377752304077, "observed_saved_seconds": 0.7002298831939697}, "2001": {"reference_seconds": 56.26166486740112, "budget_seconds": 54.101276874542236, "observed_saved_seconds": 2.1603879928588867}, "3001": {"reference_seconds": 94.11462497711182, "budget_seconds": 87.41764545440674, "observed_saved_seconds": 6.696979522705078}, "4001": {"reference_seconds": 140.59040546417236, "budget_seconds": 128.55492305755615, "observed_saved_seconds": 12.035482406616211}, "4991": {"reference_seconds": 178.5211362838745, "budget_seconds": 163.4747667312622, "observed_saved_seconds": 15.046369552612305}, "4992": {"reference_seconds": 178.5293424129486, "budget_seconds": 163.50576496124268, "observed_saved_seconds": 15.023577451705933}}`。

rowindex：`{"budget_minus_reference": {"score_out_of_80": 0.8412698412698418, "map_score": 0.0, "wall_score": 0.0, "time_score": 8.412698412698413, "placed": 0, "submission_step": -318, "final_walltime_seconds": -12.967554330825806, "total_health_lost": 0, "exploration_percent": 0.0, "missed_wall_pixels": 0, "charged_misdraw_pixels": 0}, "same_all_accepted_placements": true, "first_different_drone_step": 5039, "first_different_bomb_step": 5039, "same_selected_map": true, "score_contribution": {"map": 0.0, "wall": 0.0, "time": 0.8412698412698414}}`。

同一步数累计耗时：`{"1001": {"reference_seconds": 22.848995685577393, "budget_seconds": 22.48377752304077, "observed_saved_seconds": 0.3652181625366211}, "2001": {"reference_seconds": 54.220897912979126, "budget_seconds": 54.101276874542236, "observed_saved_seconds": 0.11962103843688965}, "3001": {"reference_seconds": 88.74705171585083, "budget_seconds": 87.41764545440674, "observed_saved_seconds": 1.3294062614440918}, "4001": {"reference_seconds": 130.2624773979187, "budget_seconds": 128.55492305755615, "observed_saved_seconds": 1.7075543403625488}, "4991": {"reference_seconds": 164.7771635055542, "budget_seconds": 163.4747667312622, "observed_saved_seconds": 1.3023967742919922}, "5021": {"reference_seconds": 166.40819668769836, "budget_seconds": 165.0974085330963, "observed_saved_seconds": 1.3107881546020508}, "5022": {"reference_seconds": 166.4339997768402, "budget_seconds": 165.12393927574158, "observed_saved_seconds": 1.3100605010986328}, "5030": {"reference_seconds": 166.62658429145813, "budget_seconds": 165.34987878799438, "observed_saved_seconds": 1.2767055034637451}, "5039": {"reference_seconds": 166.83795285224915, "budget_seconds": 165.58410477638245, "observed_saved_seconds": 1.2538480758666992}}`。

## 得分与墙钟差解释

相对V16：地图项贡献+0.080458，墙覆盖项+0.000000，时间项-0.124339，合计-0.043881。地图小幅改善尚不足补偿多47步的时间项损失。相对按行索引候选，地图/墙覆盖/图片不变，收益来自少318步，对小计贡献+0.841270。

预算开启前第5021步，本次已经比历史按行索引场次快1.310788秒；两次CPU负载和核心组不同。因此不能把最终实测12.967554秒差全部归因于预算逻辑。历史轨迹在5039步累计166.837953秒，其后到原结束仍有约11.789911秒运行，说明提前停止确实避免了一段尾部运行。

与历史按行索引回放的首次无人机及炸弹记录差异均在5039步（本次结束帧）；全部实际投放事件逐条相同。新候选采用与旧按行索引候选相同的0号4995版缓存，提交图片SHA256均为`c710c5bdc5b0bc96596701e75ee28639e26176a1259ddad3b655db4c04731212`。

## 条件与验证边界

三版相同种子、地图/特殊区、出生点、5400步/180秒、5机/10弹、评分配置、SDK封存版本均核对一致。新观察器仅在评分结束后导出预算事件和审计，运行阶段AST与历史观察器一致。候选源文件运行前后SHA通过；正式V16和原按行索引归档未改。
每版的CPU占用均值、load1均值、CPU池其他任务估计等效核均值：`{"V16": {"cpu_busy_percent": 18.809050556683918, "load1": 79.53394594594594, "estimated_other_work_cpu_equivalents_in_pool": 0.42588180557676514}, "rowindex": {"cpu_busy_percent": 11.995768759842095, "load1": 39.07783783783784, "estimated_other_work_cpu_equivalents_in_pool": 0.9015165340227655}, "budget93": {"cpu_busy_percent": 22.449718613899602, "load1": 57.149883720930234, "estimated_other_work_cpu_equivalents_in_pool": 5.535974411516629}}`。
本轮为单次新增对照历史结果；CPU核心组与背景负载不同。墙钟差为实测，不能全部归因于算法或预算出口。预算提交会结束比赛，因此提交后的轨迹不能再与未结束的历史长轨迹当作相同工作量比较。
候选SHA256：`0ed2e45090a6a8104c0a3bf92d8ac79382a7891eccb978ffaba8a72a2b06a449`。完整预算出口来源及56项反例证据见先前提交53a6e679e8f4d4faacf67ef8ca915f9ebfa9e473。

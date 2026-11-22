# 93%预算交图候选：Map08、Map09种子615各一次

本轮只新增当前冻结候选Map08、Map09各一场，共两场红队。未重跑已有V16或按行索引结果，未新增其他地图或蓝队比赛，未改算法、导航、拟合、投放或依赖。V16继续作为比赛提交基线。

## Map08：结束路径与结果

本场SDK采用1号机第3452步提交，结束路径`ordinary`。预算窗口是否进入：False；是否使用预算出口：False；是否在5022步之前结束：True。实投10枚，结束时各机真实库存：`{"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}`。
提交调用共1次，同帧多机提交：False。调用清单：`[{"drone": 1, "step": 3452, "walltime_seconds": 137.9924759864807, "image_sha256": "a2b13dd8af95eb2165a021c903a0885ec0abd73641c09739deed482d008169c4"}]`。

相对V16：步数+0，得分小计+0.000000，地图分+0.000000，墙覆盖分+0.000000，最终墙钟+11.018139秒；提交图片相同=True，全部投放事件相同=True。
相对rowindex：步数+0，得分小计+0.000000，地图分+0.000000，墙覆盖分+0.000000，最终墙钟+15.129866秒；提交图片相同=True，全部投放事件相同=True。
本场结束前尚未进入5022—5051预算窗口，因此没有通过新预算策略提前截断比赛。若与历史结果仍有差异，应检查已有墙钟收尾与缓存规则、负载和触发步数，不能把这些差异直接归为预算提前交图。

### Map08详细证据

本图只新增当前冻结候选一场红队比赛；未重跑V16或按行索引基线。两图任务仅允许Map08、Map09各一场，V16继续作为比赛提交基线。

## 三版本结果

| 指标 | 已有V16 | 已有按行索引 | 本轮93%预算候选 |
|---|---:|---:|---:|
| 交图者 | 1 | 1 | 1 |
| 交图步数 | 3452 | 3452 | 3452 |
| 提交调用次数 | 1 | 1 | 1 |
| 得分小计/80 | 52.641344 | 52.641344 | 52.641344 |
| 地图分 | 77.189215 | 77.189215 | 77.189215 |
| 墙覆盖分 | 44.466486 | 44.466486 | 44.466486 |
| 时间分 | 51.534392 | 51.534392 | 51.534392 |
| 实投数 | 10 | 10 | 10 |
| 最终墙钟/秒 | 127.056048 | 122.944320 | 138.074186 |
| 交图指令墙钟/秒 | 126.978304 | 122.868762 | 137.992476 |
| 探索率/% | 98.018148 | 98.018148 | 98.018148 |
| 掉血 | 16 | 16 | 16 |
| 漏墙像素 | 17507 | 17507 | 17507 |
| 计入扣分误画像素 | 49559 | 49559 | 49559 |

得分小计按SDK原权重0.5×地图分＋0.2×墙覆盖分＋0.1×时间分；未将未输出的炸弹项冒称为完整总分。墙覆盖使用官方coverage字段。

## 是否提前结束及提交协调

结束路径与预算状态：`{"budget_exit_used": false, "selected_budget_event": null, "stale_confirmation_bypassed": false, "old_confirmation_still_blocks_ordinary": {"0": false, "1": false, "2": true, "3": false, "4": false}, "drone_zero_budget_audit": [], "budget_window_entered": false, "actual_final_inventory": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}, "all_initial_bombs_placed": true, "selected_submission_before_budget_window": true, "hard_deadline_event": null, "submission_calls": 1, "simultaneous_submission": false, "ending_path": "ordinary"}`。

各版全部提交调用：`{"V16": [{"drone": 1, "step": 3452, "walltime_seconds": 126.97830438613892, "image_sha256": "a2b13dd8af95eb2165a021c903a0885ec0abd73641c09739deed482d008169c4"}], "rowindex": [{"drone": 1, "step": 3452, "walltime_seconds": 122.86876153945923, "image_sha256": "a2b13dd8af95eb2165a021c903a0885ec0abd73641c09739deed482d008169c4"}], "budget93": [{"drone": 1, "step": 3452, "walltime_seconds": 137.9924759864807, "image_sha256": "a2b13dd8af95eb2165a021c903a0885ec0abd73641c09739deed482d008169c4"}]}`。

各机预算门槛审计：`{"0": [], "1": [], "2": [], "3": [], "4": []}`。

各机预算出口事件：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。

各机硬兜底事件：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。

各机最终库存认知：`{"0": {"0": [3452, 0], "1": [3015, 0], "2": [2420, 0], "3": [3450, 0], "4": [3014, 0]}, "1": {"1": [3452, 0], "0": [3013, 0], "2": [2420, 0], "3": [3015, 0], "4": [3450, 0]}, "2": {"2": [3452, 0], "0": [2419, 0], "1": [2009, 0], "3": [2420, 0], "4": [2007, 1]}, "3": {"3": [3452, 0], "0": [3450, 0], "1": [3015, 0], "2": [2420, 0], "4": [3014, 0]}, "4": {"4": [3452, 0], "0": [3013, 0], "1": [3450, 0], "2": [2420, 0], "3": [3015, 0]}}`。

## 与历史结果的差值

V16：`{"budget_minus_reference": {"score_out_of_80": 0.0, "map_score": 0.0, "wall_score": 0.0, "time_score": 0.0, "placed": 0, "submission_step": 0, "final_walltime_seconds": 11.018138647079468, "total_health_lost": 0, "exploration_percent": 0.0, "missed_wall_pixels": 0, "charged_misdraw_pixels": 0}, "same_all_accepted_placements": true, "first_different_drone_step": null, "first_different_bomb_step": null, "same_selected_map": true, "score_contribution": {"map": 0.0, "wall": 0.0, "time": 0.0}, "first_closeout_audit_difference_step": null}`。

同一步数累计耗时：`{"1001": {"reference_seconds": 24.274473667144775, "budget_seconds": 27.95687198638916, "observed_saved_seconds": -3.6823983192443848}, "2001": {"reference_seconds": 57.22914004325867, "budget_seconds": 64.3962230682373, "observed_saved_seconds": -7.167083024978638}, "3001": {"reference_seconds": 93.72781538963318, "budget_seconds": 104.50564575195312, "observed_saved_seconds": -10.777830362319946}, "3240": {"reference_seconds": 105.9278256893158, "budget_seconds": 117.40844893455505, "observed_saved_seconds": -11.480623245239258}, "3444": {"reference_seconds": 126.78990888595581, "budget_seconds": 137.80006742477417, "observed_saved_seconds": -11.01015853881836}, "3452": {"reference_seconds": 126.99832963943481, "budget_seconds": 138.01065874099731, "observed_saved_seconds": -11.0123291015625}}`。

末弹收尾审计：`{"reference": {"0": [], "1": [], "2": [], "3": [], "4": []}, "budget93": {"0": [], "1": [], "2": [], "3": [], "4": []}}`。

rowindex：`{"budget_minus_reference": {"score_out_of_80": 0.0, "map_score": 0.0, "wall_score": 0.0, "time_score": 0.0, "placed": 0, "submission_step": 0, "final_walltime_seconds": 15.129865884780884, "total_health_lost": 0, "exploration_percent": 0.0, "missed_wall_pixels": 0, "charged_misdraw_pixels": 0}, "same_all_accepted_placements": true, "first_different_drone_step": null, "first_different_bomb_step": null, "same_selected_map": true, "score_contribution": {"map": 0.0, "wall": 0.0, "time": 0.0}, "first_closeout_audit_difference_step": null}`。

同一步数累计耗时：`{"1001": {"reference_seconds": 23.94310426712036, "budget_seconds": 27.95687198638916, "observed_saved_seconds": -4.013767719268799}, "2001": {"reference_seconds": 56.17591214179993, "budget_seconds": 64.3962230682373, "observed_saved_seconds": -8.220310926437378}, "3001": {"reference_seconds": 93.25037360191345, "budget_seconds": 104.50564575195312, "observed_saved_seconds": -11.255272150039673}, "3240": {"reference_seconds": 104.4247453212738, "budget_seconds": 117.40844893455505, "observed_saved_seconds": -12.98370361328125}, "3444": {"reference_seconds": 122.6840169429779, "budget_seconds": 137.80006742477417, "observed_saved_seconds": -15.116050481796265}, "3452": {"reference_seconds": 122.88857340812683, "budget_seconds": 138.01065874099731, "observed_saved_seconds": -15.122085332870483}}`。

末弹收尾审计：`{"reference": {"0": [], "1": [], "2": [], "3": [], "4": []}, "budget93": {"0": [], "1": [], "2": [], "3": [], "4": []}}`。

## 条件和证据边界

三版相同种子、地图/特殊区、出生点、5400步/180秒、5机/10弹、评分配置、SDK封存版本均核对一致。观察器在评分后导出预算状态，运行阶段AST与历史观察器一致。新算法归档与已通过56项反例及完成Map06的候选逐字节一致，运行前后全部源文件SHA通过。
CPU占用均值、load1均值、CPU池其他任务估计等效核均值：`{"V16": {"cpu_busy_percent": 13.768636243660104, "load1": 33.01253731343284, "estimated_other_work_cpu_equivalents_in_pool": 0.46199527986252337}, "rowindex": {"cpu_busy_percent": 35.733513516059936, "load1": 116.10561538461539, "estimated_other_work_cpu_equivalents_in_pool": 5.594210564340134}, "budget93": {"cpu_busy_percent": 41.08654320866985, "load1": 125.12219178082192, "estimated_other_work_cpu_equivalents_in_pool": 3.717693889438137}}`。
本轮为单次新增对照历史场次，核心组和后台负载不同，墙钟差不能全部归因于算法或预算出口。原算法包含按剩余墙钟触发的收尾及缓存规则，未进入预算窗口时也可能因墙钟触发步数不同而产生轨迹或落点差异；需结合以上预算状态、末弹审计及投放事件分析。
候选SHA256：`0ed2e45090a6a8104c0a3bf92d8ac79382a7891eccb978ffaba8a72a2b06a449`。

## Map09：结束路径与结果

本场SDK采用0号机第3990步提交，结束路径`hard_walltime`。预算窗口是否进入：False；是否使用预算出口：False；是否在5022步之前结束：True。实投10枚，结束时各机真实库存：`{"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}`。
提交调用共5次，同帧多机提交：True。调用清单：`[{"drone": 0, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "98fb7283be9183678fc3b36128754f4b64ba7b88a264d4dea224e4071c1022bb"}, {"drone": 1, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "029d7e927ab620b508fa186da4c9236c31fd35e6fb4547da7d368a6cd0ffd5d3"}, {"drone": 2, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "42aca92f8384d48cc05331d7bf838b6a8d4e381e9260d2460acd0dcedeeada9c"}, {"drone": 3, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "78ca621a511c24be9366470a7e78ae9c26145a84793c0b9f1e6c48c858a56cd2"}, {"drone": 4, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "63e1f3dcb6094401f4b7e563a11d38e0b845b111464f7248ec2f572839693f60"}]`。

相对V16：步数-907，得分小计-4.798206，地图分-10.715274，墙覆盖分-9.200198，最终墙钟+0.008114秒；提交图片相同=False，全部投放事件相同=False。
相对rowindex：步数-1006，得分小计-5.698468，地图分-14.623477，墙覆盖分-5.240526，最终墙钟+0.023464秒；提交图片相同=False，全部投放事件相同=False。
本场结束前尚未进入5022—5051预算窗口，因此没有通过新预算策略提前截断比赛。若与历史结果仍有差异，应检查已有墙钟收尾与缓存规则、负载和触发步数，不能把这些差异直接归为预算提前交图。

本场明显退分：相对已有按行索引候选，小计下降5.698468，地图分下降14.623477，墙覆盖下降5.240526。原墙钟兜底在178.519秒左右、第3990步触发；该步数尚早于新窗口，全部预算事件和审计为空。
进一步核对：1号机在3503步进入原末弹收尾，3520步实际放下末弹、3521步确认；历史V16为4343步实投，历史按行索引为4561步实投。前9次接受投放记录完全相同，最后一枚实际位置改变：`{"rowindex": {"drone": 1, "step": 4561, "event": "sdk_placement", "accepted": true, "physical_xy": [-12.38859399977959, 211.58627413954864]}, "budget93": {"drone": 1, "step": 3520, "event": "sdk_placement", "accepted": true, "physical_xy": [-188.359868341957, -437.27888072496694]}}`。
本场进入收尾时已用约155.034秒，剩24.966秒，满足原有剩余25秒及停滞条件。0号最后采用3870版缓存，历史V16和按行索引分别采用4590、4950版。它们直接说明原墙钟流程在更小步数介入，末弹位置、可运行步数和缓存更新机会均改变；不能把地图变化直接解释为新预算出口截断。
本轮整机CPU占用均值54.536%，历史两场约11.49%；所选CPU池其他任务估计等效核均值15.706，历史均低于0.04。负载差构成明显混杂，本次无法隔离代码自身开销与外部负载各自的影响，也不能证明候选在同负载下退化或无退化。
收尾与缓存证据：`{"V16": {"drone_one_closeout_entry_step": 4341, "cached_walltime_from_previous_frame": 155.78999948501587, "remaining_walltime": 24.21000051498413, "last_confirmation_step": 4344, "selected_drone_zero_cache": {"owner": 5, "version": 4590, "digest": "87388a174eec6a7a700f9e422751c1141d84ced67d1a5d18970ae82dcd8e1b8b", "precision": 0.907753184122666, "recall": 0.975934065934066, "score": 0.9406097066471591}}, "rowindex": {"drone_one_closeout_entry_step": 4559, "cached_walltime_from_previous_frame": 158.26429986953735, "remaining_walltime": 21.735700130462646, "last_confirmation_step": 4562, "selected_drone_zero_cache": {"owner": 5, "version": 4950, "digest": "ffa846ed19e00e1ef9213449f9fba871728cd6b3ef951e06683933a83e79cf77", "precision": 0.9070045899022151, "recall": 0.97354541825135, "score": 0.9390977735276901}}, "budget93": {"drone_one_closeout_entry_step": 3503, "cached_walltime_from_previous_frame": 155.0344066619873, "remaining_walltime": 24.965593338012695, "last_confirmation_step": 3521, "selected_drone_zero_cache": {"owner": 5, "version": 3870, "digest": "345fa6fd2924ed6f8b81afe92a7d88b6a1ecda4f0650df01c2b2fcc6b3e879e0", "precision": 0.8609669629553511, "recall": 0.9678088339988238, "score": 0.9112669075313734}}}`。

### Map09详细证据

本图只新增当前冻结候选一场红队比赛；未重跑V16或按行索引基线。两图任务仅允许Map08、Map09各一场，V16继续作为比赛提交基线。

## 三版本结果

| 指标 | 已有V16 | 已有按行索引 | 本轮93%预算候选 |
|---|---:|---:|---:|
| 交图者 | 0 | 0 | 0 |
| 交图步数 | 4897 | 4996 | 3990 |
| 提交调用次数 | 5 | 5 | 5 |
| 得分小计/80 | 42.772789 | 43.673051 | 37.974583 |
| 地图分 | 66.030348 | 69.938551 | 55.315074 |
| 墙覆盖分 | 42.134636 | 38.174965 | 32.934439 |
| 时间分 | 13.306878 | 10.687831 | 37.301587 |
| 实投数 | 10 | 10 | 10 |
| 最终墙钟/秒 | 178.603230 | 178.587880 | 178.611344 |
| 交图指令墙钟/秒 | 178.516066 | 178.500719 | 178.519376 |
| 探索率/% | 92.022125 | 92.023708 | 91.140944 |
| 掉血 | 5 | 4 | 5 |
| 漏墙像素 | 31264 | 27061 | 44677 |
| 计入扣分误画像素 | 63036 | 62970 | 48238 |

得分小计按SDK原权重0.5×地图分＋0.2×墙覆盖分＋0.1×时间分；未将未输出的炸弹项冒称为完整总分。墙覆盖使用官方coverage字段。

## 是否提前结束及提交协调

结束路径与预算状态：`{"budget_exit_used": false, "selected_budget_event": null, "stale_confirmation_bypassed": false, "old_confirmation_still_blocks_ordinary": {"0": true, "1": true, "2": true, "3": true, "4": true}, "drone_zero_budget_audit": [], "budget_window_entered": false, "actual_final_inventory": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}, "all_initial_bombs_placed": true, "selected_submission_before_budget_window": true, "hard_deadline_event": {"step": 3990, "fallback": "walltime", "remaining_steps": 1410, "remaining_walltime": 1.4806244373321533, "local_inventory": 0, "team_confirmed": false, "backup_step": 3870}, "submission_calls": 5, "simultaneous_submission": true, "ending_path": "hard_walltime"}`。

各版全部提交调用：`{"V16": [{"drone": 0, "step": 4897, "walltime_seconds": 178.51606559753418, "image_sha256": "082dc9e2f5f479fdb343c7da0feea0b9f3dea2f56c26d22d155e769efea17807"}, {"drone": 1, "step": 4897, "walltime_seconds": 178.51606559753418, "image_sha256": "21560e6ae94d897eb08bc8a425fcd748a8db7f31b7272b144fa5f2e25f1ac8fd"}, {"drone": 2, "step": 4897, "walltime_seconds": 178.51606559753418, "image_sha256": "0545f1d1449264561dba5cb028d4411d6ef13cc4494c6f33bcd6d1b22f196ae3"}, {"drone": 3, "step": 4897, "walltime_seconds": 178.51606559753418, "image_sha256": "2c8763df02cb5cb70056352809f8493e4a9fdef7b6e1bcc6a212312f8f22295d"}, {"drone": 4, "step": 4897, "walltime_seconds": 178.51606559753418, "image_sha256": "5f3e2b454ac6a28bb1bd54ac0efcf1ee39a76bc1616829aabff022b9d5eac833"}], "rowindex": [{"drone": 0, "step": 4996, "walltime_seconds": 178.50071907043457, "image_sha256": "2cf434daf12dff06fd49b68a4014fd324f8a7bd206e030415b83d35f355f5e73"}, {"drone": 1, "step": 4996, "walltime_seconds": 178.50071907043457, "image_sha256": "47d87cee0a98b7aa63e0606fb296ba21caf8b36b8e54517fe787f64c74342b21"}, {"drone": 2, "step": 4996, "walltime_seconds": 178.50071907043457, "image_sha256": "1efe2e9f6b9fe3ac357bbea2a04db50241f56c32e480660ea11b43f353cbf461"}, {"drone": 3, "step": 4996, "walltime_seconds": 178.50071907043457, "image_sha256": "78ca621a511c24be9366470a7e78ae9c26145a84793c0b9f1e6c48c858a56cd2"}, {"drone": 4, "step": 4996, "walltime_seconds": 178.50071907043457, "image_sha256": "811318fe5302505d4f397f255442d1f392f9a68c6373f902ed76a66404633a8c"}], "budget93": [{"drone": 0, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "98fb7283be9183678fc3b36128754f4b64ba7b88a264d4dea224e4071c1022bb"}, {"drone": 1, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "029d7e927ab620b508fa186da4c9236c31fd35e6fb4547da7d368a6cd0ffd5d3"}, {"drone": 2, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "42aca92f8384d48cc05331d7bf838b6a8d4e381e9260d2460acd0dcedeeada9c"}, {"drone": 3, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "78ca621a511c24be9366470a7e78ae9c26145a84793c0b9f1e6c48c858a56cd2"}, {"drone": 4, "step": 3990, "walltime_seconds": 178.51937556266785, "image_sha256": "63e1f3dcb6094401f4b7e563a11d38e0b845b111464f7248ec2f572839693f60"}]}`。

各机预算门槛审计：`{"0": [], "1": [], "2": [], "3": [], "4": []}`。

各机预算出口事件：`{"0": null, "1": null, "2": null, "3": null, "4": null}`。

各机硬兜底事件：`{"0": {"step": 3990, "fallback": "walltime", "remaining_steps": 1410, "remaining_walltime": 1.4806244373321533, "local_inventory": 0, "team_confirmed": false, "backup_step": 3870}, "1": {"step": 3990, "fallback": "walltime", "remaining_steps": 1410, "remaining_walltime": 1.4806244373321533, "local_inventory": 0, "team_confirmed": false, "backup_step": 3916}, "2": {"step": 3990, "fallback": "walltime", "remaining_steps": 1410, "remaining_walltime": 1.4806244373321533, "local_inventory": 0, "team_confirmed": false, "backup_step": 3872}, "3": {"step": 3990, "fallback": "walltime", "remaining_steps": 1410, "remaining_walltime": 1.4806244373321533, "local_inventory": 0, "team_confirmed": false, "backup_step": 3648}, "4": {"step": 3990, "fallback": "walltime", "remaining_steps": 1410, "remaining_walltime": 1.4806244373321533, "local_inventory": 0, "team_confirmed": false, "backup_step": 3829}}`。

各机最终库存认知：`{"0": {"0": [3990, 0], "1": [599, 2], "2": [1898, 1], "3": [2645, 1], "4": [1777, 1]}, "1": {"1": [3990, 0], "0": [1898, 1], "2": [2832, 0], "3": [1505, 2], "4": [1777, 1]}, "2": {"2": [3990, 0], "0": [2645, 0], "1": [2832, 1], "3": [2804, 1], "4": [2974, 0]}, "3": {"3": [3990, 0], "0": [2645, 0], "1": [599, 2], "2": [1898, 1], "4": [2804, 0]}, "4": {"4": [3990, 0], "0": [2645, 0], "1": [2832, 1], "2": [2974, 0], "3": [2804, 1]}}`。

## 与历史结果的差值

V16：`{"budget_minus_reference": {"score_out_of_80": -4.798205574534009, "map_score": -10.715273900965855, "wall_score": -9.20019761760993, "time_score": 23.994708994709, "placed": 0, "submission_step": -907, "final_walltime_seconds": 0.008113861083984375, "total_health_lost": 0, "exploration_percent": -0.8811804570343185, "missed_wall_pixels": 13413, "charged_misdraw_pixels": -14798}, "same_all_accepted_placements": false, "first_different_drone_step": 3504, "first_different_bomb_step": 3520, "same_selected_map": false, "score_contribution": {"map": -5.357636950482927, "wall": -1.8400395235219862, "time": 2.3994708994709}, "first_closeout_audit_difference_step": 3503}`。

同一步数累计耗时：`{"1001": {"reference_seconds": 25.84657382965088, "budget_seconds": 36.74982166290283, "observed_saved_seconds": -10.903247833251953}, "2001": {"reference_seconds": 60.62709069252014, "budget_seconds": 80.09983229637146, "observed_saved_seconds": -19.47274160385132}, "3001": {"reference_seconds": 94.85845899581909, "budget_seconds": 124.98703932762146, "observed_saved_seconds": -30.128580331802368}, "3240": {"reference_seconds": 105.39983201026917, "budget_seconds": 139.6763472557068, "observed_saved_seconds": -34.27651524543762}, "3444": {"reference_seconds": 116.68880558013916, "budget_seconds": 152.15854120254517, "observed_saved_seconds": -35.469735622406006}, "3452": {"reference_seconds": 116.88735270500183, "budget_seconds": 152.42250800132751, "observed_saved_seconds": -35.535155296325684}, "3990": {"reference_seconds": 138.5535490512848, "budget_seconds": 178.53295350074768, "observed_saved_seconds": -39.97940444946289}}`。

末弹收尾审计：`{"reference": {"0": [], "1": [[4341, "stall_enter", [-272.1413872319977, 268.3581467875526]], [4341, "direction_picked", 1.6867, 36.07, 0], [4342, "separation_open", 733.03], [4343, "pulse_sent", [-274.1798221504944, 268.07089105436467]], [4344, "drop_confirmed", 0]], "2": [], "3": [], "4": []}, "budget93": {"0": [], "1": [[3503, "stall_enter", [-187.52514217641985, -454.47244062446885]], [3503, "direction_picked", 1.5975, Infinity, 0], [3519, "separation_open", 26.15], [3520, "pulse_sent", [-189.42486646733056, -431.5827927535565]], [3521, "drop_confirmed", 0]], "2": [], "3": [], "4": []}}`。

rowindex：`{"budget_minus_reference": {"score_out_of_80": -5.698467864820309, "map_score": -14.623476553041513, "wall_score": -5.240526248376064, "time_score": 26.613756613756614, "placed": 0, "submission_step": -1006, "final_walltime_seconds": 0.023464202880859375, "total_health_lost": 1, "exploration_percent": -0.8827633106262169, "missed_wall_pixels": 17616, "charged_misdraw_pixels": -14732}, "same_all_accepted_placements": false, "first_different_drone_step": 3504, "first_different_bomb_step": 3520, "same_selected_map": false, "score_contribution": {"map": -7.311738276520757, "wall": -1.0481052496752128, "time": 2.6613756613756614}, "first_closeout_audit_difference_step": 3503}`。

同一步数累计耗时：`{"1001": {"reference_seconds": 25.670828580856323, "budget_seconds": 36.74982166290283, "observed_saved_seconds": -11.078993082046509}, "2001": {"reference_seconds": 59.49770641326904, "budget_seconds": 80.09983229637146, "observed_saved_seconds": -20.602125883102417}, "3001": {"reference_seconds": 92.86470079421997, "budget_seconds": 124.98703932762146, "observed_saved_seconds": -32.12233853340149}, "3240": {"reference_seconds": 102.93358445167542, "budget_seconds": 139.6763472557068, "observed_saved_seconds": -36.74276280403137}, "3444": {"reference_seconds": 113.23944091796875, "budget_seconds": 152.15854120254517, "observed_saved_seconds": -38.919100284576416}, "3452": {"reference_seconds": 113.43571877479553, "budget_seconds": 152.42250800132751, "observed_saved_seconds": -38.98678922653198}, "3990": {"reference_seconds": 133.82224416732788, "budget_seconds": 178.53295350074768, "observed_saved_seconds": -44.7107093334198}}`。

末弹收尾审计：`{"reference": {"0": [], "1": [[4559, "stall_enter", [-27.98697119035146, 212.10047413578138]], [4559, "direction_picked", 1.076, 120.91, 0], [4560, "separation_open", 692.29], [4561, "pulse_sent", [-28.42144365443691, 216.4472070092638]], [4562, "drop_confirmed", 0]], "2": [], "3": [], "4": []}, "budget93": {"0": [], "1": [[3503, "stall_enter", [-187.52514217641985, -454.47244062446885]], [3503, "direction_picked", 1.5975, Infinity, 0], [3519, "separation_open", 26.15], [3520, "pulse_sent", [-189.42486646733056, -431.5827927535565]], [3521, "drop_confirmed", 0]], "2": [], "3": [], "4": []}}`。

## 条件和证据边界

三版相同种子、地图/特殊区、出生点、5400步/180秒、5机/10弹、评分配置、SDK封存版本均核对一致。观察器在评分后导出预算状态，运行阶段AST与历史观察器一致。新算法归档与已通过56项反例及完成Map06的候选逐字节一致，运行前后全部源文件SHA通过。
CPU占用均值、load1均值、CPU池其他任务估计等效核均值：`{"V16": {"cpu_busy_percent": 11.482079332792857, "load1": 29.069891891891892, "estimated_other_work_cpu_equivalents_in_pool": 0.03828442617868703}, "rowindex": {"cpu_busy_percent": 11.489524812528778, "load1": 29.391027027027025, "estimated_other_work_cpu_equivalents_in_pool": 0.023837550597551653}, "budget93": {"cpu_busy_percent": 54.536197870830094, "load1": 180.33670212765958, "estimated_other_work_cpu_equivalents_in_pool": 15.705853651990871}}`。
本轮为单次新增对照历史场次，核心组和后台负载不同，墙钟差不能全部归因于算法或预算出口。原算法包含按剩余墙钟触发的收尾及缓存规则，未进入预算窗口时也可能因墙钟触发步数不同而产生轨迹或落点差异；需结合以上预算状态、末弹审计及投放事件分析。
候选SHA256：`0ed2e45090a6a8104c0a3bf92d8ac79382a7891eccb978ffaba8a72a2b06a449`。

## 汇总边界

Map08先选定当时空闲的16个物理核。Map09开始前无法找到16个空闲物理核，停止的仅是尚未开局的选核等待进程；没有中断或重跑比赛。随后复用本轮Map08同一组核心带干扰运行，实时入场负载见Map09/ADMISSION.json，变更记录见MAP09_ADMISSION_CHANGE.json。Map09的AFFINITY_SELECTION.json继承Map08的原选核拓扑和预筛选数据，不可当作Map09空闲证明。算法、比赛参数、线程配置均未改变。
历史参考场次的核心组和后台负载与本轮不同。已记录每场CPU占用、CPU亲和性、进程及运行队列等待；不声称整机低负载或严格相同负载。单次最终墙钟差不等于纯算法耗时差。
比赛参数、出生点、配置、SDK版本均已核对；原始比赛产物和额外导出均按SHA256核验，算法源文件运行前后校验通过。完整候选源码及56项反例见提交53a6e679e8f4d4faacf67ef8ca915f9ebfa9e473。

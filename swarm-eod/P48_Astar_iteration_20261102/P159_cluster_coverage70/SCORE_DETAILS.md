# 固定6枚、覆盖保护70%：真实SDK小测

首个物理运行已完成，但导出JSON时NumPy int64计数不能序列化，原FIRST_ERROR和原日志保留。仅用不改控制器/fixture/seed的记录重放补分项；原始投放/发出的计划/排除耗时的模型日志必须一致。没有保存的首轮全部逐帧输出不冒称已逐帧核验；不把重放当新增性能样本或资格补救。

状态：`RECORDED_AUTHOR_MECHANISM_REJECTED`；严格2R圈实际最多 **3枚**，投放10/10，结束498步。此为作者场景，不是官方五图；没有BLUE，布局难度与完整红分未评估。

|指标|原P48 A*|P159覆盖70%|变化|
|---|---:|---:|---:|
|地图原始分|98.503722|98.148971|-0.354752|
|地图×0.5|49.251861|49.074485|-0.177376|
|墙体原始分|76.006079|67.884498|-8.121581|
|墙体×0.2|15.201216|13.576900|-1.624316|
|时间原始分|100.000000|100.000000|0.000000|
|时间×0.1|10.000000|10.000000|0.000000|
|可控加权小计|74.453077|72.651385|-1.801692|
|布局难度贡献/完整红分|未评估|未评估|无BLUE，不能填0|

原P48实际10枚、508步、健康[50, 50, 50, 50, 50]；新方案10枚、498步、健康[50, 50, 50, 50, 50]。实际loop秒20.4892→21.9575，与作者合成.05秒每步输入分开报告。

冻结门槛逐项：

- actual_cluster6: False
- all10: True
- map_loss_at_most_half_pp: True
- wall_retained70: True
- time_nonregress: True
- no_added_total_damage: True
- actual_loop_under90: True
- available_original_logs_match: True

实际执行链：264步接受7枚圈内目标、预测联合覆盖84.3862%；288步重规划未找到满足条件的内角，退回原方案，同圈目标降为4个；后续继续变化，最终SDK实际弹药中心严格2R内3枚。这里没有把+12px到达容差的4枚混算为严格集中。曾用投放确认时无人机位置估算2枚，已更正；无人机位置不是最终弹药中心。

该结果表明70%已经允许初始方案接受，但角落目标未被保持。no_two_measured_corner_surfaces是几何候选入口的总括原因，尚需区分Harris重新识别、自由区/禁区与旧anchor有效性，不能断言只因角点噪声。下一步先补几何证书/旧计划失效原因，不继续降低覆盖门槛或直接跑五图。

70%只调整布局预测覆盖门槛与一致的消息校验；固定6、原地图/运动/间距/路线/SDK/依赖未改，P157旧90%失败不重写。确认实际集中、覆盖/地图/时间/健康是否通过后，才决定正式测试。

原P48墙体：内部命中4961，边界命中2581，边界权重0.5，加权命中6251.5，固定10枚SDK参考8225.0。

原P48地图细则：{"s_time": 1.0, "s_map": 0.9850372226879289, "credit": 1.0, "penalty": 0.014962777312071117, "wall_pixels": 24045, "wall_hits": 24045, "wall_hit_rate": 1.0, "wall_available": true, "interior_pixels": 6, "interior_hits": 6, "interior_hit_rate": 1.0, "interior_available": true, "predicted_pixels": 71936, "exact_pixels": 24051, "dead_zone_pixels": 41197, "charged_pixels": 6688, "capped_pixels": 796, "total_charge": 1798.89990234375, "truth_pixels": 24051, "surface_pixels": 24045}

P159墙体：内部命中4307，边界命中2553，边界权重0.5，加权命中5583.5，固定10枚SDK参考8225.0。

P159地图细则：{"s_time": 1.0, "s_map": 0.9814897076120295, "credit": 1.0, "penalty": 0.018510292387970473, "wall_pixels": 24045, "wall_hits": 24045, "wall_hit_rate": 1.0, "wall_available": true, "interior_pixels": 6, "interior_hits": 6, "interior_hit_rate": 1.0, "interior_available": true, "predicted_pixels": 73126, "exact_pixels": 24051, "dead_zone_pixels": 41913, "charged_pixels": 7162, "capped_pixels": 1266, "total_charge": 2225.39990234375, "truth_pixels": 24051, "surface_pixels": 24045}

墙体爆炸区域按并集计算，重叠不重复得分；SDK参考为确定性贪心参考，不是严格全局最优。时间上限2000步，<=1000步满分。真值仅所有控制和提交冻结后用于作者评价，没有提供给控制器。

# P48 A* 持续分析与规则验证（2026-11-02）

工作底本已切换到冻结P48_ASTAR；Goal和automation90已恢复ACTIVE。一次一条规则，先分析、反例及真实SDK小闭环，有希望才正式单图和同条件五图。地图精度优先，最终以完整五图红队平均分评价，不以路线更直或作者场景分数代替。

[已完成的A*五图与冻结源码](https://github.com/quanliangwen/1/tree/7820d3deac9b063bf6ca470c371e33662a428012/swarm-eod/P48_Astar_five_20261102)：74.2558833655，50/50，双方无墙钟超时；旧P48留存72.6026760546。自然随机不同，仅观察差异。

## 本轮已完成

- P141：5份已首审的own RED日志和公开评分复盘，零新比赛。Map01末投和提交同在1194步；五图误绘扣分均大于漏墙项。Map04满投10枚但覆盖65.8717，不能解释为少投，也不能把最终图当规划时输入。
- P142：诊断状态 `STOP_FIRST_ORIGINAL_SDK_CHECK`。最多两臂同一作者场景，OFF/ON只区别cProfile；完整任务快照是只读观察。这里不运行蓝队，不复现官方Map04，不构成新的完整红队成绩。
- P142实际在OFF首臂健康检查失败（344步两机各掉1健康），ON未启动；原错误和门槛保留。P143仅补原失败的实际感知/驱动证据，要求全部动作/地图/健康与原失败完全一致，不重试恢复性能资格，不计新成绩。
- P143全部779帧与原失败一致，实际感知说明侧向交会进入目标方向管道较晚，已经刹车时仍有明显惯性速度。P144进一步用已有输入否决“仅加自身速度方向的同宽管道就能补上缺口”，没有为这个不成立的简单改动开比赛。
- 正式V09提交包保持；没有发布新的比赛包，没有使用Gurobi或改SDK/依赖/正式门槛。

目标、依据、小测协议、脚本、结果与限制见各子目录。实际运行的详细逐帧输入输出保留在必要临时工作区和服务器证据链，不把临时存储当用户下载或永久备份。后续分析按目标自主接续，用户停止立即停后续。

## 工程原文

[Nav2 Smac2D](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/planners_plugins/smac/smac_2d/configuring_smac_2d/)提供代价感知的全向A*工程参考；[Nav2重规划条件](https://docs.nav2.org/rolling/getting_started/nav2_behavior_trees/trees/nav_to_pose_with_consistent_replanning_and_if_path_becomes_invalid/)区分目标变化、路径失效和周期触发。只借工程原则，不搬阈值、清图或重试，不将文献当游戏提分证据。

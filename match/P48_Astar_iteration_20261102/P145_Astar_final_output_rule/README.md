# P145：A*底本上的单条最终输出规则

状态：`PASS_ASTARA_FINAL_OUTPUT_MECHANISM`。作者场景实际地图变化：+1.98810136个百分点。

这次适配历史P125的输出一致性规则；helper和wrapper字节不变，仅接入冻结P48_ASTAR入口。不是新算法机制，也不继承旧原生试验的性能资格。所有A*、探索、地图更新、任务、布点、运动和依赖保持。

父本作者场景的两机各掉1点健康被明确保留，本试验不宣称修复或通过健康安全资格。性能比较要求所有原动作、地图、库存、目标和健康与保留父本完全一致，只有实际提交图可改变；五机的地图与真实墙面credit也必须不退。

完整门槛、首测结果及结论见JSON/TXT。零新正式地图、零五图，不是比赛提交包。`source_delta.json`保存三份改动的精确原始字节及SHA；`changes.diff`供阅读；基准研究源码归档有固定SHA和GitHub链接。没有Gurobi、环境覆盖或官网上传。

[OctoMap原始API说明](https://octomap.github.io/octomap/doc/classoctomap_1_1OccupancyOcTreeBase.html)仅提供命中/空闲证据分离的工程参考，本规则不实现OctoMap或贝叶斯占据。实际分数证据才用于决定是否继续。

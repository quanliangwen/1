# CCMCKP CDF-DRO 稳定性改进 S1

基于用户提供的冻结源码包改进。原服务器工程未覆盖；独立目录为 `/home/quanliangwen/work/cdf_stability_20261109/candidate`。

增加多个均值/方差初始候选、CDF 局部线性模型（2/4/8/16 组调整）、高分辨率 CDF 快速筛选，以及 0/0.1%/0.25% 的细小成本改进档位。保留三个歧义半径和三种折半分组；MITM 引导采用 512 格最近点投影和单精度 FFT。原生验收函数、100 万次抽样、0.99 门槛及原本只缓存成功判定的行为保持不变。样本降序排序增加缓存，校验结果及随机数状态与原实现一致。

二进制子问题改用 SciPy/HiGHS，源代码不再依赖 Gurobi。当前服务器账号的默认 Gurobi 许可证已过期。

每次只读取原始样本、成本和本次状态，不读取历史解或其他运行的解。原表对应的 1,200 次实验记录及 3,660 个原始输入文件已核验。固定 S1 后，40 个算例各验证 5 次，种子 900001..900005，每次上限 600 秒；普通失败不替换。完整结果见 [RESULTS.md](RESULTS.md)。5 次结果不冒称原表的 30 次统计。

运行示例（Linux，依赖见 `source/requirements.txt`）：

```bash
python3 source/run.py --instance /path/to/APP_50_10_500_ --capacity 100 --seed 900101 --seconds 600 --out /path/to/new_run.json.gz
```

输出必须为新名称。主记录及 `.run.json` 侧记录保留向量、原生概率、实际时间及源码/输入 SHA-256。加载实例、初始化、搜索、验收及主记录写盘均计时。

CDF/DRO 分布用于候选引导，最终接受仍沿用原经验分布验收，不声称严格 DRO 全局最优。部分历史 Best 在 0.99 附近存在蒙特卡洛边界误判，独立数值复核见 `historical_best_probability_audit*.json`。原 MC 实现排除每个边际的最后一个样本；为保持比较口径，本版明确保留该行为。复核是经验乘积分布的数值计算，不是总体概率证书。

`experiment_scripts/` 保存本次服务器实验脚本，按服务器任务根目录布局运行；`source/run.py` 为独立运行入口。`BASELINE_AUDIT.json` 与 `candidate_verification.json` 为校验记录。

本轮成本口径结果：37/40 个算例达到平均值不高于旧 Best，尚未全面达标。额外概率复核揭示边界误判；采用候选前请运行 `strict/strict_select.py`，空结果表示本次记录没有复核通过的候选。此后处理时间单独计算。

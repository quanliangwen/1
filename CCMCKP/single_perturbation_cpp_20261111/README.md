# CCMCKP 单扰动 C++ 版

本版移植自 `CCMCKP_单扰动源码_20261109.zip` 的 `--operator-selection-policy single` 与随包 `selected_policy.json` 的组合。求解、概率评估和随机数均在 C++ 进程内完成。运行只需要编译后的程序和原 benchmark 数据目录。

## 编译和运行

在 64 位 Linux、GCC 9.4 和 CMake 上完成编译与对照验证。源码使用 C++17，编译器需支持 128 位无符号整数。保留 CMake 中的浮点选项，避免乘加合并改变边界判定。

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/ccmckp_single --instance /path/to/benchmark/APP_3_5_30_ \
  --tmax 21 27 --p0 0.99 --seed 832273 --runs 1 \
  --output-dir result/app_3_5_30
```

输入直接使用原目录里的 `cost.txt`、`node_to_factor.pkl` 和各个 `<id>_sample.txt`。实例目录名称提供 (m, N, L)。输出包含每次运行的解、成本、概率和计数 JSON，以及各个 Tmax 的 `ddts_summary.csv`。使用 `--runs 30 --run-workers 30` 可在同一 Tmax 下并行执行 30 次，种子逐次加一。运行 `--help` 查看参数。

正常模式按原版的每次运行 600 秒时间预算停止。默认 P0 为 0.99，蒙特卡洛评估每次 100 万样本，候选排序用的小样本为 1 万。输出中的概率是原搜索评估器记录的概率。由于每个实现的耗时不同，固定 600 秒内完成的评估次数可能不同。

## 迁移范围

- 预处理保留均值、样本标准差、经验随机占优和原候选排序。初始化按原版使用效用或成本风险起点，经小样本修复后由原评估器确认。
- (L^m < 10^7) 时执行原精确堆评估、随机类序逐类改进和反应式禁忌期限。其他算例执行原蒙特卡洛评估、小样本引导的单类候选和补偿性双类交换。每轮搜索使用轻量单类扰动。
- 蒙特卡洛使用与 NumPy `RandomState` 对应的 MT19937、新鲜抽样和原抽样上界。候选排序和修复使用对应的 `SeedSequence` 与 PCG64。QuickCheck 保留原分解和抽样逻辑，并与原版共用版本 2 的 JSON 缓存格式。

`--quick-check-cache-dir` 可指向原 Python 程序的缓存目录。缓存缺失时，原 Python 的 QuickCheck 子进程会从系统重新播种排列随机数，C++ 也以系统熵初始化该随机数流。固定种子逐步复现时，请让两版读取同一缓存。可用 `--inspect` 导出候选列表和 QuickCheck 行，`--trace` 导出逐次评估与搜索事件。`--evaluation-budget` 供逐步对照使用，正常实验使用 600 秒模式。

原版对照脚本和验证记录随 GitHub 目录单独提供。对照脚本用 Python 调用原包，C++ 编译与求解不需要 Python。

## 主要源文件

| 文件 | 对应逻辑 |
| --- | --- |
| `search.cpp` | 精确分支和蒙特卡洛分支的禁忌搜索、单类扰动 |
| `initialization.cpp` | 原始起点、成本风险起点和可行性修复 |
| `evaluation.cpp` | 参考精确堆评估、蒙特卡洛评估及小样本增量评估 |
| `rng.cpp`、`rng.hpp` | NumPy 与 CPython 随机数逻辑 |
| `model.cpp`、`quick_check.cpp` | 原数据读取、经验占优、候选排序与 QuickCheck |

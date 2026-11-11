# CCMCKP 双扰动 C++17 版

本版对应 `CCMCKP_双扰动源码_20261107.zip` 中的 DDTS 入口和随包 `selected_policy.json`。求解、评估与随机数均在 C++ 进程内执行，运行需要原 benchmark 数据。

## 编译和运行

使用支持 `unsigned __int128` 的 64 位 GCC 或 Clang 和 CMake 3.16+。Windows 可用 MSYS2 UCRT64 GCC 和 `-G "MinGW Makefiles"`。保留 CMake 的浮点选项，以免乘加合并改变阈值附近的判定。

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j
./build/ccmckp_dual --instance /path/to/benchmark/APP_3_5_30_ \
  --tmax 21 27 --p0 0.99 --seed 832273 --runs 1 \
  --output-dir result/app_3_5_30
```

输入直接使用原算例的 `cost.txt`、`node_to_factor.pkl` 和 `<id>_sample.txt`。实例目录名称包含组数、每组因子数和样本数。Windows 上运行 `build\ccmckp_dual.exe`。

正常模式每次运行共用 600 秒预算，包括初始化和搜索。默认搜索概率阈值为 0.99，每次权威蒙特卡洛评估抽取 100 万样本，候选引导抽取 1 万样本。`--runs 30 --run-workers 30` 可并行执行同一 Tmax 的 30 次运行，种子从 `--seed` 起逐次加一。程序输出每次运行的 JSON 和 `ddts_summary.csv`。JSON 中的概率来自原搜索评估器。

## 搜索与评估

- 轻扰动随机排列分组和备选因子，按与当前成本的差值稳定排序，并接受首个通过原评估的替换。
- 连续 5 轮未改善全局最优后切换强扰动，目标为向上取整的半数组。备选因子按随机顺序评估，强扰动完成后重置停滞计数。
- 精确分支先抽取固定数量的分组，整次强扰动完成后更新当前解、禁忌表和最优解。蒙特卡洛分支跳过找不到可行替换的分组，每成功替换一组就立即更新状态，达到目标数量即停止。
- 当 `L^m < 10^7` 时保留作者的精确堆评估和反应式禁忌期限。其他算例保留 QuickCheck、每次新鲜蒙特卡洛抽样、小样本候选排序及补偿性双类交换。每次蒙特卡洛抽样的上界沿用原 `randint(0, L-1)`，判定采用 `sum < Tmax`。
- 初始化保留效用起点或成本风险起点，以及小样本修复和原评估器确认。所用实验配置为随包 `selected_policy.json` 中的基线设置。

## 随机数与逐步验证

`rng.cpp` 实现 NumPy `RandomState` 的 MT19937、整数抽样和排列，候选排序和修复使用对应的 SeedSequence 与 PCG64。QuickCheck 复现 CPython `random.choice` 的整数抽取和排列，并兼容原版 v2 JSON 缓存。

QuickCheck 缓存缺失时，原版子进程的排列随机数流使用系统熵播种。固定种子逐步对照时，用 `--quick-check-cache-dir` 让两版读取同一份缓存。可用 `--inspect` 导出候选排序和 QuickCheck 行，用 `--trace` 导出逐次评估和事件。`--evaluation-budget` 用于逐步对照。正式模式按 600 秒计时，各语言实现的评估吞吐量可能不同。

| 源文件 | 对应逻辑 |
| --- | --- |
| `search.cpp` | 双扰动规则、精确和蒙特卡洛两条禁忌搜索路径 |
| `evaluation.cpp` | 原精确堆评估、蒙特卡洛评估和小样本增量评估 |
| `initialization.cpp` | 起点、成本风险排序和可行性修复 |
| `rng.cpp`、`rng.hpp` | NumPy 与 CPython 随机数 |
| `model.cpp`、`quick_check.cpp` | 数据读取、经验占优、候选排序与 QuickCheck |

Python 只用于对照验证。编译和运行本程序无需 Python 环境。

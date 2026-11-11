# CCMCKP S10 C++ 移植

本目录移植 `S10__FROZEN_SOURCE.zip` 中登记的 S10 搜索和原始 LSS 输出流程。默认采用冻结实验的 `G_NONE` 配置，使用 Gurobi、单线程、600 秒搜索预算，并关闭前后两段局部搜索。所有求解、评估和 CSV 输出均在同一个 C++ 进程中完成。原算例目录可直接使用。

## 编译

使用 64 位 GCC 或 Clang（需要 `unsigned __int128`）、CMake 3.20+ 和 GMP 开发库。默认后端需要 Gurobi C SDK、对应的运行库和有效的原生许可证。建议采用冻结登记的 Gurobi 13.0.1。Windows 运行时应将 Gurobi 的 `bin` 目录加入 `PATH`，Linux 应确保链接器能找到 Gurobi 运行库。

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DS10_GUROBI_ROOT=/path/to/gurobi1301/linux64
cmake --build build --config Release --target ccmckp_s10 -j
```

GMP 位于非标准目录时，传入 `-DS10_GMP_ROOT=/path/to/gmp`。Windows 上可用 MSYS2 UCRT64 GCC，将 Gurobi SDK 根目录设为 `win64`，并将 CMake 生成器设为 `-G "MinGW Makefiles"`。

源码也保留 `mip_backend.py` 的 HiGHS 路径。使用下面的配置构建免 Gurobi 许可证的版本，并在执行时明确传入 `--backend highs`。CMake 会优先使用已安装的 HiGHS，否则获取固定版本 1.11.0。

```sh
cmake -S . -B build-highs -DCMAKE_BUILD_TYPE=Release -DS10_ENABLE_GUROBI=OFF -DS10_ENABLE_HIGHS=ON
cmake --build build-highs --config Release --target ccmckp_s10 -j
```

## 运行

按冻结登记运行第 10 个算例的第 1 次重复。输入校验使用随源码提供的算例清单，`--out` 指向新建的结果目录。

```sh
./build/ccmckp_s10 --index 10 --rep 1 --benchmark-root /path/to/benchmark --out run_10_01
```

也可直接指定原算例目录、容量和种子。以下命令只运行 S10 搜索并保存候选及证书。

```sh
./build/ccmckp_s10 --instance /path/to/benchmark/LAB_3_5_30_ --capacity 14 --seed 960001 --out lab_14 --search-only
```

Windows 上使用 `build\ccmckp_s10.exe`。原算例输入包括 `cost.txt`、`node_to_factor.pkl` 和各 `*_sample.txt`。程序直接读取冻结算例的整数列表 pickle。全流程仅在搜索结束后读取 `*_dist.txt` 并报告真实概率。

`--seconds` 支持 30 到 600 秒。小算例沿用冻结源码的 55 秒预留，应使用默认 600 秒运行。`--local-phases pre|post|both` 可显式开启已有局部搜索阶段。主输出包括 `S10_search.json`、`S10_search.run.json`、`RESULT.json`、`ORIGINAL_LSS_DECISION_TRACE.json` 和 `result/Localsearch` 下的 CSV。`--search-only` 仅生成前两个 JSON。搜索文件采用未压缩 JSON。

单独对照评估时，`--evaluate` 接收按分组顺序排列的因子编号，并输出网格整数证书、LSS 结果、快筛序列和 PCG64 索引预览。加 `--real` 可同时执行真实概率评估。

```sh
./build/ccmckp_s10 --instance /path/to/benchmark/LAB_3_5_30_ --capacity 14 --seed 960001 --evaluate 12,1,5 --bins 4096 --real
```

## 实现对应关系

| 冻结 Python 实现 | C++ 实现 |
| --- | --- |
| `instance.py` | `model.cpp` 读取分组、样本和成本，保持分组顺序 |
| `strict_solver.py`、`stable_solver.py`、`engine.py` | `search.cpp` 实现小算例成本序枚举、均值方差前沿、风险候选、CDF/DRO MITM、局部搜索开关及短名单 |
| `small_counts.py`、`exact_oracle.py` | `evaluation.cpp` 实现外向舍入区间计数、十进制向上和向下量化、GMP 无进位整数多项式乘法及最终重算 |
| `gurobi_backend.py`、`mip_backend.py` | `mip.cpp` 通过原生 API 构建同一线性模型并逐次追加排除约束 |
| `native_support.py` 和 `engine.py` 的随机初始化 | `rng.cpp` 和 `evaluation.cpp` 复现 NumPy SeedSequence、PCG64、整数采样和快筛排列 |
| `func_cl_estimator.py` 和 `Factor.resample_multi` | `evaluation.cpp` 复现 CPython `random.choice`、NumPy `RandomState`、LSS 快筛、堆评估及蒙特卡洛重采样 |
| `s10_lss_bridge.py`、`func_localsearch.py` 的输出段 | `report.cpp` 按成本顺序评估候选、复评两类队列并输出原来的三个变体 |
| `real_P_test` 和 LAB/APP 分布函数 | `report.cpp`、`normal.hpp`、`rng.cpp` 复现固定种子 832273 的五类分布和 1000 万次真实概率统计 |

原始样本证书和 LSS 重采样采用 `sum < T`，真实概率报告采用 `sum <= T`。LSS 重采样保留 `randint(0, L-1)` 的上界排除语义。整数证书包含所有原始样本，并用整数交叉相乘判定 0.99 阈值。浮点 FFT、矩阵点积和壁钟预算会影响大算例的候选排序与搜索进度，完整搜索轨迹的逐步一致性需要在相同后端和环境下另行验证。

## 第三方代码

`third_party/` 包含 PocketFFT、nlohmann/json 和 PicoSHA2 单头文件。NumPy 1.24.4 的随机数与间接分区代码，以及 SciPy 1.10.1 的 Cephes 逆正态系数，在相应模块中注明来源。许可证随源码提供。


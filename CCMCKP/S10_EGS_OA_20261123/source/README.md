# CCMCKP S10 C++ · EGS椭球引导搜索（统一验收）

本版本在用户上传的S10冻结源码基础上增加EGS椭球引导搜索。初始化、原始样本整数概率证书、LSS评价及报告保持原实现；只替换主候选生成搜索。默认使用 `ellipsoid_oa`、半径系数2.4、每次代理求解最多5秒、单线程、600秒搜索预算，前后局部搜索均关闭。原MITM搜索保留为显式对照选项。

## 新算法与比较口径

每次从当前原始样本执行原 `init_frontier()`，禁止历史解或跨重复解输入。随后在当前搜索最好解的严格降本上界内，最小化 `mu'x + gamma*||diag(sqrt(v))*x||_2`。分组仍每组恰选一项，方差仍是原 `Instance` 的ddof=0定义。

`ellipsoid.cpp` 使用Gurobi线性整数主模型、范数支撑平面及完整向量排除来生成候选。每次查询可以因时间片用尽而提前返回实际离散候选，其真实椭球风险单独计算；`proxy_optimal` 仅表示该次未访问代理子问题达到数值意义的最优，不是原CCMCKP全局最优。

没有添加“椭球风险小于容量”的硬约束，也不以椭球评分拒绝原问题可行性。候选始终通过原 `native_check()`；只有原始样本整数证书下界满足0.99才进入原候选池。原接口返回未接受可能包含未判定情况，日志不将其提升为不可行证明。已处理完整向量的排除只是枚举去重，不推广成子集不可行割。

原概率证书下的搜索最好解与最终LSS输出解分别记录。最终继续原短名单、LSS复评和三个输出变体；默认主结果仍是原成本优先变体。真实分布参数不用于搜索。

半径2.4继承原S10初始化的工程系数，时间片5秒也是本版本预先固定的工程参数，均不是论文给出的普适最优设置或0.99置信保证。EGS不是一个更换最终约束的DRO模型。

对照命令（使用相同算例、种子、预算，输出目录必须不同）：

```sh
# 默认：椭球引导候选搜索
./build/ccmckp_s10 --index 11 --rep 1 --benchmark-root /path/to/benchmark --out egs_11_01
# 原S10 MITM主搜索
./build/ccmckp_s10 --index 11 --rep 1 --benchmark-root /path/to/benchmark --out baseline_11_01 --search-flow frontier_mitm
# 仅将新主搜索的波动项置零；共同初始化仍完全相同
./build/ccmckp_s10 --index 11 --rep 1 --benchmark-root /path/to/benchmark --out mean_11_01 --ellipsoid-gamma 0
```

`--ellipsoid-gamma` 允许0..100，`--ellipsoid-slice` 允许0.1..30秒。默认试验采用2.4和5，不根据测试结果临时调参。旧默认流程可用 `--search-flow frontier_mitm` 显式恢复，未开启局部搜索时结果arm为 `G_NONE`；新流程为 `EGS_OA_none`，gamma独立记录。

当前上传包的搜索计时仍为原S10定义：默认600秒搜索、内部预留45秒；搜索后的LSS复评和真实概率报告在搜索预算外。不能把完整进程称为严格600秒，也不能与另外修改过LSS时钟的版本混为同一冻结口径。

文献、数学适配边界、校验范围见 `DESIGN_AND_REFERENCES.txt`、`SOURCE_DERIVATION.json` 和 `validation/`。本包不包含原始benchmark、许可证或历史解。

## 编译

使用 64 位 GCC 或 Clang（需要 `unsigned __int128`）、CMake 3.20+ 和 GMP 开发库。编译必须提供 Gurobi C SDK 和对应运行库。运行到 MIP 阶段时需要有效的原生许可证。建议采用冻结登记的 Gurobi 13.0.1。Windows 运行时应将 Gurobi 的 `bin` 目录加入 `PATH`，Linux 应设置 Gurobi 运行库路径，并按服务器现有配置使用原生许可证。

```sh
export GUROBI_HOME=/path/to/gurobi1301/linux64
export LD_LIBRARY_PATH="$GUROBI_HOME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --target ccmckp_s10 -j
```

GMP 位于非标准目录时，传入 `-DS10_GMP_ROOT=/path/to/gmp`。Windows 上可用 MSYS2 UCRT64 GCC，将 Gurobi SDK 根目录设为 `win64`，并将 CMake 生成器设为 `-G "MinGW Makefiles"`。

## 运行

按登记运行第 21 个算例（`APP_3_5_30_`，`Tmax=21`）的第 1 次重复。输入校验使用随源码提供的算例清单，`--out` 指向新建的结果目录。

```sh
./build/ccmckp_s10 --index 21 --rep 1 --benchmark-root /path/to/benchmark --out run_21_01
```

也可直接指定原算例目录、容量和种子。以下命令只运行 S10 搜索并保存候选及证书。

```sh
./build/ccmckp_s10 --instance /path/to/benchmark/LAB_3_5_30_ --capacity 14 --seed 960001 --out lab_14 --search-only
```

Windows 上使用 `build\ccmckp_s10.exe`。原算例输入包括 `cost.txt`、`node_to_factor.pkl` 和各 `*_sample.txt`。程序直接读取冻结算例的整数列表 pickle。全流程仅在搜索结束后读取 `*_dist.txt` 并报告真实概率。

`--seconds` 支持 30 到 600 秒。`--local-phases pre|post|both` 可显式开启已有局部搜索阶段。主输出包括 `S10_search.json`、`S10_search.run.json`、`RESULT.json`、`ORIGINAL_LSS_DECISION_TRACE.json` 和 `result/Localsearch` 下的 CSV。`--search-only` 仅生成前两个 JSON。运行元数据的 `search_flow` 为实际选择的 `ellipsoid_oa` 或 `frontier_mitm`，兼容字段 `exhaustive` 和 `S10_exhaustive` 均为 `null`。

单独对照评估时，`--evaluate` 接收按分组顺序排列的因子编号，并输出网格整数证书、LSS 结果、快筛序列和 PCG64 索引预览。加 `--real` 可同时执行真实概率评估。

```sh
./build/ccmckp_s10 --instance /path/to/benchmark/LAB_3_5_30_ --capacity 14 --seed 960001 --evaluate 12,1,5 --bins 4096 --real
```

## 实现对应关系

| 冻结 Python 实现 | C++ 实现 |
| --- | --- |
| `instance.py` | `model.cpp` 读取分组、样本和成本，保持分组顺序 |
| 原 `stable_solver.py`、`engine.py` | `search.cpp` 保留共同初始化、原MITM对照、局部搜索开关及短名单；新 `ellipsoid.cpp` 实现椭球代理外逼近 |
| `exact_oracle.py` | `evaluation.cpp` 实现十进制向上和向下量化、GMP 无进位整数多项式乘法及原始样本概率证书 |
| `gurobi_backend.py` | `mip.cpp` 通过原生 API 构建同一线性模型并逐次追加排除约束 |
| `native_support.py` 和 `engine.py` 的随机初始化 | `rng.cpp` 和 `evaluation.cpp` 复现 NumPy SeedSequence、PCG64、整数采样和快筛排列 |
| `func_cl_estimator.py` 和 `Factor.resample_multi` | `evaluation.cpp` 复现 CPython `random.choice`、NumPy `RandomState`、LSS 快筛、堆评估及蒙特卡洛重采样 |
| `s10_lss_bridge.py`、`func_localsearch.py` 的输出段 | `report.cpp` 按成本顺序评估候选、复评两类队列并输出原来的三个变体 |
| `real_P_test` 和 LAB/APP 分布函数 | `report.cpp`、`normal.hpp`、`rng.cpp` 复现固定种子 832273 的五类分布和 1000 万次真实概率统计 |

Gurobi 使用单线程、登记的种子及零相对 MIP gap，并在每次求解后加入排除约束。许可证或原生求解调用失败时，程序记录错误并退出。

原始样本证书和 LSS 重采样采用 `sum < T`，真实概率报告采用 `sum <= T`。LSS 重采样保留 `randint(0, L-1)` 的上界排除语义。整数证书包含所有原始样本，并用整数交叉相乘判定 0.99 阈值。浮点 FFT、矩阵点积和壁钟预算会影响大算例的候选排序与搜索进度，完整搜索轨迹的逐步一致性需要在相同 Gurobi 版本和环境下另行验证。

## 小型验证

```sh
cmake -S . -B build -DS10_BUILD_EGS_TESTS=ON
cmake --build build -j2
python3 tests/check.py --binary build/ccmckp_s10 --math-binary build/egs_math_test --workdir /path/to/new_tiny_check
```

该检查创建合成小数据，完整枚举8个选择检验代理风险排序，并用Fraction枚举27000种样本组合核对证书上下界；不运行原始benchmark或额外原生MC。

本次交付已在服务器原生Gurobi11.0.3/GCC环境完成数学检查与四条完整合成流水线，原版与显式MITM对照的语义结果一致，详见 `validation/VALIDATION_FINAL.json`。Windows/Gurobi13.0.1接口编译通过，但本机现有PIP限定许可不能用于原生C++运行，未声称Windows运行通过。若正式性能对照采用13.0.1，应在相同完整许可及版本下另行登记；本次不构成40例30次的性能验证。

原合成夹具发现时间字段比较错误的首轮记录保存在 `validation/synthetic/VALIDATION.json`，最终语义审计只忽略 `found_seconds`、`certificate_seconds` 两类实际耗时，未改结果或重跑种子。详见 `validation/PREPARATION_NOTES.txt`。

## 第三方代码

`third_party/` 包含 PocketFFT、nlohmann/json 和 PicoSHA2 单头文件。NumPy 1.24.4 的随机数与间接分区代码，以及 SciPy 1.10.1 的 Cephes 逆正态系数，在相应模块中注明来源。许可证随源码提供。


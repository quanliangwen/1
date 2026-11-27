本版入口：--search-flow entropy_cdf_calibrated；原S10/LSS及B01、D02、R02公共实现未改。
构建依赖：64位GCC或Clang（C++17和unsigned __int128）、CMake>=3.20、GMP/GMPXX、BLAS、Gurobi C SDK及有效许可证。第三方开源头文件与许可证随source/提供；不包含Gurobi SDK、商业许可证或完整benchmark样本。
构建示例（新的空工作目录）：
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release -DS10_GUROBI_ROOT=/path/to/gurobi/linux64
cmake --build build --target ccmckp_s10 entropic_test -j2
新增entropic_test。已经通过的核心数学和高精度包络检查不重复；复现者可在新工作区运行。
算法每run从当前原始500样本现场构造192bit熵权重，t=.1/.16/.25/.4/.6/.85；eta>=.8。无跨run系数缓存/旧解/MIP start。eta<ln100不能声称代理单独保证.99，最终只原LSS。
bin/ccmckp_s10 --instance BASE/benchmark/NAME --capacity T --seed N --rep R --seconds 600 --out NEW_DIR --manifest source/BENCHMARK_MANIFEST.json --search-flow entropy_cdf_calibrated。
正式测试必须由冻结controller设置CCMCKP_LAUNCH_MONOTONIC并监督595秒硬guard；不能省略完整进程时钟。
原始benchmark须由用户已有数据提供并与formal_PROTOCOL.json输入SHA逐项一致。controller和audit_reader中冻结路径指向本次实验，只能读取本次原记录；如另做复现，应在全新根目录重新配置、登记、冻结，不得覆盖本次formal/runs或outcomes。
当前登记四臂三例各30共360，首60计入正式30，独立核验后继续300，不补跑失败。R04必须等本版完整测试统计后才修改。
熵模型的KL惩罚表示不是固定KL球DRO，参数使用原消耗单位，不保证对单位缩放不变。toy夹具同比放大100只用于本轮小型验证，正式benchmark原样未动。

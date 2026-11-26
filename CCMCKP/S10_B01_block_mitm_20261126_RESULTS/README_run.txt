B01源码使用说明

正式三例30次对照已结束：本版平均运行时间减少约18.4%—23.5%，avg未改善，APP50样本std增大。属于已验证的加速工程基础，未作为质量更优版本推广，也未扩展40例。

明确选择新flow：--search-flow block_mitm。
frontier_mitm是原S10半径组合；frontier_mitm_zero是原S10零半径对照。
为保留历史接口，未改变旧CLI的默认flow，不传--search-flow不会自动选择B01。

依赖：Linux，C++17 GCC/Clang，CMake，GMP/GMPXX，Gurobi C接口及有效许可，系统BLAS（dgemm_）。不依赖Python调用概率评价器。
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release -DS10_GUROBI_INCLUDE=<含gurobi_c.h目录> -DS10_GUROBI_LIBRARY=<libgurobi路径>
cmake --build build --target ccmckp_s10 block_test -j 4
build/block_test fixtures/block
上述内置小夹具用于3943项确定性/穷举检查，不运行额外原生MC。

运行示例（参数路径需替换，输出目录必须此前不存在）：
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 build/ccmckp_s10 --instance <原始算例目录> --capacity 63 --seed 980001 --rep 1 --seconds 600 --search-flow block_mitm --out <全新输出目录> --manifest source/BENCHMARK_MANIFEST.json

本次正式性能试验通过controller.py启动：启动前设置CCMCKP_LAUNCH_MONOTONIC，独立wait线程记录退出时刻，595秒外部保护；完整时长不允许超过600。
直接CLI同样记录其main入口后的时钟；要复现实验的进程启动前时钟，应使用随包controller与匹配协议、而非只比较内部search.elapsed。
controller拒绝重复LAUNCH；不可拿其覆盖已有结果或补跑失败。
全部初始候选只来自本run输入。最终只按原LSS>=.99，不新增真实概率评价。

新增文件：convolution_tree.hpp，block_mitm.hpp，block_bounds.hpp，block_schedule.hpp，tests/block_test.cpp。
主要接入：Search::block_search和两个新flow；公共evaluation/rng/report/model/mip/fft保持原字节。
源码包含三臂所需旧实现，仅flow=block_mitm运行新增小块机制。

工程2次与正式30次使用不同seed族，不混合统计。没有自动扩展40例。

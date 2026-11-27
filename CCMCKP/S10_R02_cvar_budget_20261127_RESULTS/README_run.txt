R02当前入口：--search-flow cvar_budget_calibrated
本次formal/PROTOCOL.json为唯一有效参数与身份登记， source/README.md是统一基线历史通用说明，不能据其启动旧流。
编译：cmake -S source -B build -DCMAKE_BUILD_TYPE=Release，指定已安装Gurobi11 C头文件与libgurobi110.so；cmake --build build --target ccmckp_s10 calibrated_test -j4。
数学测试已通过，不重复运行成功测试；复现者可以另建新目录运行calibrated_test fixtures/budget_tiny。
单次调用：bin/ccmckp_s10 --instance BASE/benchmark/NAME --capacity T --seed SEED --rep REP --seconds 600 --out 全新目录 --manifest source/BENCHMARK_MANIFEST.json --search-flow cvar_budget_calibrated。
正式运行必须由冻结controller设置CCMCKP_LAUNCH_MONOTONIC并监督595秒guard，不能脱离控制器省略完整进程时钟。B01与D02对照分别block_mitm与block_winf_transport。
不读取历史解，初始候选仅由当前原数据精确ES95资源模型构造。只保留原LSS最终验收，不额外估计真实概率。所有失败不补跑选优。
R02必须完整终末、独立审计及统计后才修改下一版R03，R04再后续。当前未授权自动扩展40例，不按试点成本私改已冻结R02。

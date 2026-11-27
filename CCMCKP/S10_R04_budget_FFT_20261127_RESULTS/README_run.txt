R04入口：--search-flow cvar_budget_polish。三个新鲜对照入口为block_mitm、block_winf_transport、cvar_budget_calibrated。
依赖64位GCC/Clang C++17、unsigned __int128、CMake>=3.20、GMP/GMPXX、BLAS、Gurobi C SDK及有效许可证。独立读者依赖Python、NumPy、SciPy；不导入C++写者或求解器。第三方开放头文件/许可证随源码，商业SDK/许可证和完整benchmark样本不打包。
在全新空目录构建：
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release -DS10_GUROBI_ROOT=/path/to/gurobi/linux64
cmake --build build --target ccmckp_s10 polish_test -j2
主程序示例：build/ccmckp_s10 --instance ORIGINAL_BENCHMARK/NAME --capacity T --seed N --rep R --seconds 600 --out NEW_DIR --manifest source/BENCHMARK_MANIFEST.json --search-flow cvar_budget_polish
正式测试必须设置CCMCKP_LAUNCH_MONOTONIC并由controller监督launch至exit全程与595秒guard。不能省略全程时钟或在搜索计时外额外预生成模型/FFT/起点。
原始样本须与formal_PROTOCOL.json输入SHA一致。冻结controller/audit_reader写死本轮路径，仅用于本轮记录；另做复现需新根目录与重新登记，不能覆盖原formal/runs/outcomes。
已通过453项小型数学检查含12个真实tinyMILP、26项独立读者/篡改检查及两个完整tinyLSS集成；未变R02/R03b数学按源SHA有限复用，不重复成功测试，不新增真实概率诊断MC。
R04不是同一预算集合下保证更强的RO：本run预算RO提供种子，私人近似FFT及局部MCKP可生成预算集合外候选，只有原整数CDF接受后才进入原短名单，最终只原LSS。私人FFT绝不写公共guide_cache。
母体120秒、私人提议最多60秒，全部阶段共享实际600。600秒包括加载、系数、RO/FFT/整数CDF、原LSS、保存fsync与退出。初始解全部自身产生，无历史解/MIPstarts/跨重复输入，无LSS反馈调参。
本批四臂三例各30共360，首60计入正式360，技术gate通过才其余300。自然终末后按冻结门槛判断是否另行登记全40；不是默认全量或反复重跑选seed。

R01预算鲁棒优化：源码与已完成测试说明

当前算法入口：--search-flow budget_robust。
对照入口：block_mitm为B01；block_winf_transport为D02。
source/README.md保留的是历史说明，用于继承来源核对，不是本版预算RO说明。

依赖：64位Linux C++17、CMake、GMP/GMPXX、Gurobi SDK/有效许可、BLAS。
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release -DS10_GUROBI_ROOT=/path/to/gurobi/linux64
cmake --build build --target ccmckp_s10 budget_ro_test -j4
小型数学测试：build/budget_ro_test fixtures/budget_tiny

正式三例×三版本×30=270次已经结束，不得在原formal目录重启controller或覆盖结果。控制器、输入SHA、二进制SHA和协议随包保留，用于复核，不是重复启动指令。
每run从原始数据生成正预算模型和起点，使用本run冷启动MIP，禁止旧解/旧证书/外部MIP start。
最终只按原LSS验收，0..499索引、strict sum<T和复核政策不改。预算Gamma不是概率水平，样本最大值不是总体上界。
本次R01未达到成本改进目标：APP30无有效结果，另两例成本显著较高。不能将快速失败或高成本std为0说成综合改善。

完整600从pre-Popen至退出，包括加载、构造模型、排序、内部证书、LSS、保存fsync和返回。算法使用430搜索、590 LSS截止，控制器595独立硬保护；事后独立审计时间不计作算法求解时间。
原始benchmark数据不重复上传，1306项SHA登记于formal_PROTOCOL.json。仅必要小型测试夹具随源码包提供。
全部紧凑记录如超过90MiB，分成80MiB文件上传；合并脚本核验总体SHA，不需重新运行算法。

D02：与D01相同正半径DRO模型的运输占优有效剪枝
正式结果以修改说明与测试结论.txt和Excel为准，完整证明、假设和文献见设计与文献依据.txt。
source/README.md是继承的历史MB说明，保留其冻结字节用于来源复核；它不是当前新flow的算法描述。

依赖：64位Linux GCC/Clang C++17、CMake、GMP/GMPXX、Gurobi SDK/有效许可及BLAS。
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release -DS10_GUROBI_ROOT=/path/to/gurobi/linux64
cmake --build build -j4
新增数学目标transport_cuts_test，传入fixtures/winf、fixtures/compensating、fixtures/crossing、fixtures/overflow四个路径。
数学及活跃机制测试结果见VALIDATION.json，独立排除证据读者测试见INDEPENDENT_READER_TEST.json。

三个flow：block_mitm原B01；block_winf_dro原D01正半径；block_winf_transport同DRO加新有效剪枝。
正式controller.py和formal_PROTOCOL.json是可审核的原实验注册，不是重复运行授权；禁止在原结果目录重启它或覆盖结果。
每run自己从原始数据生成起点、半径与空witness缓存。新代码不能读取旧结果/旧证书或其他重复的解。
最终仍只用原LSS .99，所有索引0..499、strict sum<T及最后完整评价政策保持；无额外真实概率采样。
完整600包括启动/加载/模型/排序矩阵/初始化/搜索/全部LSS/保存fsync及退出。原生网格和推断排除是内部DRO求解证书，不是新增最终统计验收规则。
证书重建独立使用Python Fraction和GMP通用算术，未导入优化写者、求解器或概率抽样。其事后耗时不属于算法运行。
原始benchmark数据不重复打包，1306个数据文件SHA登记在formal_PROTOCOL.json。小型测试夹具随源码包提供。
全紧凑记录如超90MiB将按80MiB分片；合并脚本逐片串接并校验总体SHA256，不需要重新运行算法。

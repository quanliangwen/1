D01：B01候选覆盖框架上的加权Wasserstein∞分布鲁棒机会约束

当前正式结果与文献/数学边界以“设计与文献依据.txt”和“修改说明与测试结论.txt”为准。
source/README.md为历史继承说明，未参与当前flow注册，不能据它把D01当成旧MB/椭球版本；保留其冻结原字节便于复核来源。

依赖：64位Linux GCC/Clang C++17、CMake、GMP/GMPXX、Gurobi SDK及有效许可、BLAS/OpenBLAS、Python3标准库。
构建示例（根据本机依赖路径配置）：
  cmake -S source -B build -DCMAKE_BUILD_TYPE=Release -DS10_GUROBI_ROOT=/path/to/gurobi/linux64
  cmake --build build -j4
新增确定性数学目标为 winf_product_test；正式服务器的构建配置与全部验证日志见紧凑证据。

三个flow：block_mitm=原B01；block_insurance=名义共同覆盖对照；block_winf_dro=正半径DRO。
命令行及原始数据路径以formal_PROTOCOL.json和controller.py内逐项实参为准。禁止直接重复运行交付控制器：它是原正式270的可审计冻结源码，存在防重启保护，不是新实验启动授权。
原数据未重复打包；formal_PROTOCOL.json含1306条源数据SHA针，数据目录为benchmark/<算例名>。
每run自身生成起点；DRO从当前原始500样本精确计算自身r_j并构造最坏平移分布，不读取历史解。
原始LSS最终统计验收不变；内部DRO整数证书用于候选生成，不替代LSS。不额外计算真实概率。
600秒含启动/加载/模型构造/初始化/搜索/全部LSS/保存fsync/退出；运行记录来自启动前到退出的父级独立计时线程。
完整紧凑记录如超过GitHub单文件限制，按80MiB分片；“合并证据分片.py”校验合并结果SHA256，原大归档只留临时工作区。

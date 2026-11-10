# F001：实际执行的冻结I002源码与正式证据

正式优化器为iterations/I002_cdf_neighborhood/candidate中的16个Python文件；登记和最终审计包含逐项SHA256。reference下是21个原LSS源码，校验后仅用兼容别名加载。主搜索不读取真实分布、历史解或外部验收缓存。

实际搜索环境：Python3.13.9，numpy2.4.0，scipy1.17.1，python-flint0.8.0；原LSS环境：Python3.8.10，numpy1.24.4，scipy1.10.1。原benchmark数据不重复打包，按RAW_REFERENCE.json和LSS_DATA_REFERENCE.json逐项SHA恢复原始输入；不能用其他样本或新生成分布替代。

单次搜索入口：candidate/run.py --instance 原算例目录 --capacity T --seed 登记搜索种子 --seconds 600 --risk-method cdf_lns --phase-seconds 180 --out 新输出路径。40例参数见CASES.json，30个新种子见formal/F001_I002_40x30/REGISTRATION.json。程序拒绝覆盖证据；复现需新工作目录并恢复vendor313依赖。原始driver中的服务器路径需按实际原数据位置配置，路径调整不改变求解器算法。

主队列run_f001_stages.py严格先完成1200次搜索再调用validate_f001.py。全部原样本的sum<T整数下界≥0.99，再按冻结候选成本顺序运行原real_P_test：1000万次，seed832273，sum≤T，点估计≥0.985；首次通过即停。固定身份原调用可在优化器外复用，不能当1200次独立MC种子估计。不得只保留成功运行计算Avg；每例30次协议有效才给Avg和总体Std(ddof=0)。

40个case_XX.zip包含各例全部登记种子的搜索输出/日志/元数据/终止记录、外部原LSS验收记录及实际引用的调用凭证。NATIVE_ATTEMPT_LOGS.zip单独保存本正式阶段新增的调用尝试日志（含可能失败）。最终审计、Excel、校验文件和归档逐项SHA在本目录。工程/开发结果不替代本正式队列。

# CCMCKP：当前按原LSS主流程对齐

已去掉额外真实概率硬筛。原LSS的评估函数、CL=.99、原始最小成本输出_0和CSV记录流程保持原样，只替换搜索阶段。

|算例|T|新运行输出|
|---|---:|---:|
|APP_3_5_30_|21|9.034717|
|APP_3_5_30_|27|7.250013|

两例各一次新运行，已核对原始CSV、原21份参考源码和输出段AST。真实概率仅作为原CSV列记录，不筛输出。这里还不是新口径的40×30统计。

[实际确认CSV](iterations/I017_LSS_mainflow_two_case_confirmation/CONFIRMED_OUTPUT.csv) · [源码](iterations/I017_LSS_mainflow_two_case_confirmation/I017_LSS_MAINFLOW_TWO_CASE_SOURCE.zip) · [完整新运行证据](iterations/I017_LSS_mainflow_two_case_confirmation/I017_TWO_CASE_ACTUAL_MAINFLOW_EVIDENCE.zip) · [详情及运行方式](iterations/I017_LSS_mainflow_two_case_confirmation/README.md)

[当前验收要求](CURRENT_ACCEPTANCE_POLICY.json) · [完整历史过程](ITERATION_LOG.md)

此前采用原样本99加真实概率985硬筛的代码、Excel和实验保留为不同口径的历史记录，不代表当前与LSS的公平比较。用户已暂停持续目标，本次只完成指定两例确认。

# S10原算法与LSS主流程对齐

最新实跑使用原冻结S10搜索算法：12份搜索源码逐字节保持一致，只替换外围额外真实概率后筛。候选复核和最终输出复用原LSS评估函数CL=.99及原始_0输出、CSV写入；真实概率仅记录。

|算例|T|S10新运行输出|
|---|---:|---:|
|APP_3_5_30_|21|9.034717|
|APP_3_5_30_|27|7.250013|

两例各一次新运行。原S10均完成其125组合小例枚举，最终结果及原LSS判定均已核验；本次未使用I017替换搜索，也不是40×30统计。

[S10实跑CSV](iterations/S10_LSS_mainflow_APP3_confirmation/S10_CONFIRMED_OUTPUT.csv) · [原S10源码和LSS适配入口](iterations/S10_LSS_mainflow_APP3_confirmation/S10_LSS_MAINFLOW_SOURCE.zip) · [完整新运行证据](iterations/S10_LSS_mainflow_APP3_confirmation/S10_APP3_ACTUAL_EVIDENCE.zip) · [方法和计时说明](iterations/S10_LSS_mainflow_APP3_confirmation/README.md)

[当前口径](CURRENT_ACCEPTANCE_POLICY.json) · [完整历史过程](ITERATION_LOG.md)

早先双门槛99+真实985的统计是不同口径历史记录，不用于当前公平比较；之前I017两例确认另行保留。持续目标由用户暂停。

已按用户要求另存[S10、I002、I016三个版本与存储盘点](preserved_versions_20261110/README.md)，服务器既有文件未删除。60并行全量实验尚未启动。

# CCMCKP S10：移除尾部硬筛后的正式结果

**40例×30次已完成：1200/1200次同时通过原样本检查与LSS真实概率≥0.985。25/40例Avg追平或优于原Best。** 相比S9，8例Avg改善、32例持平、0例变差。仍有差距的算例完整报告。

[下载优化源码ZIP](packages/S10_OPTIMIZED_SOURCE.zip) · [40例完整结果与限制](RESULTS.md) · [完整统计JSON](FINAL_SUMMARY.json) · [1200条运行](RUN_DETAILS.json) · [原始记录ZIP](records/) · [SHA256清单](CHECKSUMS_SHA256.json)

尾部重构及硬筛已完全删除；原样本阈值统一0.99。小例完整枚举，大例保留CDF/DRO MITM和不同成本/风险候选。独立原LSS按成本验收并选择合格成员，阈值0.985、1000万次、种子832273，保留全部拒绝。该外部检验参与最终选择，额外MC耗时单列，不能将搜索时间当完整流程时间。

冻结源码及登记在正式试验前经GitHub提交33888997d58d02a85f87a887822be2b90382b02e发布并远端校验；本轮使用960001–960030新种子，每次独立求解，搜索不读取真实分布参数、旧解或其他重复结果。独立LSS调用按固定种子相同身份复用，不复用搜索。最低Real P=0.9850423；搜索超过600秒0次，原始记录均保留。

源码使用方式及环境见packages/S10_OPTIMIZED_SOURCE.zip内README和REGISTRATION.json。source目录frozen_candidate与正式1200次记录逐文件SHA一致。要得到正式合格输出，必须执行源码内的独立LSS后筛选；run.py单独输出的最低原样本成本不代表通过真实概率验收。

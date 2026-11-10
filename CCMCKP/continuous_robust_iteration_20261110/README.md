# CCMCKP鲁棒优化持续迭代

目标保持active。冻结I002的正式40例×30次已完成：1200/1200协议有效且联合合格，最终独立审计、Excel公式缓存/精确文本核验和5页视图检查已通过。源码与全部实际记录按版本区分。

[下载40×30 Excel统计](formal/F001_I002_40x30/F001_40cases_30runs.xlsx) · [对应正式源码及独立审计ZIP](formal/F001_I002_40x30/full_records/F001_SOURCE_AND_AUDIT.zip) · [40例完整运行归档](formal/F001_I002_40x30/full_records) · [正式结果与计时口径](formal/F001_I002_40x30/COMPLETED_RESULTS.md)

39例Avg等于本轮Best；39号本轮Best329.505243、Avg329.781011、Std.P0.123327，原历史Best321.700547尚未达到。25例Avg不高于历史Best；与同门槛S10相比，39/40号Avg降低、其余38例持平。最低独立原样本下界0.990004525，最低原LSS点估计0.9851032。

原验收保持：全部原始样本严格sum<T整数下界≥0.99，原完整LSS real_P_test1000万/seed832273/sum≤T点估计≥0.985；搜索不读真实参数、旧向量或验收缓存，无新增尾部硬筛。16小例已全枚举当前固定联合最优，8个APP旧成本线低于其联合最优；其余例不能据旧向量失败推断成本线不可达。

39号三个全新配对开发种子的后续进展如下，六个完整成本前缀均已独立验收：

|冻结开发版本|种子数|Best|Avg|总体Std|Avg−自身Best|
|---|---:|---:|---:|---:|---:|
|I002对照|3|329.505243|329.658117|0.136266|0.152875|
|I015自身CDF+块+精度|3|324.916225|326.196601|1.171122|1.280377|

三个配对成本均降低，但自身Best差距及波动扩大，稳定性目标仍需改进。这是3次开发统计；正式40×30表对应上方冻结I002。[配对源码与全证据](research/D003_paired_stability_prefix/D003_COMPLETE_PAIRED_EVIDENCE.zip) · [正反结果与费用](research/D003_paired_stability_prefix/RESULTS_NOTES.md)

I016已实现自身CDF后通用两组覆盖并使用剩余预算做块/精度，保留全部已接受成员。新种子冷启动536.94秒，27次完整组对扫描、33075组对，全部1071份原样本证书独立重算通过；已再现已知合格324.916225同一身份，D004完整原LSS前缀现已完成独立审计，确认池内最低合格成本324.916225及70项更便宜成员拒绝。源码与冷启动证据已经冻结，尚无I016三种子或30次Avg。[I016源码](iterations/I016_cdf_pair_cover/I016_FROZEN_ENGINEERING_SOURCE.zip) · [实际冷搜索与全部原样本复核](iterations/I016_cdf_pair_cover/engineering39/I016_COLD_SEARCH_EVIDENCE.zip) · [D004验收前登记](research/D004_I016_full_prefix/REGISTRATION.json)

[完整迭代思考、尝试和负结果](ITERATION_LOG.md) · [最新实际状态快照](progress/LATEST.json) · [全部文件SHA256清单](CHECKSUMS_SHA256.json)

正式全部文件已在提交`6fd5f9455b4e93c99ac514910a2a8a14a02de3a9`经远端608文件255525881字节及SHA核验。[D004实际启动与持续迭代](research/D004_I016_full_prefix/ACTUAL_RUN_STATUS.md)

I016下一组三种子配对已登记：与I015父版在9716211/12/13同预算冷启动，核验启动前源码后运行。[协议与源文件](stability/I016_pair_cover_case39/README.md) · [D004完整冷搜索验收证据](research/D004_I016_full_prefix/D004_COMPLETE_I016_PREFIX_EVIDENCE.zip)

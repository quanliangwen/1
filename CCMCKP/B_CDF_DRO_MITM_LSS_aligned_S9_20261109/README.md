# CCMCKP S9：LSS 对齐的可行性与稳定性优化

> **2026-11-09三例复核更正：** S9新增的APP尾部重构及概率硬筛改变了原样本模型的候选可行集，不能称作原模型同约束下的等价搜索优化。关闭该模块后三例各30次均恢复原成本（但不通过外部真实概率≥0.985）；另找到14.076616、13.564858、5.796148三个更低且通过双种子复核的候选，表明S9有可避免的保守性。这些候选是单解诊断参考，不是新的30次平均值。以下1200次原记录、源码及Excel数值均保留。[完整复核、原LSS重现及证据](https://github.com/quanliangwen/1/blob/745e7b157909e86a0187a9100261d159fec71d71/CCMCKP/S9_small_case_recheck_20261109/REPORT.md)。


**S9正式概率验证已完成：40例×30次独立求解，1200/1200通过原LSS≥0.985验收，最低Real P=0.9851032。25/40例Avg不高于原Best，40/40例Std在1e-10以内。** 仍有15例未追平原Best，其中3例已穷举证明旧成本线以内没有LSS合格选择。

[下载Excel统计表（40例汇总、1200次记录、时间超限）](statistics/CCMCKP_S9_Statistics.xlsx)

[下载优化源码包（ZIP）](packages/S9_OPTIMIZED_SOURCE.zip)

含收尾总耗时超过600秒的运行有5次，最高617.210秒，完整保留并单列。严格600秒预算合规结果与概率验收结果分别报告；不能将1200次概率合格解释为全部满足严格时间预算。

[完整40例结果与限制](RESULTS.md) · [全部1200次概率统计](USER_VALIDATION_SUMMARY.json) · [原注册严格600秒核验](FINAL_SUMMARY.json) · [原始记录及诊断压缩包](records/) · [SHA256清单](CHECKSUMS_SHA256.json)

源码已在正式试验前通过提交 `d497e61ac052a37d8d2c3e31dfc69f8df25cd8f3` 冻结并核验，实际注册见 `REGISTRATION.json`。40个不同最终向量/算例组合的原LSS仿真通过明确映射覆盖全部1200次独立搜索。

最终验收保持用户确认的原 LSS 辅助统计口径：名义 CL=0.99，原 `real_P_test` 函数体，10,000,000 次仿真，种子 832273，事件 `sum<=Tmax`，真实分布仿真概率 **≥0.985**。内部经验概率整数证书只约束原样本的边际乘积分布，不能代替最终 LSS 检验。

S8 发现一次并发下的空解：辅助模型逐项做10万次FFT，耗尽可搜索时间。该轮已中止并保留所有失败、已完成及中止时活动任务的记录，见同仓库 `B_CDF_DRO_MITM_LSS_aligned_20261109/`。本版独立注册并整轮重跑，未使用补跑替换失败记录。

S9 将小算例的辅助 CDF 评分改成两半卷积与 CDF 矩阵乘法，加入60秒辅助计算上限，并在辅助计算前保存经整数计数通过的低风险候选。10万选择的实测批量评分为12.30秒；100个原逐项FFT对照的最大误差约4.25e-14，合成分布与直接卷积的最大误差约7.8e-16。另有12次并发、180秒预算压力测试全部返回解，详见验证JSON。上述是开发验证，不替代正式40×30实验。

正式计划：全部40例，每例30个独立搜索种子 **940001–940030**，每次600秒，最多64个并行进程。失败、空解与超时均保留。每次从原样本、成本和分组独立求解；禁止读取 `_dist.txt` 真实分布参数、旧解或其他运行结果。验证进程独立读取原 LSS 的分布元数据。相同算例/容量/解向量/检验种子对应确定性相同的原 LSS 仿真，重复结果显式映射复用，公开实际独立仿真调用数。

搜索保留 CDF/DRO 折半框架，使用独立初始化、CDF 局部优化和单/双组交换。一般实例的内部经验门槛为0.99，50组APP使用0.993安全裕量。30样本APP按公开的长尾生成结构及输入样本构造辅助模型，分型与有限样本均值裕量是启发式模型假设。所有参数已在这40例的开发阶段校准；正式试验衡量同一基准上的独立重复运行稳定性，不代表未见算例的泛化测试。

`frozen_candidate/` 是冻结源码，`FROZEN_SOURCE_SHA256.json` 是源码清单。`lss_eval_reference/` 保留上传LSS原文件及原压缩包/数据哈希；`lss_real_eval.py` 只恢复导入和路径接线，核对原函数AST、原文件和分布数据哈希。真实仿真耗时单独记录，不计入搜索时间，原LSS主实验也在搜索计时结束后执行真实仿真。按用户要求统计全部30条运行。

原CDF Best是成本参考，需接受同一LSS检验，不能默认可行。APP_3_5两容量和APP_4_5 T=47的全部旧成本线以内选择均未通过原LSS验收；T=49存在5个旧成本线内的LSS合格选择。该有限成本前缀审计在S8冻结后完成，不向搜索过程反馈，详见 `OLD_COST_EXHAUSTION_SUMMARY.json`。本实现仍保留内部经验概率0.99约束，不能把LSS外部0.985容差解释成将内部概率约束改为0.985。

运行环境：求解器Python3.13.9、NumPy2.4.0、SciPy1.17.1、python-flint0.8.0；原LSS检验Python3.8.10、NumPy1.24.4、SciPy1.10.1。依赖见requirements。原始基准目录为服务器 `/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/`，3660个输入文件哈希见原始注册清单。监督脚本含服务器环境绝对路径，迁移时应显式调整。

```bash
python3.13 -m pip install --target vendor313 -r requirements_solver.txt
python3.13 frozen_candidate/run.py --instance /path/to/benchmark/LAB_3_5_30_ --capacity 11 --seed 940001 --seconds 600 --out /path/to/new_run.json.gz
python3 lss_real_eval.py --instance /path/to/benchmark/LAB_3_5_30_ --capacity 11 --selection '[12,10,5]' --out /path/to/new_LSS_test.json
```

`WORKBOOK_REFERENCE.json` 是统计表只读摘录，原表未修改，未提供LSS原始解和概率列，因此表中的LSS成本不能直接认定为经过本次真实概率复核。

时间预算和分析范围的定义见 `ANALYSIS_SCOPE.json`。全部原始记录均保留，未补跑覆盖。各历史压缩包应分别解压到各自目录。

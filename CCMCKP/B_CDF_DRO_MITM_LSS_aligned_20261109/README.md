# CCMCKP：与上传 LSS 对齐的可行性优化

当前阶段：已冻结候选源代码，冻结后的 40 例复核正在运行；本提交不宣称完成正式 40×30 验证。

最终验收采用用户确认的原 LSS 辅助统计口径：名义 CL=0.99，原 `real_P_test` 函数体，10,000,000 次仿真，种子 832273，事件 `sum<=Tmax`，实际仿真概率 **≥0.985**。真实仿真耗时与搜索耗时分别记录。内部整数卷积证书只证明经验边际乘积分布的概率，不替代最终 LSS 检验。

冻结后的正式计划：全部 40 例各独立求解 30 次，搜索种子 930001–930030，每次最多 600 秒；失败、无解、超时均保留，不补跑替换。每次独立搜索，禁止读取真实分布参数、历史解或其他运行的输出。原 LSS 每次重置同一仿真种子，因此同一算例、容量、解向量和种子的最终检验可复用完全相同的确定性计算，并公开独立仿真调用数及 1200 次运行的映射。

算法保留 CDF/DRO 折半搜索，并加入独立初始化、CDF 局部模型、单/双组交换和经验分布整数计数。LAB 与一般 APP 使用 0.99 的内部经验概率门槛；50 组 APP 使用 0.993 安全裕量。30 样本 APP 另用公开生成器的长尾混合权重以及输入样本构造辅助模型，不读取 `_dist.txt`。辅助模型使用明确记录的启发式分型和有限样本均值裕量，属于模型假设，不是总体概率保证。参数已经用这 40 例的开发实验校准；正式 30 次验证衡量同一基准上的重复运行稳定性，并不构成未见算例的泛化测试。

`frozen_candidate/` 是冻结求解器；`lss_eval_reference/` 是上传 LSS 原始参考文件及 SHA256 清单；`lss_real_eval.py` 仅恢复导入和路径接线，并核对原函数 AST/原文件及所选分布元数据的哈希。`WORKBOOK_REFERENCE.json` 为用户统计表的只读摘录，原表没有概率列、没有 LSS 原始解，不能凭成本表认定其真实概率合格。

运行环境：求解器 Python 3.13.9；LSS 检验 Python 3.8、NumPy 1.24.4、SciPy 1.10.1。依赖分别见 requirements。原始基准目录位于服务器 `/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/`，数据哈希见 `RAW_REFERENCE.json`。求解器将 python-flint 安装在任务根目录的 `vendor313/` 后使用；如安装在环境 site-packages，也可直接导入。

```bash
python3.13 -m pip install --target vendor313 -r requirements_solver.txt
python3.13 frozen_candidate/run.py --instance /path/to/benchmark/LAB_3_5_30_ --capacity 11 --seed 930001 --seconds 600 --out /path/to/new_run.json.gz
python3 lss_real_eval.py --instance /path/to/benchmark/LAB_3_5_30_ --capacity 11 --selection '[12,10,5]' --out /path/to/new_LSS_test.json
```

正式监督脚本使用服务器环境绝对路径；迁移机器时应显式调整 Python 和基准目录。不要修改冻结源文件后仍使用同一轮注册记录。

此前 S2 的 1200 次整数经验可行性实验只能作为诊断；在统一 LSS 检验下仅 900/1200 合格，不能当作本轮完成。原 CDF Best 也必须接受同一检验，不能把未通过的原成本直接当成可行的最优目标。最终报告会同时列出全部 40 例的合格数、成本统计、旧 Best 的概率及成本差距。

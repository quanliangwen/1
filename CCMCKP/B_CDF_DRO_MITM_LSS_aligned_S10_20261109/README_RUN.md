# S10源码运行说明

原样本可行阈值0.99，原LSS真实概率验收阈值0.985。尾部重构/硬筛已全部删除。

## 环境

本版本在Linux服务器测试。求解器Python3.13.9，NumPy2.4.0，SciPy1.17.1，python-flint0.8.0；安装到包根目录vendor313。LSS使用独立Python3.8.10、NumPy1.24.4、SciPy1.10.1、Pandas2.0.3，保持随机数流和原生成函数一致。

```bash
python3.13 -m pip install --target vendor313 -r requirements_solver.txt
```

## 单例完整流程

```bash
python3 solve_one.py --instance /home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_3_5_30_ --capacity 21 --seed 966101 --seconds 600 --out-dir /path/to/new_output --solver-python /home/junhao/miniconda3/bin/python --lss-python /usr/bin/python3
```

输出目录必须尚不存在。search.json.gz是原样本搜索及候选；RESULT.json是完整LSS后筛选的最终合格结果，所有拒绝记录一并保留。直接把search.json.gz中的原样本最低成本当最终合格解，会绕过真实概率验收。

solve_one.py是交付用单例便捷入口，调用与正式实验相同的冻结worker和原LSS检验。40×30正式试验由formal_campaign.py与validate_portfolio.py执行，并未使用该便捷入口。例子不属于正式1200次统计。

## 完整40×30复现

基准数据是用户原始benchmark目录；数据和源码SHA见RAW_REFERENCE.json及REFERENCE_SHA256.json。监督脚本使用测试服务器原Python与基准路径，迁移时须显式调整绝对路径和验证进程python3命令。必须在新的包目录运行，已有formal30/validation结果不会被覆盖。

```bash
python3 formal_campaign.py
python3 validate_portfolio.py formal
python3 audit_final_certificates.py
```

可在独立终端并行启动这三个脚本，验证与证书审计会等待各自输入。正式种子960001–960030、每次600秒、固定LSS种子832273和1000万次。REGISTRATION.json与PRE_REGISTRATION_REMOTE_VERIFIED.json保留原冻结登记及远端核验；若改源码，需要新登记，不能把变更后的结果称作原冻结版本复现。

完整流程分为样本搜索与LSS后筛选。后筛选会读取真实分布元数据并参与最终选择，但不向样本搜索反馈。LSS额外计算量（含被拒绝候选）单列；原Best只供事后比较，不进入求解器。相同固定种子LSS向量在批量验证中按key复用，搜索始终独立。

压缩包中的frozen_candidate与正式1200次运行逐文件SHA一致；交付只补充单例入口、运行说明和冻结回执。S10_PREREGISTERED_SOURCE.zip保留正式试验之前的原始源码归档。

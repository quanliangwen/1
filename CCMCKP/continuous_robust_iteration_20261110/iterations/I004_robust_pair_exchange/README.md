# I004：10次搜索已结束，真实概率验收待进行

预注册并远端核验后启动的五例配对开发试验：35/37/38/39/40，none与pair_exchange各一次，独立搜索种子970401，每次600秒，2个开发搜索进程。18个优化器源文件保持冻结，10次搜索均在预算内结束，无运行错误。搜索快照和SHA清单明确标为search-only。

方法是在多个自身搜索得到的风险中心进行两组联合替换，使用鲁棒有限支持CDF分数提出向量，再以全部原始观测的整数概率下界≥0.99筛选；没有额外尾部硬筛。源码不读历史向量、真实分布参数或验收缓存。

35/37/38的已生成池没有比现有I002合格成本更便宜的候选。39的pair_exchange池中有215个更便宜的样本合格向量，其中178个不在原I002开发池；40对应116个，其中101个新向量。它们是否满足原LSS点估计≥0.985尚未验收，不能声称新增降本。外部验收进程明确等待F001完整验证结束。

I004_SEARCH_ONLY_RECORDS.zip包含18个源文件、登记/启动、全部10次候选输出及日志、池分析、输入SHA和驱动脚本。尚无LSS结果，不是30次Avg/Std。工程阶段两次试跑和1107项数学对照亦单独保留。成功标准是同时超过配对none和已有I002合格成本，之后才做新种子稳定性与新的40×30。

搜索复现环境：Python3.13.9、numpy2.4.0、scipy1.17.1、python-flint0.8.0。恢复原benchmark和任务目录结构后，用新输出名运行，例如：

```bash
python iterations/I004_robust_pair_exchange/candidate/run.py --instance /home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_50_10_500_ --capacity 100 --seed 970401 --seconds 600 --risk-method pair_exchange --phase-seconds 180 --out iterations/I004_robust_pair_exchange/reproduce.json.gz
```

原LSS使用原Python3.8环境及未修改21个源码，固定10m、种子832273、sum≤T点估计≥0.985，在外部按成本顺序选择，身份相同的调用复用并单独披露。完整原LSS源码可见主目录的I002冻结源码包。当前搜索快照不冒充已完成这一验收阶段。

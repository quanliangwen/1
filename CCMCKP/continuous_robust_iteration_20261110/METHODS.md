# 方法与验收

I001的CVaR子问题采用有限场景尾部权重：w非负、权重和为1、每个权重不超过1/(epsilon*N)，对资源总量取最坏加权平均。实现用排序构造权重，并以独立线性规划及CVaR原始表达式交叉核对；对当前候选的最坏权重生成线性割。它是搜索子问题，不能把CVaR≤T当作本项目新增的最终可行性条件。

CVaR原始表达式与场景优化参考：[Rockafellar与Uryasev原文](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf)。离散场景含质量点的定义参考：[一般损失分布的CVaR](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf)。本实现的权重和割平面构造是针对离散经验场景的实现，数学模块对照记录在RISK_MATH_CHECK.json。

Γ子问题使用样本均值mu和样本分位数偏差d，考虑0≤z≤1、sum(z)≤Γ的预算盒集合。固定非负pivot时，mu+max(d-pivot,0)作为线性系数，容量右侧减去Γ*pivot，生成成本较低的组合。只枚举有限pivot网格作为提案，不宣称穷尽全部鲁棒最优解。预算不确定集和线性等价形式参考：[Bertsimas与Sim，The Price of Robustness](https://www.mit.edu/~dbertsim/papers/melvyn/The-Price-Of-Robustness-OR52.pdf)。

全部提案面对相同最终谓词：全部原样本的精确计数下界≥0.99，随后原LSS real_P_test、1000万次、固定种子832273、sum≤T、点估计≥0.985。样本风险模型不读取真实分布，外部检验参与最终候选选择且不向搜索反馈。本流程仍属“样本搜索＋LSS后筛选”，不能宣传为完全不使用真实参数参与最终选择的纯样本算法。

本轮为开发试验，基准已用于方法设计；不作为未见实例泛化实验。旧Best不默认可行，Cost低于旧Best但验收失败不能算改善。

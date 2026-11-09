# 方法与验收

I001的CVaR子问题采用有限场景尾部权重：w非负、权重和为1、每个权重不超过1/(epsilon*N)，对资源总量取最坏加权平均。实现用排序构造权重，并以独立线性规划及CVaR原始表达式交叉核对；对当前候选的最坏权重生成线性割。它是搜索子问题，不能把CVaR≤T当作本项目新增的最终可行性条件。

CVaR原始表达式与场景优化参考：[Rockafellar与Uryasev原文](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf)。离散场景含质量点的定义参考：[一般损失分布的CVaR](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf)。本实现的权重和割平面构造是针对离散经验场景的实现，数学模块对照记录在RISK_MATH_CHECK.json。

Γ子问题使用样本均值mu和样本分位数偏差d，考虑0≤z≤1、sum(z)≤Γ的预算盒集合。固定非负pivot时，mu+max(d-pivot,0)作为线性系数，容量右侧减去Γ*pivot，生成成本较低的组合。只枚举有限pivot网格作为提案，不宣称穷尽全部鲁棒最优解。预算不确定集和线性等价形式参考：[Bertsimas与Sim，The Price of Robustness](https://www.mit.edu/~dbertsim/papers/melvyn/The-Price-Of-Robustness-OR52.pdf)。

全部提案面对相同最终谓词：全部原样本的精确计数下界≥0.99，随后原LSS real_P_test、1000万次、固定种子832273、sum≤T、点估计≥0.985。样本风险模型不读取真实分布，外部检验参与最终候选选择且不向搜索反馈。本流程仍属“样本搜索＋LSS后筛选”，不能宣传为完全不使用真实参数参与最终选择的纯样本算法。

本轮为开发试验，基准已用于方法设计；不作为未见实例泛化实验。旧Best不默认可行，Cost低于旧Best但验收失败不能算改善。

I002按有限支持CDF扰动生成多个风险中心的局部线性提案，交换2/4/8组。其单组替换导数已与直接卷积对照54次。邻域的降本上限相对于各中心设置，避免全程受最便宜原样本解的成本上限限制。扰动分数只引导提案，全部输出仍用原样本0.99和原LSS0.985验收。

I003使用椭球不确定集a=mu+diag(sd)u、||u||2<=k，最坏资源为mu*x+k*sqrt(var*x)。参考[Ben-Tal与Nemirovski，Robust Convex Optimization](https://www2.isye.gatech.edu/~nemirovs/MOR_RCO_1998.pdf)。sqrt在给定方差区间内用割线下界生成MILP提案，区间自适应细分；这是本任务的提案实现，不宣称论文给出了本启发式或99%验收保证。求解器限时状态与mip_dual_bound含义按[SciPy milp官方文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)区分，本轮不作全局最优证明。


## I005成本界限

本轮从CDF顺序和独立卷积的基本性质推导成本折扣乐观上界：对每组取`Gg(t)=max_j exp(-lambda*(cj-mincg))*Fgj(t)`，则成本不高于C的任意选择均有`P(sum<=T)<=exp(lambda*(C-sum mincg))*(convolution Gg)(T)`。无条件和两组分块版本在7例中仍过松，完整负结果保留，未作为最终硬筛。

随机序、离散卷积和量化误差的基础概念参考[Marković等，On the Convolution Efficiency for Probabilistic Analysis of Real-Time Systems，ECRTS2021](https://www.es.mdu.se/pdf_publications/6263.pdf)。成本折扣和本轮分支实现是这里的推导，不宣称该论文提出了本算法。

固定部分组后，lambda=0的乐观CDF上界明显加强，因此改用精确十进制样本向下量化和整数卷积作分支定界。核心算法与独立审计采用不同CDF构造和卷积组合顺序；审计同时检验前缀无重叠以及覆盖组合数。12个独立小输入、24条成本线共649项穷举对照通过。仅在完整耗尽、无未决、没有可行叶子时才声明该成本线被排除。原LSS点估计门槛保持0.985，新的数学证明只做原样本必要条件排除；正向联合可行上界必须另有原LSS合格见证。

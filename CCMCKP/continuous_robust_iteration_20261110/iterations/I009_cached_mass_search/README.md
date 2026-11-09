# I009：缓存CDF增量，等价加快上界核计算

沿用I008的原始样本、精确成本、后缀表和全部验收条件，仅把前缀质量与后缀CDF的逐项点积，改成与缓存CDF增量的整数多项式卷积后累加。9000项实测整数结果逐项相同，新的小模型41989项及4个确定性边界模型再次通过。

编号35同一旧成本线、512/256格、48位概率、120秒工程预算：118.003秒预算退出，DP12.487秒，访问204700节点，182135项概率上界剪枝、513个原样本不合格叶子、1578项成本剪枝，无可行或未决叶子。访问节点比I008的163979多约25%，但覆盖仍约99.5878%，剩余约0.4122%，说明推进到了难分支。并发资源未作受控隔离，节点/计时只按原始工程记录解释，不宣称最终算法提速或降本。

仍然没有全局排除结论，没有新的原LSS调用，没有新的合格成本；不替换正在执行40×30的正式版本。独立审计记录在证据包中逐项保存。下一轮倾向按成本条件概率上界和鲁棒分数安排候选搜索顺序，先找更便宜可行候选，再决定是否扩大证明预算；尚未实现的方案另有明确标记。

环境与输入要求同I008：Python3.13.9、numpy2.4.0、scipy1.17.1、python-flint0.8.0，原benchmark按RAW_REFERENCE.json恢复。在证据包解压根目录中运行：

```bash
python iterations/I009_cached_mass_search/candidate/run_search_bound.py --instance /home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_30_10_500_ --capacity 58 --cost-limit 193.774222960923 --time-bins 512 --cost-bins 256 --bits 48 --seconds 120 --out iterations/I009_cached_mass_search/reproduce/tree.json
python audit_i009_search.py --trial probe35_old
```

复核时使用临时解压副本，先另存已有INDEPENDENT_AUDIT.json，程序拒绝覆盖原记录。数学检查可在另取新目录名后重跑。标量历史成本目标已明确披露，没有向优化器输入历史向量、真实参数或LSS缓存。

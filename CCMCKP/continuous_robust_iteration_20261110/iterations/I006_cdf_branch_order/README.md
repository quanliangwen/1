# I006：用CDF上界决定分支顺序

这是有时限的数学求解工程试验，没有产生新的LSS合格降本结果，也不是40×30统计。

思路：乐观CDF包络对所有未分配组取各选项CDF的逐点最大值，可能把不同选项的优势拼在一起。先对每一组的每个实际选项计算精确整数上界，按可提前剪掉的选项数排序；只改变搜索顺序。原样本全部保留、严格事件sum<T的概率下界≥0.99、外部原LSS验收≥0.985均不变。没有新增尾部硬筛。浮点预诊断只用于提出思路；实际排序分数使用精确整数卷积。

验证：12个独立小模型，24次成本线试验，627项全枚举检查通过，包括每个剪枝子树的真实概率、精确成本、叶子原组顺序恢复、完整前缀分区。源码4个Python文件与检查记录的SHA一致。

编号35（APP_30_10_500_，T=58）在相同512格和120秒工程预算下，以第12组开始。118秒预算退出，访问178534节点，152259个CDF剪枝、8420个成本剪枝，覆盖约96.90%的组合空间，仍有未处理分支；没有找到原样本合格叶子，没有全局排除结论。自然顺序另一次试验覆盖约97.79%。这两次计算有其他任务并行，不能作受控速度对比；首层可剪枝更多也没有带来更好的全树覆盖，因此目前不替换正式求解器。

独立审计使用另一种阈值CDF构造、平移后的平衡整数卷积与前缀树分区，逐项重算证书。最终审计身份、完整源代码、全部小模型、未完成前沿及原始日志在证据包和清单中保留。

复现环境：Python3.13.9、numpy2.4.0、scipy1.17.1、python-flint0.8.0。解压证据包后，以解压根目录作为工作目录，把原始benchmark放回原路径（或相应调整路径）；原始数据不重复打包，SHA见RAW_REFERENCE.json。`vendor313`只是运行环境依赖的可选搜索路径，标准安装依赖也可使用。

```bash
python check_i006_math.py math02
python iterations/I006_cdf_branch_order/candidate/run_bound.py --instance /home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_30_10_500_ --capacity 58 --cost-limit 193.774222960923 --bins 512 --seconds 120 --out iterations/I006_cdf_branch_order/case35/reproduce.json
```

每次使用新输出文件，避免覆盖证据。正式记录以REGISTRATION、run元数据和清单SHA为准。审计命令：`python audit_i006_proof.py --result case35/probe_old_512_120.json --registry case35/REGISTRATION.json`，先删除/另存解压包中已有的同名审计输出再复核；不要覆盖原证据归档。该审计不调用原生真实概率仿真，不读取真实分布参数。

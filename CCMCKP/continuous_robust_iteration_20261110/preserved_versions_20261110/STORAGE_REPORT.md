# CCMCKP服务器磁盘和运行内存盘点

本次只保存、只读盘点，未删除或移动既有服务器文件。I1016按此前I016处理，三个源代码版本12/16/22文件均已逐一SHA核对。

|分类|已测磁盘占用|
|---|---:|
|S10、I002、I016直接目录及现有实验结果|1.048 GiB|
|当前工作区其它试验及辅助文件|0.533 GiB|
|旧CCMKCP/work历史实验，可访问部分|至少3.669 GiB|
|上面两项“其它”合计|至少4.202 GiB|
|共享依赖、验证缓存和交付副本|0.176 GiB|
|原始公共算例数据|68.65 MiB|

“其它”是磁盘占用分类，不是自动删除清单；原始数据和共享依赖另列。旧历史目录有8个无法读取，因此上述历史占用和总计是下界，不能称为全盘完整总量。当前账号工作目录合计1.757GiB，包括保留版本、其它试验和共享文件，不能与子目录再重复相加。

盘点时当前账号可见CCMCKP相关进程合计RSS 14.77MiB，PSS 7.45MiB；主要是旧监测进程及父shell。RSS包括共享页重复计数，PSS按共享页比例分摊。它们与磁盘空间是两回事。新60并行实验尚未启动。

根分区可用空间在盘点时为230.20MiB；它相对先前0值已有变化，本次没有执行清理。数据是文件CCMCKP_STORAGE_AND_MEMORY.json所载时间的快照。

## 最大可见其它历史目录

|目录|占用|
|---|---:|
|codex_B_DRO_R08_20261102|2130.00 MiB|
|v50_all40x30_20261007|372.23 MiB|
|codex_v50_dro_ablation_20261016|232.50 MiB|
|codex_B_DRO_R04_20261101|209.84 MiB|
|codex_v50_dro_i01_20261017|90.47 MiB|
|codex_robust_v37_all40_20261005|88.51 MiB|
|codex_B_Gamma_EPS_20261109|74.95 MiB|
|codex_B_DRO_R08F_20261102|56.95 MiB|

## 未能读取的历史目录

- du: cannot read directory '/home/junhao/quan/parallel_test_solver/CCMKCP/work/stage3_test_20261107': Permission denied
- du: cannot read directory '/home/junhao/quan/parallel_test_solver/CCMKCP/work/stage1_test_20261106': Permission denied
- du: cannot read directory '/home/junhao/quan/parallel_test_solver/CCMKCP/work/stage1_callback_20261106': Permission denied
- du: cannot read directory '/home/junhao/quan/parallel_test_solver/CCMKCP/work/codex_robust_v37_20261005': Permission denied
- du: cannot read directory '/home/junhao/quan/parallel_test_solver/CCMKCP/work/stage1_final600_20261106': Permission denied
- du: cannot read directory '/home/junhao/quan/parallel_test_solver/CCMKCP/work/stage4_test_20261107': Permission denied
- du: cannot read directory '/home/junhao/quan/parallel_test_solver/CCMKCP/work/codex_robust_v14_20261005': Permission denied
- du: cannot read directory '/home/junhao/quan/parallel_test_solver/CCMKCP/work/stage2_test_20261107': Permission denied

逐目录字节、占用口径、进程PID和权限限制详见JSON。没有扫描其它用户所有私人目录，因此也不把根盘全部已用空间归因于这些CCMCKP目录。

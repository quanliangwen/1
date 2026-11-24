# S10 / EGS：全样本抽样与LSS统一验收修正版

版本：2026-11-24，`S10_LSS_full_sample_v2`。一个C++程序提供原S10与椭球EGS两条主搜索，二者共用本次修正。

## 变更

- LSS蒙特卡洛使用`numpy.below(L)`：500个样本抽取索引0—499；30个样本抽取0—29。
- 搜索预筛中的同类PCG索引上界同步改为L；原始经验样本整数证书仍使用全部L样本。
- 最终输出只以LSS概率`>=0.99`验收，仍沿用原LSS精确/蒙特卡洛分支、默认100万次MC及严格事件`sum<T`。
- 保留原成本队列与概率队列每项两次复检的调用次数；不抽样到通过为止。每个方案以本次运行中最后一次LSS结果为唯一值，两队列和三个输出变体统一使用该值。
- 修正概率队列复检写回错误，过滤所有最后LSS值低于0.99的方案。若成本队列无通过项，可使用本次概率队列已有的通过方案；若全部失败则写明原因并返回失败，不输出假成本或历史解。
- 完全移除按`_dist.txt`生成样本的额外真实概率计算。程序不再读取该类文件；`--real`参数、JSON真实概率字段及CSV真实概率列已移除，`real_probability_reporting=false`。
- 记录全部LSS调用和负观测，最终验收值可在`ORIGINAL_LSS_DECISION_TRACE.json`中追溯。

原始经验样本证书保留为搜索内部判据；最终输出不叠加生成分布概率门槛。初始化仍由每次运行自行生成。MITM、椭球目标/OA、gamma和搜索预算政策保持原样；本次不作新的算法效果声明。

## 编译

需要64位GCC或Clang、GMP/GMPXX及可用Gurobi C库/头文件。源码不附求解器或许可证。

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DS10_GUROBI_ROOT=/path/to/gurobi
cmake --build build --parallel 2
```

也可分别设置`S10_GUROBI_INCLUDE`、`S10_GUROBI_LIBRARY`和`S10_GMP_ROOT`。本次实际服务器以Gurobi11.0.3编译并验证。

## 两种搜索共用同一验收器

```sh
# 原S10
build/ccmckp_s10 --instance /data/LAB_50_10_500_ --capacity 63 --seed 960001 --rep 1 --seconds 600 --out new_run_S10 --search-flow frontier_mitm
# 椭球EGS
build/ccmckp_s10 --instance /data/LAB_50_10_500_ --capacity 63 --seed 960001 --rep 1 --seconds 600 --out new_run_EGS --search-flow ellipsoid_oa --ellipsoid-gamma 2.4
```

输出目录必须是新目录。默认流程为`ellipsoid_oa`；`--ellipsoid-gamma 0`可运行零风险项消融。未切换原600秒搜索、45秒余量的政策，LSS后处理仍在搜索时钟外。`--search-only`仅供内部搜索诊断，不产生通过最终LSS的正式输出。

## 输出格式

`RESULT.json`仅在有LSS通过解时生成。主输出`original_LSS_confidence>=0.99`，所有`original_output_variants`亦必须达到该阈值；同一选择在各变体中的概率一致。

旧字段`recorded_real_probability`、变体`real_probability`不再存在。新版主CSV列为`Times,Cost,Confidence Level,Evaluation Times,Solution,Running Time`。`_record.csv`是历史入队记录，最终验收以RESULT和最终验收trace为准。

## 针对性回归验证

```sh
cmake -S . -B build -DS10_GUROBI_ROOT=/path/to/gurobi -DS10_BUILD_LSS_TESTS=ON
cmake --build build --parallel 2
python tests/create_fixture.py build/fixtures/LAB_3_2_500_
build/lss_fix_test build/fixtures/LAB_3_2_500_ build/unit_output
```

测试覆盖最后一项可抽到、最后一个样本会影响LSS结果、后续失败覆盖先前通过、三变体使用同一最后LSS值、全部失败不输出、没有抽到通过为止。测试回调仅在独立测试目标启用，正式程序不包含该测试入口。

服务器已额外完成原S10、EGS2.4、EGS0三条真实生产入口的微型集成测试，全部不提供`_dist.txt`，并验证JSON、CSV和最终trace。验证记录见发布目录。没有额外真实概率MC，没有重新运行270次大算例或全40例。

旧试验及旧源码保持不变。新旧LSS抽样范围和最终验收行为不同，后续性能比较应使用本修正版在同批新运行中对照，不混用旧成绩。

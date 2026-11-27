# R07复现说明

报告区分6例各5次的精准冒烟与条件全40例评测。门槛失败时不生成全40例成绩，不得把本批数据复制补成30次。

冻结源码使用C++17、GMP和Gurobi11；商业SDK和许可证不分发。通过source/CMakeLists.txt显式源码清单构建；遗留的.tmp组装草稿不参与编译。

```sh
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release \
  -DS10_GUROBI_INCLUDE=/path/to/gurobi/include \
  -DS10_GUROBI_LIBRARY=/path/to/libgurobi110.so
cmake --build build --target ccmckp_s10 -j4
```

主入口flow为`adaptive_dual_gated`。单个新实验必须用新的输出目录。正式严格完整时钟应由已冻结controller.py从Popen前传入CCMCKP_LAUNCH_MONOTONIC，并按独立wait线程记录进程退出时间；直接运行CLI只供功能复现，不能冒称与本报告相同的完整启动时钟。

```sh
build/ccmckp_s10 --instance /path/to/benchmark/LAB_10_20_500_ \
  --capacity 12 --seed 1075001 --rep 1 --seconds 600 \
  --manifest source/BENCHMARK_MANIFEST.json \
  --search-flow adaptive_dual_gated --out NEW_OUTPUT_DIRECTORY
```

原始40例benchmark需使用SOURCE包中BENCHMARK_MANIFEST.json相同SHA的数据。合成tiny输入单独提供于R07_tiny_validation_inputs.zip，可运行validate_remote.py中的三个完整集成；脚本中的工作根目录需适配，但原始报告仅对应冻结服务器、工具链、源/input SHA和注册seed。

R07模型：r07_budget.cpp、r07_search.cpp、r07_polish.cpp。硬看门狗：isolated_native.hpp。独立读者：r07_reader.py、adaptive_r07_reader.py、interval_reader.py、r05_fft_reader.py与audit_reader.py；读者不调用优化器或新增MC。

压缩证据分片按证据分片清单.json，用merge_evidence.py合并；脚本逐片及整体SHA256核验，拒绝覆盖既有合并文件。原始成功/失败/未知、全部LSS负观测都在归档中，不能删除负观测后重算成绩。CHECKSUMS_SHA256.json涵盖发布的每个文件。

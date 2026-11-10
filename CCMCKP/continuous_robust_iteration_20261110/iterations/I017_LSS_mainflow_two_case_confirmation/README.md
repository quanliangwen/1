# LSS原主流程：两例已实跑确认

当前口径：原LSS评估函数与CL=.99，原始最小成本输出_0；真实概率只记录，不作硬筛。原Construct_Procedure、候选池更新、_0/_1/_2及前十输出、param_test和CSV写入代码保持原样，只替换小例搜索阶段。没有自有整数证书的额外输出筛选。

|算例|T|新运行原始_0成本|原LSS置信度|原LSS真实概率记录|搜索秒|
|---|---:|---:|---:|---:|---:|
|APP_3_5_30_|21|9.034717|0.992481481481|0.9651546|0.630891|
|APP_3_5_30_|27|7.250013|0.995518518519|0.9713810|1.286517|

两例均是新进程从头运行，各一次，不是复制旧结果，也不是40×30统计。真实概率低于旧.985筛选线仍保留输出，符合原LSS主实验记录流程；原21份参考源码SHA及原始CSV、原输出段AST均已核验。

[确认结果CSV](CONFIRMED_OUTPUT.csv) · [核验记录](VERIFIED_TWO_OUTPUTS.json) · [源码ZIP](I017_LSS_MAINFLOW_TWO_CASE_SOURCE.zip) · [完整实际CSV、日志及源码证据](I017_TWO_CASE_ACTUAL_MAINFLOW_EVIDENCE.zip)

原生环境：Python3.8、NumPy1.24.4、SciPy1.10.1。源码包解压为任务根后，在原服务器数据路径可分别运行：

```text
python3 run_lss_mainflow_confirmation.py --capacity 21
python3 run_lss_mainflow_confirmation.py --capacity 27
```

程序拒绝覆盖已运行目录。该分支目前只确认用户指定的两个小例；大例与40×30尚未按新口径重新验证。之前双门槛实验保留为不同口径历史记录，不再代表当前与LSS的公平比较。

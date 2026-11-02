# parallel_test_solver 四项文件迁移

日期：2026-11-02（Asia/Shanghai）。源服务器：`junhao@10.112.162.60`。
源目录：`/home/junhao/quan/parallel_test_solver`。

共 **8,623 个原始文件**，原始实际磁盘占用 **7.45 GiB**；压缩包合计 **1.72 GiB**。
本仓库使用 [Release 附件](https://github.com/quanliangwen/1/releases/tag/server-migration-20261102) 存放完整大文件，各项包内保留服务器上的原名和目录结构。并非只上传索引、空文件或本地路径。

| 原始目录或文件 | 原始文件数 | 原始磁盘占用 | 完整压缩包 |
|---|---:|---:|---|
| `A=problem1` | 988 | 3.23 GiB | [A_problem1.tar.gz](https://github.com/quanliangwen/1/releases/download/untagged-df360b840757b8303bc9/A_problem1.tar.gz) |
| `model_q2_no_solution.mps` | 1 | 2.13 GiB | [model_q2_no_solution.mps.tar.gz](https://github.com/quanliangwen/1/releases/download/untagged-df360b840757b8303bc9/model_q2_no_solution.mps.tar.gz) |
| `CCMKCP-gurobi` | 7430 | 1.22 GiB | [CCMKCP-gurobi.tar.gz](https://github.com/quanliangwen/1/releases/download/untagged-df360b840757b8303bc9/CCMKCP-gurobi.tar.gz) |
| `A=problem3` | 204 | 0.86 GiB | [A_problem3.tar.gz](https://github.com/quanliangwen/1/releases/download/untagged-df360b840757b8303bc9/A_problem3.tar.gz) |

`CCMKCP-gurobi` 的任务索引按要求放在 [`CCMCKP/server_migration_20261102/CCMKCP-gurobi`](https://github.com/quanliangwen/1/tree/main/CCMCKP/server_migration_20261102/CCMKCP-gurobi)。

## 校验

1. `source_manifest.json`：所有原始文件逐一 SHA256，以及路径、目录、权限等元数据。
2. `archive_manifest.json`：四个压缩包的实际 GitHub 资产、大小和 SHA256。
3. `REMOTE_VERIFICATION.json`：GitHub 服务端摘要及从 GitHub 完整下载后的 SHA256 核验结果。
4. 四个压缩包都已解读并与原始文件清单逐一比较，8,623个文件全部一致，目录及空目录保留。

## 下载和恢复

从上表下载所需压缩包，同时下载此目录中的 `SHA256SUMS.txt`。四项都下载齐时运行：

```sh
sha256sum -c SHA256SUMS.txt
tar -xzf A_problem1.tar.gz
tar -xzf model_q2_no_solution.mps.tar.gz
tar -xzf CCMKCP-gurobi.tar.gz
tar -xzf A_problem3.tar.gz
```

压缩包解开后分别得到 `A=problem1/`、`model_q2_no_solution.mps`、`CCMKCP-gurobi/`、`A=problem3/`。
这里完整保存原件，不合并重名MPS，也不删除日志、结果、缓存等原目录内容。

## 服务器移除状态

本提交时，GitHub资产和逐文件清单已完成核验，服务器原件仍保留。只有重新确认原件未变化且没有相关任务运行后才移除；最终状态将追加到 `SERVER_MOVE_RECEIPT.json`。
临时上传暂存不作为本地交付或永久备份，迁移完成后会清理。

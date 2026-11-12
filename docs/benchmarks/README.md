# Benchmark artifacts

`latest.json` 由 `bench_goals` 写出（`make bench`），结构见 `docs/BENCHMARK.md`。

约定：

- `latest.json` **提交进仓库**，因为 README 表格引用它；
- 原始 JSONL 与 CSV 不入库（`.gitignore` 已排除），避免仓库膨胀；
- 每次发版前用当前 commit 重跑一次并刷新 `latest.json`，`meta.git_sha` 必须与 `git rev-parse HEAD` 一致，
  否则表格里的数字说明不了当前代码。

目录当前为空是**故意的**：在没有真实基准运行结果之前，README 表格保持 `—`。

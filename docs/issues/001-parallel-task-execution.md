# 为 `sd-hwe-bench run` 添加 `--jobs` 参数以支持并行任务执行

## 状态

**已实现**，2026-06-25。

实现概要：

- `src/sd_hwe_bench/commands/run.py` 新增 `--jobs` / `-j` 选项，默认 `-1` 表示自动选择 `min(4, cpu_count)`，`1` 表示串行。
- 使用 `concurrent.futures.ProcessPoolExecutor` 进程池并发执行 `(task_id, attempt)` rollout。
- `Workspace.create()` 增加 `attempt` 参数，目录名加入 `_aNNN` 后缀以避免并发冲突。
- 新增 `tests/test_run_parallel.py` 覆盖串/并行行为与目录唯一性。

## 动机

SD-HWE-Bench 目前已将评分（`piki check`）和交付物生成（`piki generate`）放到容器（`docker` / `podman`）中执行。这使得评分阶段天然具备隔离性和可并行性。然而，当前的 `sd-hwe-bench run` 命令仍然是串行执行：

```python
for tid in task_ids:
 for attempt in range(passes):
 ... # 一次只跑一个 rollout
```

在计划的 M2 阶段（30+ 任务 × 多个 Actor × pass@5），串行执行将成为瓶颈。仅一个 canonical 工程就能产生 14 个任务；如果 3 个 Actor 各跑 5 轮，就是 210 个相互独立的 rollout。

## 目标

为 `sd-hwe-bench run` 增加 `--jobs` / `-j` 选项，使多个 `(task_id, attempt)` rollout 能够并行执行。

```bash
sd-hwe-bench run telecom/ --actor kimi --passes 5 --jobs 4
```

## 为什么现在可以并行

1. **Workspace 隔离**：`Workspace.create()` 为每次 rollout 生成独立目录（`runs/<timestamp>_<task>_<actor>_<model>/`），并行 rollout 不会共享项目文件。
2. **容器隔离**：每次 `score_task()` 都会启动独立容器并挂载独立卷，运行时状态互不干扰。
3. **Actor 状态隔离**：`KimiActor`、`CodexActor`、`GeminiActor` 均以 `cwd=workspace_root` 启动子进程调用 CLI，不修改 benchmark 框架内的全局状态。

## 风险与待验证问题

| 风险 | 待评估的缓解措施 |
|---|---|
| Agent CLI 全局锁 | 在同一主机上测试并发 `kimi` / `codex` / `` 进程。某些 CLI 可能存在单实例锁或共享锁文件。 |
| API 限流 | 模型服务商（Kimi / OpenAI / Google）可能因并发调用触发速率限制。`--jobs` 应能按 Actor/模型 灵活配置。 |
| 容器资源争用 | 同时启动过多 `docker run` 会消耗 CPU/内存。默认 `--jobs` 应保守，例如 `min(4, os.cpu_count())`。 |
| 控制台输出顺序 | 并行 worker 同时输出会交错。需要按 job 加前缀，或等全部结束后再汇总打印。 |
| 可复现性 | Actor 本身可能非确定性；每个 rollout 的随机种子和行为仍需记录在 `manifest.json` 中。 |

## 建议设计

### CLI 变更

在 `src/sd_hwe_bench/commands/run.py` 中增加：

```python
jobs: int = typer.Option(
 1, "--jobs", "-j",
 help="最大并行 rollout 数量（任务 × 轮次组合）。",
)
```

### 并行单元

最小工作单元是一个 rollout：

```python
@dataclass
class RolloutJob:
 task_id: str
 attempt: int
 actor: str
```

### 执行器选择

建议使用 `concurrent.futures.ProcessPoolExecutor`，原因：

- Actor CLI 调用兼具 I/O 和 CPU 特性，Process 能避免 GIL 问题；
- 进程隔离可防止 Actor 库潜在的全局状态污染；
- `score_task()` 本身已使用子进程/容器调用，Process 是自然的扩展。

替代方案：`ThreadPoolExecutor`，仅在性能分析显示进程开销显著且已确认 Actor CLI 线程安全时使用。

### 输出处理

可选方案：

1. **静默运行 + 结束汇总**：每个 worker 只写自己的 `trajectory.jsonl` 和 `manifest.json`，主进程最后打印汇总表。
2. **Rich 进度条**：使用 `rich.progress.Progress`，每个 rollout 一个任务。
3. **缓冲日志**：worker 将日志写入按 job 区分的文件，主进程仅打印错误。

建议先从方案 1 开始（简单、稳健），后续可选增加进度条。

### 资源感知默认值

```python
default_jobs = min(4, (os.cpu_count() or 1))
```

## 验收标准

- [ ] `sd-hwe-bench run telecom/ --actor kimi --passes 3 --jobs 2` 能完成且不会产生 workspace 冲突。
- [ ] 与 `--jobs 1` 相比，结果一致（允许 Actor 非确定性带来的差异）。
- [ ] 每个 rollout 的 `manifest.json` 正确记录 `task_id`、`actor`、`attempt`、`success`。
- [ ] 控制台输出仍然可读（不会完全混乱交错）。
- [ ] 现有测试全部通过。

## 相关文件

- `src/sd_hwe_bench/commands/run.py`
- `src/sd_hwe_bench/sandbox/workspace.py`
- `src/sd_hwe_bench/actors/base.py`
- `src/sd_hwe_bench/scorer.py`

## 优先级

**M2（任务集扩展）** —— 在扩展到 30+ 任务并跑多模型基线之前必须实现。

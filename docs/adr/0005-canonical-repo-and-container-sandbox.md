# ADR 0005: Canonical 工程仓库组织与容器沙箱边界

## 状态

已提出 → **已通过**，2026-06-25。

## 背景

在将 SD-HWE-Bench 从 5 个手工 POC 任务扩展到基于 canonical ADL 工程的任务集过程中，需要确定：

1. canonical 工程仓库与 benchmark 框架仓库的关系；
2. 容器沙箱（container sandbox）应该覆盖哪些执行阶段；
3. 本地 Docker/Podman 环境不一致时的 workaround；
4. 任务并行执行的边界条件。

## 决策

### 1. Canonical 工程作为 Git submodule

每个 canonical ADL 工程是一个**独立的 Git 仓库**，并作为 `sd-hwe-bench` 的 Git submodule 放在 `canonical/<project-name>/` 下。

**首个 canonical 工程**：

- 路径：`canonical/telecom-rack/`
- 范围：单台 42U 电信机柜的完整部署（RACK、PDU、服务器、交换机、光纤连接、配合约束）
- 提交历史：15 个 commit（c00–c14），生成 14 个任务；每个 reference solution commit 都能通过 `piki check`

### 2. 任务通过 commit 历史提取

使用 `tools/extract_tasks.py` 从 canonical 工程的 `task_manifest.yaml` 与 Git 历史生成任务：

```bash
python tools/extract_tasks.py \
 --project-dir canonical/telecom-rack \
 --output-dir tasks \
 --validate
```

每个任务包含：

- `scaffold/` = commit `k`
- `solution/` = commit `k+1`
- `task.yaml` = 从 `task_manifest.yaml` 生成的元数据

### 3. 容器沙箱只覆盖 piki，不覆盖 Actor

容器镜像 `sd-hwe-bench-piki:latest` 只包含 `piki` 规则引擎，**不包含** Kimi Code / Codex /Claude Code 等 Actor CLI。

执行模型：

```text
宿主机 Actor (kimi/codex/...) → 修改 workspace/ → 容器内 piki check/generate
```

理由：

- Actor CLI 需要安装、登录态、API KEY 或订阅凭证，难以在容器内复用研究者已有的本地认证；
- piki 是确定性的规则引擎，容器化后能保证评分环境完全一致；
- 这种 "thin sandbox" 设计更符合现代 benchmark 的可复现性要求。

### 4. Containerfile 设计

```dockerfile
FROM python:3.12-slim
COPY . /src/piki
RUN pip install --no-cache-dir -e "/src/piki/adl" && \
 pip install --no-cache-dir -e "/src/piki"
WORKDIR /work
# 无 ENTRYPOINT：runner 直接传入 python -m piki <subcommand>
```

关键修改：

- 必须先安装本地 `adl` submodule，因为 PyPI 上同名 `adl` 不是 piki 的依赖；
- 不设置 `ENTRYPOINT`，与 `SandboxRunner` 的命令格式保持一致。

### 5. 评分流水线自动生成交付物

`score_task()` 在检查 `expected_deliverables` 之前，若传入了 `runner`，会自动调用 `runner.generate(project_dir)`。

这确保带交付物任务在 Actor 完成后无需额外手动步骤即可评分。

### 6. Docker Desktop DNS 问题的 workaround

本机 Docker Desktop 存在容器内 DNS 解析失败的问题（`Temporary failure in name resolution`），无法通过 `docker build` 成功构建镜像。

Workaround：

1. 使用 Podman 构建镜像；
2. `podman save -o image.tar sd-hwe-bench-piki:latest`；
3. `docker load -i image.tar`；
4. `docker tag localhost/sd-hwe-bench-piki:latest sd-hwe-bench-piki:latest`。

Docker 容器运行评分本身正常，仅 `docker build` 受影响。

### 7. Issue as Code

项目治理不依赖 GitHub Issues 系统。新增的需求、讨论和决策以 Markdown 文件形式存放在 `docs/issues/` 和 `docs/adr/` 中。

首个 Issue-as-Code：

- `docs/issues/001-parallel-task-execution.md`

## 结果

### 正面

- canonical 工程与 benchmark 框架解耦，便于独立版本控制和复现；
- 14 个新任务可一键从 canonical 工程提取，且全部通过容器内 `piki check`；
- 容器评分环境统一，CI/CD 可直接复用同一镜像；
- Actor 复用宿主机凭证和订阅，不增加 Token 成本。

### 负面 / 风险

- Docker Desktop DNS 问题未根本解决，需要 podman 辅助；
- Actor 仍在宿主机运行，实验可复现性受宿主机 CLI 版本影响；
- submodule URL 当前是本地相对路径 `./canonical/telecom-rack`，推送到远程仓库前需要改为真实 URL。

## 相关文件

- `canonical/telecom-rack/README.md`
- `canonical/telecom-rack/task_manifest.yaml`
- `tools/extract_tasks.py`
- `Containerfile`
- `src/sd_hwe_bench/sandbox/runner.py`
- `src/sd_hwe_bench/scorer.py`
- `docs/issues/001-parallel-task-execution.md`

## 参考

- ADR 0001：任务生成策略
- ADR 0003：任务提取工具与元数据 schema
- AGENTS.md §4：容器策略

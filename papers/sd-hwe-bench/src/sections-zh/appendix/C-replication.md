# 附录 C：复现说明

## C.1 环境配置

### 依赖

- Python 3.11+
- Docker（用于容器化 piki check 执行）
- 使用 `uv` 进行 Python 依赖管理

```bash
git clone <repo-url> sd-hwe-bench
cd sd-hwe-bench
uv sync
```

### 构建 piki 容器镜像

```bash
docker build -t sd-hwe-bench-piki:latest -f docker/Dockerfile.piki .
```

验证：

```bash
uv run sd-hwe-bench list
```

## C.2 单任务评分

```bash
# 列出全部任务
uv run sd-hwe-bench list

# 直接对已有方案评分
uv run sd-hwe-bench score telecom/comprehensive-001 tasks/telecom/comprehensive-001/solution/

# 运行 Agent 生成并评分
uv run sd-hwe-bench run telecom/comprehensive-001 --actor codex
```

## C.3 批量基线实验

```bash
# 全量任务，pass@1，无 repair
uv run sd-hwe-bench run --all --actor codex --passes 1

# 并行执行
uv run sd-hwe-bench run --all --actor codex --passes 1 --jobs 4

# Repair 循环消融
uv run sd-hwe-bench run-repair telecom/comprehensive-001 --actor codex --max-repair 5
```

结果写入 `runs/` 目录。

## C.4 Leaderboard 生成

```bash
# 从 runs/ 归档并更新 leaderboard
uv run sd-hwe-bench leaderboard --update

# 查看当前 leaderboard
uv run sd-hwe-bench leaderboard
```

## C.5 数据与代码

- 任务数据集：`tasks/telecom/`（37 个任务）
- Canonical 工程源码：`canonical/`（5 个工程）
- 评测框架：`src/sd_hwe_bench/`
- DTS 规则配置：`src/sd_hwe_bench/config/rule_layers.yaml`

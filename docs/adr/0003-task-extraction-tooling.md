# ADR 0003: 任务提取工具与元数据 Schema

## 状态

已提出 → **已通过**，2026-06-24。

## 背景

根据 ADR 0001 和 ADR 0002，SD-HWE-Bench 将基于 2–3 个 canonical ADL 工程（Telecom / Datacenter / Mechanical）的顺序 commit 历史来生成任务。本 ADR 决定：

1. 如何从 commit 历史中提取任务；
2. 任务的元数据 schema；
3. 提取工具的入口、输入输出和工作流程。

## 决策

### 1. 任务即 commit 转移

每个任务对应 canonical 工程中相邻两个 commit 之间的状态转移：

- **scaffold**：commit `k` 的仓库快照（Agent 可见的初始状态）。
- **requirement**：对下一步设计的自然语言描述（由人工维护在 `task_manifest.yaml` 中）。
- **reference solution**：commit `k+1` 的仓库快照。
- **test suite**：对 commit `k+1` 运行 `piki check` 和交付物检查。

约束：**每个 commit 都必须是一个合法的 piki 项目**（至少能通过当前 plugin 集的检查），这样 reference solution 天然可作为评分标准。

### 2. 元数据 Schema

每个生成的任务包含一个 `task.yaml`，字段在现有 schema 基础上扩展：

```yaml
task_id: telecom/rack-expansion-001-step-03
name: 添加 PDU 冗余
source_project: canonical-telecom-rack
source_commit_from: c1a2b3c
domain: telecom
task_type: comprehensive
difficulty: medium
requirement: |
  当前机柜已有一台服务器 SRV-01 和 PDU-A。
  请为 SRV-01 添加第二路供电 PDU-B，并声明 PDU-B 与 SRV-01/power-b 的 IEC 配合。
  添加后功率预算仍须满足 PDU 容量 80% 阈值。

plugins:
  - telecom

expected_files:
  - instances/pdus/PDU-B.yaml
  - layouts/layout.yaml
  - mates/power-iec/PDU-B-SRV-01-B.yaml

scoring_layers:
  - L0
  - L1
  - L2
  - L3
  - L4

expected_deliverables:
  - bom-csv
  - power-budget

rubrics: []
```

新增字段说明：

| 字段 | 含义 |
|---|---|
| `source_project` | 来源 canonical 工程名称 |
| `source_commit_from` | scaffold 对应的 commit hash |
| `source_commit_to` | reference solution 对应的 commit hash |

### 3. 提取工具

工具入口：`tools/extract_tasks.py`

输入：

- `--project-dir`：canonical 工程仓库路径。
- `--manifest`：该工程根目录下的 `task_manifest.yaml`（默认）。
- `--output-dir`：任务输出目录（默认 `tasks/<domain>/`）。

`task_manifest.yaml` 示例：

```yaml
project: canonical-telecom-rack
domain: telecom
base_difficulty: medium
commit_history:
  - commit: "a1b2c3d"
    step: 0
    summary: "初始 scaffold：空项目，仅含 piki.toml 和 models/"
    is_scaffold_only: true
  - commit: "b2c3d4e"
    step: 1
    summary: "声明 RACK-A01 和两个 PDU"
    task_type: instance-declaration
    difficulty: easy
    requirement: |
      请声明 42U 标准机柜 RACK-A01 以及 PDU-A、PDU-B，两个 PDU 容量均为 2000W。
    expected_files:
      - instances/racks/RACK-A01.yaml
      - instances/pdus/PDU-A.yaml
      - instances/pdus/PDU-B.yaml
    expected_deliverables: []
  - commit: "c3d4e5f"
    step: 2
    summary: "添加服务器并更新 layout"
    task_type: layout-design
    difficulty: medium
    requirement: |
      在现有机柜中添加 SRV-01 和 SRV-02 两台服务器，分别部署在 U10 和 U14，并更新 layouts/layout.yaml。
    expected_files:
      - instances/devices/SRV-01.yaml
      - instances/devices/SRV-02.yaml
      - layouts/layout.yaml
    expected_deliverables: []
```

工作流程：

1. 读取 `task_manifest.yaml`。
2. 对每一对相邻 commit `(k, k+1)`：
   - 将 commit `k` 的文件导出到 `<output-dir>/<task-id>/scaffold/`。
   - 将 commit `k+1` 的文件导出到 `<output-dir>/<task-id>/solution/`。
   - 生成 `<output-dir>/<task-id>/task.yaml`。
3. 对每个 reference solution 运行 `piki check`，确保 0 错误。
4. 输出汇总报告：任务数量、类型分布、难度分布、通过/失败数。

### 4. 文件复制规则

- 排除 `.git/`、`.DS_Store`、`.sdhwe.*` marker 文件、以及 `dist/` 等生成目录。
- 保留 `piki.toml`、`models/`、`instances/`、`layouts/`、`mates/` 等声明文件。
- 如果某个 commit 包含交付物，也不复制到 scaffold/solution；交付物应由 Agent 通过 `piki generate` 重新生成。

## 结果

### 正面

- **自动化**：一次配置后可以批量生成数十个任务，极大降低 benchmark 扩展成本。
- **可追溯**：每个任务都能追溯到 canonical 工程的具体 commit，便于后续修正和版本更新。
- **一致性**：所有任务共享同一套 models/rules，减少 domain convention 不一致问题。
- **可验证**：reference solution 天然通过 `piki check`，不需要额外人工校验。

### 负面 / 风险

- **工具链需要开发**：`extract_tasks.py` 需要支持 Git 操作、文件过滤、YAML 生成和 piki check 调用。
- **manifest 维护成本**：每个 commit 的 requirement 和 expected_files 仍需人工编写。
- **commit 历史设计要求高**：如果 commit 切分不合理（例如一次修改太多文件），会导致任务粒度不均、难度不可控。

## 相关决策

- ADR 0001：任务生成策略。
- ADR 0002：canonical 工程领域选择。
- ADR 0004（待写）：canonical 工程的 commit 粒度与任务分类规范。

## 参考

- 现有任务 schema：`tasks/telecom/comprehensive-001/task.yaml`
- `papers/sd-hwe-bench/AGENTS.md`

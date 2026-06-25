# ADR 0004: Canonical 工程的 Commit 粒度与任务分类规范

## 状态

已提出 → **已通过**，2026-06-24。

## 背景

根据 ADR 0001–0003，SD-HWE-Bench 将通过 canonical ADL 工程的 commit 历史来生成任务。本 ADR 规定：

1. 如何切分 commit，使每个 commit 对应一个高质量任务；
2. 任务的分类体系与难度定义；
3. 什么情况下允许 scaffold commit 不是合法 piki 项目（例如 debugging 任务）。

## 决策

### 1. Commit 切分原则

每个 canonical 工程的 commit 历史应当模拟真实工程设计的演进过程。切分原则：

- **原子性**：一个 commit 只做一个明确的设计增量，不要把“添加设备 + 修改布局 + 添加连接”混在同一个 commit 里，除非是刻意设计的 comprehensive 任务。
- **合法性**：作为 reference solution 的 commit（即每个任务的 commit `k+1`）必须能通过当前插件集的 `piki check`。
- **可解释性**：commit message 和 `task_manifest.yaml` 中的 `summary` 必须清楚说明本次设计增量“做了什么”和“为什么”。
- **连贯性**：相邻 commit 之间应有自然的工程依赖关系，Agent 看到 scaffold 后能推断下一步要做什么。

允许例外：

- **Debugging 任务**的 scaffold commit 可以故意包含错误；此时 requirement 会明确要求 Agent 修复错误，solution commit 才是合法状态。

### 2. 任务分类

每个任务必须标注一个主要 `task_type`，可选 secondary tags。

| 类型                   | 定义                                                      | 典型能力考查                              |
| ---------------------- | --------------------------------------------------------- | ----------------------------------------- |
| `instance-declaration` | 声明新的 instance（设备、机柜、PDU、端口等）              | 正确填写 family/model/接口/物理尺寸       |
| `layout-design`        | 为已有 instance 分配位置（rack_id / position_u / pdu_id） | 空间规划、避免冲突、U 位合理利用          |
| `mating-design`        | 声明配合关系（rack-mount、power、fiber、sfp 等）          | 理解配合类型、parent/child 方向、约束条件 |
| `connection-design`    | 声明端口/线缆/光纤连接                                    | 端口类型匹配、线缆类型、长度、方向        |
| `comprehensive`        | 需要同时完成多个增量（如新增一个子系统）                  | 综合规划能力                              |
| `debugging`            | 给定一个已有但非法的设计，修复错误                        | 阅读诊断信息、定位错误、正确修改          |
| `optimization`         | 在合法设计基础上改进指标（功率、成本、空间）              | 权衡多目标约束                            |
| `incremental`          | 在现有设计上做小幅扩展（如新增一台设备）                  | 在不破坏现有约束的前提下集成新元素        |

### 3. 难度定义

难度根据以下维度综合判定：

| 维度               | easy                 | medium                    | hard                         |
| ------------------ | -------------------- | ------------------------- | ---------------------------- |
| 新增/修改文件数    | ≤ 5                  | 6–15                      | > 15 或跨多个目录            |
| 涉及能力维度       | 单一（如只声明实例） | 2 个维度（如布局 + 配合） | 3 个及以上维度               |
| 约束数量           | 少量显式约束         | 多个显式约束              | 多约束 + 需要权衡/优化       |
| 是否需要阅读诊断   | 否                   | 可能                      | 是（debugging/optimization） |
| 是否需要生成交付物 | 否                   | 部分                      | 是                           |

### 4. 推荐的 Commit 序列模板（以 Telecom 项目为例）

一个 20-commit 的电信机柜项目可以按以下节奏设计：

```text
C00  初始 scaffold：piki.toml + models/
C01  instance-declaration/easy：声明 RACK-A01、PDU-A、PDU-B
C02  layout-design/easy：把 PDU 分配到机柜 U 位
C03  instance-declaration/easy：添加 SRV-01
C04  layout-design/medium：为 SRV-01 分配 U 位并更新 layout
C05  instance-declaration/easy：添加 SRV-02
C06  layout-design/medium：为 SRV-02 分配 U 位，避免冲突
C07  instance-declaration/easy：添加 SW-01
C08  layout-design/medium：为 SW-01 分配 U 位
C09  mating-design/medium：为所有设备添加 rack-mount-19inch 配合
C10  instance-declaration/medium：添加端口和光模块实例
C11  connection-design/medium：添加第一条光纤连接
C12  connection-design/medium：添加第二条光纤连接
C13  mating-design/medium：添加 SFP28 cage 和 LC connector 配合
C14  mating-design/easy：添加 power-iec 配合
C15  debugging/medium：故意引入功率超载，要求 Agent 修复
C16  optimization/medium：在满足约束前提下减少 PDU 数量
C17  incremental/hard：新增第二台交换机并重新布线
C18  comprehensive/hard：新增一个机柜并把部分设备迁移过去
C19  deliverable-generation/medium：运行 piki generate 产出全部交付物
```

每个 commit 对应一个任务，因此一个 20-commit 项目可产生 19 个任务。

### 5. Debugging 任务的设计

Debugging 任务需要 scaffold 是非法状态。设计方式：

- 在合法 commit `k` 之后，额外创建一个 `k-buggy` commit（不进入主历史，只作为任务 scaffold）。
- `task_manifest.yaml` 中明确指定 `from: k-buggy`，`to: k+1`。
- requirement 中给出具体错误现象或 `piki check` 诊断摘要，要求 Agent 修复。

### 6. Comprehensive 与 Incremental 的区分

- **Incremental**：在已有完整设计上增加一个小元素，且不破坏现有约束。例如“新增一台服务器并正确接入现有 PDU/网络”。
- **Comprehensive**：需要同时处理多个相互依赖的新增/修改。例如“为新业务扩容一个机柜，包括新机柜、新设备、新连接、新 layout 和相应的 power/space 校验”。

## 结果

### 正面

- 任务粒度统一，便于控制 difficulty 分布。
- 每个任务有明确的能力考查点，便于后续错误分析和论文叙事。
- Commit 历史本身成为 benchmark 的“设计故事线”。

### 负面 / 风险

- 设计一个 20–30 commit 的高质量工程历史需要大量领域工作。
- 过于严格的 atomic commit 可能导致某些任务过于琐碎；需要 allow comprehensive commits 来保持任务趣味性。
- Debugging 任务需要额外维护 buggy scaffold commits，增加 repo 复杂度。

## 相关决策

- ADR 0001：任务生成策略。
- ADR 0002：canonical 工程领域选择。
- ADR 0003：任务提取工具与元数据 schema。

## 参考

- 现有任务示例：`tasks/telecom/*/task.yaml`
- `docs/adr/0003-task-extraction-tooling.md`

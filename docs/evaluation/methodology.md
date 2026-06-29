# SD-HWE-Bench 评估方法论

> 最后更新：2026-06-28 · 反映当前 37-task telecom 实现

---

## 1. 任务组织

```text
telecom (37 tasks)
├── 声明型 (instance/layout/connection/mating) — 11 tasks
│ ├── POC 手工任务: comprehensive-001, connection-design-001,
│ │ instance-declare-001, layout-design-001, mating-design-001
│ └── easy-compound: 001-005
├── 合并阶段 (rack/dc/site) — 16 tasks
│ ├── rack-stage1 ~ stage4 (机柜扩容)
│ ├── dc-stage1 ~ stage5 (数据中心)
│ └── site-stage1 ~ stage7 (户外基站)
├── 涌现约束 (emergent) — 4 tasks
├── 跨专业综合 (cross) — 3 tasks
└── AIDC (aidc) — 4 tasks
 ├── operation-001/002 (运营优化)
 └── co-design-001/002 (设计-调度联合优化)
```

每个 task 是一个自包含目录：

```text
tasks/telecom/<task-name>/
├── task.yaml # 元数据 + scoring_layers + l7_config
├── scaffold/ # Agent 可见的初始项目
├── solution/ # 参考方案（Agent 不可见）
└── expected/ # 期望交付物（可选）
```

---

## 2. 评分体系

详细的评分层定义、权重、Pass/Fail 判定请见 **[scoring.md](scoring.md)**。

快速概览：

| 维度 | 说明 |
|------|------|
| **L0** | Syntax：YAML 合法、预期文件/交付物存在 |
| **L1** | Schema：字段类型、值域、必填字段 |
| **L2** | Reference Integrity：ID、外键、端口、接口、配合、目录引用 |
| **L3** | Static Engineering Constraints：功率预算、U 位、静态工程约束 |
| **L4** | Reduced-Order Dynamic Model：AIDC 降阶动态仿真硬约束 |
| **L5** | Geometry Interference & Error Analysis：几何碰撞、rack 空间 |
| **L6** | FEM/CFD 高保真仿真（预留） |
| **Deliverable** | `piki generate` 产出期望交付物（关键 but 非层） |
| **Performance Score** | 相对 baseline/reference 的优化诊断分数（非层） |
| **Rubric** | LLM-as-judge 语义评估（可选，非层） |

**Pass 条件**：所有 Critical Layer (L0-L5，AIDC 含 L4) 通过 + 交付物齐全。

---

## 3. 任务类型与能力映射

| 类型 | 考察能力 | 难度 | 评分重点 |
|------|---------|------|---------|
| instance-declaration | 型号选择、参数赋值 | easy-medium | L1-L2 |
| layout-design | 离散空间分配、约束满足 | easy | L1-L3 |
| connection-design | 接口匹配、拓扑推理 | medium | L1-L3 |
| mating-design | 机械配合、耦合选择 | medium | L1-L3 |
| comprehensive | 全链路协调、多约束 | medium-hard | L1-L3 + L5 + deliverable |
| co-design | 设计-调度联合优化 | hard | L1-L4 + 性能诊断 |

---

## 4. 实验协议

### 4.1 运行模式

```bash
sd-hwe-bench run <task-id> --actor <spec> --passes 5 --jobs 1
```

- **pass@5**：每个任务独立运行 5 次，每次 Agent 从 scaffold 开始
- **--sandbox none**：Agent 直接写本地文件系统
- **score 阶段**：`sd-hwe-bench score <task-id> <output> --sandbox docker`（piki check 在容器中运行）

### 4.2 模型

| Actor | 模型 | 说明 |
|-------|------|------|
| kimi | kimi (kimi-code) | Kimi 代码助手 |
| codex:deepseek-v4-pro | DeepSeek-v4-Pro | 通过 Codex CLI |
| codex:deepseek-v4-flash | DeepSeek Flash | 通过 Codex CLI |

### 4.3 基线

当前实验基线：

- **Flash pass@1** (28-task): 82.1% — 早期单次实验
- **Kimi pass@5** (30-task): 84.7% — 本会话
- **DSv4-Pro pass@5** (30-task): 86.7% — 本会话
- **Flash pass@5** (25-task): 96.0% — 本会话（6 个 hard 任务未完成）

### 4.4 人类基线

**待收集**。计划招募 3-5 名熟悉 ADL/piki 的工程师，每人完成 10-15 个代表性任务。

---

## 5. Canonical Projects

5 个 canonical project 作为任务提取的源工程：

| Project | 路径 | 用途 |
|---------|------|------|
| telecom-rack | canonical/telecom-rack/ | 42U 机柜扩容 |
| datacenter | canonical/datacenter/ | 数据中心 ToR 组网 |
| datacenter-hall | canonical/datacenter-hall/ | AIDC 14.8kW 运营 |
| aidc-60mw | canonical/aidc-60mw/ | 60MW AIDC 全生命周期 git-lineage（concept/detailed/epc，3 tasks） |
| telecom-site | canonical/telecom-site/ | 户外基站 |

---

## 6. 已知局限

1. **pass@1 偏高**：30 tasks 中 Kimi 84.7%、DS-Pro 86.7%，仅有 7 个区分度任务
2. **Flash 未完成**：6 个 hard 任务（cross-*, aidc-*）上 codex flash 频繁 hang，数据缺
3. **人类基线缺失**：无法回答"人类工程师表现如何"
4. **模型覆盖少**：仅 3 个模型，无 GPT-4o/Claude/
5. **AIDC 仿真为集总参数模型**：未引入 CFD/二维热模型
6. **LCC 收益模型简化**：统一 IT 租金/显卡折旧

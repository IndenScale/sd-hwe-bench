# 4. 数据集

本章详细描述 SD-HWE-Bench 的数据集构建过程。第 4.1 节给出整体 pipeline 的漏斗数字；第 4.2 节介绍 canonical 工程；第 4.3 节描述任务提取流程与质量控制；第 4.4 节给出数据集的统计特征。

## 4.1 构建 Pipeline 概览

SD-HWE-Bench 的数据集构建遵循四阶段 pipeline（图 2）：

```text
Canonical 工程 Authoring        Commit 序列化
   2-3 个完整 ADL 工程    →    人工迭代，每个 commit 是有意义增量
                ↓
        任务提取 (extract_tasks.py)
   相邻 commit → 自动生成任务（需求描述/上下文/gold patch/测试）
                ↓
        执行验证 + 人工审核
   gold patch 必须通过 piki check
   人工审核问题描述正确性和任务合理性
                ↓
        最终任务集
   N 个任务 × M 个领域
```

**Figure 2**：SD-HWE-Bench 数据集构建 pipeline。{#fig:pipeline}

最终数据集规模预期：

| 阶段 | 数量 |
|------|------|
| Canonical 工程 | 2–3 个 |
| 总 commit 数 | 40–80 个 |
| 候选任务（相邻 commit 对） | 35–70 个 |
| 人工审核后保留 | 30–60 个 |

> 注：具体数字将在 canonical 工程完成后更新。当前 POC 阶段有 5 个 telecom 任务用于流程验证。

## 4.2 Canonical 工程

SD-HWE-Bench 基于两个 canonical ADL 工程构建任务，覆盖不同的硬件工程子领域和设计复杂度。

### 4.2.1 电信机柜扩容工程（Telecom Rack Expansion）

**领域**：电信基础设施
**ADL 规模**：预计约 800–1200 行 PDL + 1500–2500 行 PML + 600–1000 行 PLL
**Part 类型**：15–25 种（交换机、服务器、PDU、PatchPanel、UPS、光纤盒、理线器等）
**设计约束**：功率预算、U 位分配、散热间隙、接口兼容性、承重限制、线缆路由

该工程模拟一个 42U 标准电信机柜从空白到满载的完整部署过程。初始 commit 仅包含机柜框架和基础 PDL 定义。后续 commits 逐步增加：电源分配单元配置、第一组交换机和服务器部署、PatchPanel 和布线规划、冗余电源/UPS 添加、最终的热管理和承重验证。

### 4.2.2 数据中心一排机架工程（Datacenter Row Deployment）

**领域**：数据中心基础设施
**ADL 规模**：预计约 600–1000 行 PDL + 2000–3000 行 PML + 800–1500 行 PLL
**Part 类型**：8–15 种（机架、CRAC 空调、配电柜、母线槽、架空地板、传感器等）
**设计约束**：冷热通道布局、气流管理、功率密度限制、冗余配置（N+1/2N）、地板承载

该工程模拟数据中心中一排（5–10 个）机架的部署。任务覆盖机架间距规划、功率分配、冷却容量计算、冗余路径设计等典型数据中心工程设计问题。

### 4.2.3 任务与 Commit 的对齐

每个 canonical 工程的设计原则：

1. **每个 commit 是一个有意义的设计增量**：不是一个文件的一行修改，而是一个完整的设计决策（如"增加一个交换机并更新功率预算"）。
2. **每个 commit 通过 piki check**：确保任何时候 checkout 到的状态都是合法的 ADL 工程。
3. **Commit message 可作为任务描述的基础**：清晰的 commit message 在人工审核后转化为任务需求自然语言。

## 4.3 任务提取流程

`tools/extract_tasks.py` 是自动任务提取工具。其核心算法：

1. 遍历 canonical 工程的 git log，识别相邻 commit 对 `(commit_k, commit_{k+1})`。
2. 对于每对 commit：
   - **生成需求描述**：读取 commit message + `git diff` 的变更摘要，结合领域模板生成自然语言任务需求。
   - **生成 scaffold**：checkout `commit_k` 的完整工程状态，作为任务上下文。
   - **提取 gold patch**：计算 `git diff commit_k commit_{k+1}` 中影响 ADL 文件（`.yaml` 在 `models/` 下）的变更。
   - **提取 DTS 测试**：在 `commit_{k+1}` 状态运行 `piki check`，记录所有通过的 DTS 层和规则。
   - **判断任务类型**：根据变更涉及的 ADL 层（PDL/PML/PLL）和变更性质（新建/修改/删除），自动分类为 `instance-declaration` / `layout-design` / `connection-design` / `mating-design` / `comprehensive`。

3. 输出每个候选任务的 `task.yaml` 骨架和 `scaffold/`、`solution/` 目录。

### 4.3.1 质量控制

所有自动提取的任务随后进入人工审核：

- **需求准确性**：检查自动生成的任务需求是否准确反映 commit 的变更意图。
- **Scaffold 完整性**：确认 scaffold/ 包含任务所需的全部上下文文件。
- **Solution 正确性**：验证 solution/ 中的 gold patch 确实满足任务需求，且 `piki check` 全通过。
- **难度标注**：根据修改范围、跨域耦合和 DTS 覆盖层数手动标注 difficulty。
- **Rubrics 补充**：为需要定性评估的任务（如 comprehensive 类型）补充 rubrics。

不符合标准的任务被直接剔除，不进入最终数据集。POC 阶段的初步经验表明，自动提取的候选任务中约 70-80% 可通过人工审核。

## 4.4 数据集统计特征

@tbl:dataset-stats 给出了数据集的预期统计特征（具体数字待 canonical 工程完成后更新）。

| 统计维度 | 值 |
|---------|-----|
| 总任务数 | N |
| 领域数 | 2–3 |
| 任务类型分布 | instance-declaration: xx%, layout-design: xx%, connection-design: xx%, mating-design: xx%, comprehensive: xx% |
| 难度分布 | easy: xx%, medium: xx%, hard: xx% |
| 平均 scaffold ADL 行数 | ~xxx 行 |
| 平均 gold patch 行数 | ~xx 行 |
| 平均 gold patch 涉及文件数 | ~x 个 |
| 平均 DTS 覆盖层数 | L0–L3（大部分），L4 部分 |
| 任务需求平均长度 | ~xxx 词 |

Table: SD-HWE-Bench 数据集统计。{#tbl:dataset-stats}

### 4.4.1 任务特性总结

SD-HWE-Bench 的任务具有以下核心特性：

1. **真实硬件工程设计任务**：任务来自 canonical ADL 工程的真实 commit 历史，每个 commit 对应一个有意义的完整设计增量，而非人工合成的 toy problem。
2. **多物理域耦合**：单个任务可同时涉及电气连接（电源线/信号线）、物理配合（螺栓/卡扣）、空间布局（U 位/间距/散热）、热管理和结构约束。
3. **长上下文**：scaffold 通常包含 800–3000+ 行 ADL 声明、数十个 Part 实例、多层装配关系——要求 Agent 具备长上下文理解和全局一致性保持能力。
4. **可执行数字模型**：每个任务绑定 DTS 分层断言，可在毫秒至秒级给出确定性正确/错误信号。
5. **跨抽象层编辑**：修改可能发生在 Part 类型定义（PDL）、实例声明、连接关系（PML）、布局位置（PLL）任意一层——要求 Agent 理解三层正交的语言语义。
6. **可持续更新**：canonical 工程的任何新增 commit 都可自动提取为新任务，无需重新构建数据集。

## 4.5 数据集划分

数据集按 canonical 工程来源划分训练/验证/测试集：

- **训练集**：部分 canonical 工程的连续 commit 段，用于模型微调和 prompt 调优。
- **验证集**：保留的 commit 段，用于方法开发和超参数选择。
- **测试集**：完整保留的 canonical 工程（全部 commit），用于最终评测和 leaderboard。

测试集 canonical 工程的选择原则：不与训练/验证集共享任何 Part 类型定义或工程场景，以确保评测的独立性和泛化性。

## 4.6 与 Related Benchmarks 的数据集对比

@tbl:dataset-comparison 将 SD-HWE-Bench 的数据集与代表性 benchmark 对比。

| 维度 | SWE-bench | SWE-bench M | HumanEval | SD-HWE-Bench |
|------|-----------|-------------|-----------|-------------|
| 任务来源 | 开源 GitHub repo | 开源 GitHub repo | 手写 | Canonical ADL 工程 |
| 领域 | Python 代码 | JS/TS + 视觉 | 算法/逻辑 | 物理工程设计 |
| 上下文规模 | 数百-数万行 | 数百-数万行 | 数行函数签名 | 800-3000+ 行 ADL |
| 反馈类型 | pytest 通过/失败 | pytest + 视觉 | 输入/输出对 | DTS L0-L5 分层 |
| 多域耦合 | 无 | 有限 | 无 | 电气/热/结构/信号 |
| 几何约束 | 无 | 有限 | 无 | 碰撞/U位/间距 |
| 新任务扩展 | 依赖新 issue | 依赖新 issue | 手写新题 | 自动从 commit 提取 |

Table: 数据集构建范式对比。{#tbl:dataset-comparison}

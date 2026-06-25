# ADR 0002: Canonical 工程领域选择

## 状态

已提出 → **已通过**，2026-06-24。

## 背景

根据 ADR 0001，SD-HWE-Bench 将采用“构建 canonical ADL 工程并从顺序 commit 中提取任务”的策略。下一步需要确定：

1. 选择哪些工程领域作为 canonical 项目。
2. 每个领域需要覆盖哪些设计能力维度。
3. 如何平衡领域多样性、插件成熟度和 authoring 工作量。

## 候选方案

### 方案 A：单领域深度（只做 Telecom）

- 只构建一个大型 telecom 项目，从中提取 30+ 任务。
- 优点：领域统一、插件成熟、authoring 成本低。
- 缺点：缺乏跨领域泛化证据，Dataset Track 审稿人可能质疑 benchmark 的广度。

### 方案 B：多领域浅尝（Telecom + Datacenter + Mechanical，各做少量）

- 三个领域各构建一个小型项目，每个提取 5–10 个任务。
- 优点：多样性足够。
- 缺点：每个项目都不够“完整”，难以支撑从概念到施工的叙事。

### 方案 C：多领域深度（Telecom + Datacenter + Mechanical Keyboard，各做完整项目）

- 三个领域各构建一个完整、可加工/可施工的 canonical 工程，每个提取 15–20 个任务。
- 优点：兼顾深度与广度，最能支撑 Dataset Track 的规模和叙事。
- 缺点： authoring 工作量大， mechanical 领域插件成熟度待验证。

## 决策

采用 **方案 C**，但按以下优先级推进：

1. **电信机柜扩容（Telecom Rack Expansion）**
   - 插件：`piki.extensions.telecom`
   - 覆盖能力：实例声明、layout、rack-mount mating、电源配合、光纤连接、功率预算、碰撞检查、交付物生成。
   - 状态：已有 5 个参考任务作为基础，最快完成。

2. **数据中心一排机架（Datacenter Row）**
   - 插件：`piki.extensions.datacenter` + `piki.extensions.telecom`
   - 覆盖能力：多机柜布局、冷热通道、PDU 冗余、跨机柜线缆、承重与散热、抬高地板网格对齐。
   - 状态：telecom 的自然扩展，需要补充 datacenter 特定规则。

3. **机械键盘外壳装配（Mechanical Keyboard Chassis Assembly）**
   - 插件：`piki.extensions.keyboard` 或 `piki.extensions.assembly`
   - 覆盖能力：3D 配合、螺孔对齐、板壳间隙、材料/BOM、可制造性检查。
   - 状态：领域差异最大，能最好地验证 ADL 的跨领域通用性；但插件成熟度需先验证。

**备用方案**：如果 mechanical 领域插件在 2 个月内无法达到完整检查能力，则替换为 `piki.extensions.assembly` 下的一个 simpler mechanical assembly（如小型钣金支架），或只保留 Telecom + Datacenter 两个深度项目。

## 结果

### 正面

- **领域多样性**：覆盖电信、数据中心、机械装配，能证明 ADL/ESA 的跨领域通用性。
- **难度梯度自然**：每个项目内部由浅入深；跨项目又能测试不同类别约束（电缆 vs. 气流 vs. 3D 配合）。
- **插件利用率高**：全部基于 piki 已有插件，不需要从零写新 domain checker。
- **叙事完整**：每个项目都能讲出“从概念设计到可加工/施工”的故事。

### 负面 / 风险

- **工作量显著**：3 个完整项目大约需要 1.5–2 个月全职 authoring。
- **datacenter 规则待补**：当前 datacenter 插件可能比 telecom 插件粗糙，需要补充或调整规则。
- **mechanical 插件成熟度不确定**：需要先用一个简单装配验证 `piki check` 是否能覆盖几何/制造约束。

## 相关决策

- ADR 0001：任务生成策略。
- ADR 0003（待写）：任务提取工具与元数据 schema。
- ADR 0004（待写）：每个 canonical 工程的 commit 粒度与任务分类。

## 参考

- `/Users/indenscale/workspace/piki/src/piki/extensions/` 下的可用插件。
- `papers/sd-hwe-bench/AGENTS.md`
- `docs/adr/0001-task-generation-strategy.md`

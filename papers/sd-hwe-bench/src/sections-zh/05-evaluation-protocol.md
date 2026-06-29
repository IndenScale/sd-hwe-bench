# 5. 评测协议

本章详细定义 SD-HWE-Bench 的评测协议，包括 DTS 分层评分体系、评分聚合与 pass@k 计算、评测上下文设置、以及 repair loop 协议。

## 5.1 DTS 分层评分体系

SD-HWE-Bench 的核心评分引擎是 **DTS（Design Test Suite）**。DTS 将设计正确性分解为六个层次，从文本格式到物理行为逐层递进。每层可独立评分，Agent 在任意一层失败即该任务判定为失败。

DTS 的分层遵循"先文本、后符号、再物理"的递进逻辑：L0–L2 检查设计声明的形式正确性（文本和符号图），L3–L5 检查物理装配体的正确性（静态断言、动态激励、几何干涉），L6 预留为高精度物理仿真层（本次未启用）。

### 5.1.1 L0：语法层（Syntax）

**检查内容**：YAML 文件合法性、项目非空、所有 `expected_files` 与 `expected_deliverables` 存在。

- ADL 使用 YAML 作为序列化格式。L0 使用标准 YAML 解析器验证所有输出文件是否符合 YAML 语法。
- 验证 `task.yaml` 中声明的 `expected_files` 是否全部存在且非空。
- 验证 `expected_deliverables` 中声明的交付物是否被生成（或在交付物检查阶段确认）。
- 当 Agent 输出包含 YAML 语法错误、缺少必需文件或交付物时，任务直接失败——后续层不再执行。

**检查延迟**：< 10ms

### 5.1.2 L1：语义层（Schema & Type System）

**检查内容**：ADL Schema 校验、类型系统一致性、属性合法范围。

- 验证每个 Part 声明包含必需的 `id`、`model`、`type` 字段。
- 验证 Part 的 `power`、`heat`、`weight` 等属性值在物理合理范围内（非负、非溢出）。
- 验证端口声明（`ports`）的 `connector_type`、`protocol`、`direction` 字段合法。
- 验证枚举类型的值在允许集合内（如 `connector_type` 仅允许 `C13/C14/C19/C20/LC/SC/RJ45/...`）。
- 验证 PML 连接声明和 PLL 布局声明的 schema 完整性。

**检查延迟**：< 50ms

### 5.1.3 L2：引用完整性（Reference Integrity）

**检查内容**：Part 引用可解析、端口可匹配、配合/目录引用有效、层级无循环。

- 验证 PDL/PML/PLL 中引用的每个 `part_id` 在 PDL 中有对应定义。
- 验证 PML 中声明的 `source_port` 和 `target_port` 均在对应 Part 的端口列表中存在。
- 验证 PLL 中声明的 `parent_rack`/`parent_assembly` 引用存在且类型兼容。
- 验证装配层级无循环引用（Part A 包含 Part B，而 Part B 又包含 Part A）。
- 验证配合/目录引用（mate type、catalog item）有效且存在。

**设计原则**：L2 不再拆分为子层。所有引用完整性错误统一计为 L2 失败，避免过度细分导致权重碎片化。

**检查延迟**：< 100ms

### 5.1.4 L3：装配体静态分析 / ASA（Assembly Static Analysis）

**分析对象**：物理装配体

**分析模式**：不施加激励，纯静态声明断言。基于声明即可判断对错，无需模拟系统行为。

**检查内容**：

- **功率预算检查**：机柜/排的总功耗是否超过 PDU/UPS 容量。
- **U 位冲突检查**：两个 Part 是否占用了重叠的 U 位范围。
- **端口兼容性检查**：连接的 source 和 target 端口类型是否兼容（如 `C13` 插头只能接 `C14` 插座；`LC` 光纤口不能连 `RJ45` 电口）。
- **接口方向检查**：电源线/信号线的方向是否合理（输入→输出/上行→下行）。
- **散热空间声明检查**：发热设备之间是否满足最小散热间距（仅声明间距，不模拟热传导过程）。
- **装配兼容性检查**：Part 之间的物理配合类型（螺栓/卡扣/导轨）是否与 Part 声明兼容。
- **线缆路由声明检查**：线缆长度是否超限、是否穿过禁止区域。
- **数值断言（Numeric Asserts）**：任务可在 `task.yaml` 中声明数值约束（如 `floor_load <= 12 kN/m²`），由 NumericCritic 校验。

**设计原则**：ASA 下的所有检查都是"看声明就能判断"的——它们不涉及状态变化、激励施加或模型求解。一条功率超额就是超额，不因为"运行时可能降频"而改变结论。

**检查延迟**：< 500ms

### 5.1.5 L4：装配体动态分析 / ADA（Assembly Dynamic Analysis）

**分析对象**：物理装配体

**分析模式**：施加虚拟激励 → 观察系统响应 → 阈值判断。在 DTS 框架中，ADA test case 的形式与软件单元测试完全一致：

```python
def test_fire_resistance(assembly):
    apply_heat_load(assembly, duration="2h", temp=800)
    assert assembly.part["wall"].max_temp < assembly.part["wall"].ignition_temp
```

即 **setup → exercise → assert** 的标准测试三元组，只是激励和响应位于物理域。

**检查内容**：

- **AIDC 设计任务仿真合规**：对 AIDC 主机房模型进行全年 8760 小时（或 48h 简化）步进仿真，验证：
  - 进风温度不超过安全阈值；
  - PUE、电费、碳排、水耗满足任务声明的硬约束；
  - 对于 `co-design` 任务，TCO/NPV/LCOE 满足约束。
- **EPC 施工排程仿真**：对 CPML 活动网络进行离散事件调度，验证：
  - 项目完工日期不超过 `deadline_days`；
  - 任意时刻人工/机械/材料资源使用不超过可用量；
  - 应急预案决策合法（如雨天不进行室外吊装、加班需额外成本）。
- **防火检查**：施加热荷载（时间、温度曲线），验证被保护结构的温升是否低于燃点。防火等级（如 EI60/EI120）是打包了多个 ADA test case 的语法糖。
- **承重/结构检查**：施加重力荷载和地震荷载，验证应力分布是否低于材料屈服强度。
- **散热检查**：施加热功率荷载，验证散热路径是否满足设计要求（区别于 ASA 的间距声明——ADA 实际模拟热传导/对流）。
- **软碰撞检查**：施加人员动线荷载或设备维护动线，验证是否存在空间临时侵入（区别于硬碰撞的永久包围盒重叠）。
- **硬碰撞/几何干涉**：施加碰撞体，检测 Part 包围盒在水密/干密条件下是否存在干涉（传统任务中由 L5 几何规则覆盖；AIDC 任务中不启用）。
- **电缆电压降验证**：施加额定电流荷载，计算给定长度和线规的电压降是否在允许范围内。

**设计原则**：ADA 不要求高精度 CFD/FEA 仿真。当前 DTS 使用解析公式和轻量代理模型（包围盒碰撞、集总参数热模型、简支梁公式、CPML 离散事件调度等）。这足以筛除明显违规，并为未来接入高精度仿真后端（参见 §9.2）提供接口预留。

**检查延迟**：1–5 秒（AIDC 全年仿真约 1–3 秒，CPML 排程约 0.5–2 秒）

### 5.1.6 L5：几何干涉、误差分析与施工可建性

**检查内容**：几何碰撞、rack 空间冲突、装配误差、施工可建性等。

- **3D 包围盒碰撞**：Part 在三维空间中的占用体是否存在重叠。
- **U 位/Rack 空间**：机柜内 Part 的 U 位范围是否冲突、是否超出机柜高度。
- **装配误差**：机械配合的公差/间隙是否满足设计要求。
- **施工可建性**（detailed-design / epc 任务）：
  - 重型设备（冷水机组、变压器等）是否配置吊装方案：起重机吨位 ≥ 1.25× 设备重量、作业半径、净空高度、吊点位置；
  - 主吊车在设备到场至就位期间持续在场；
  - 至少两个 VDC 工作面，含编号、区域、里程碑、前置条件。

这些规则由 piki 几何规则引擎与 `ConstructabilityCritic` 共同执行，映射为 L5 失败。

### 5.1.7 L6：高精度物理仿真（预留）

**L6 预留**用于接入 FEM/CFD 等高保真物理仿真后端，例如：

- 机柜级气流组织 CFD 仿真；
- 结构件应力/模态有限元分析；
- 整站电磁兼容仿真。

本次评测未启用 L6，但 DTS 架构已为该层预留接口。

### 5.1.8 Performance Score：诊断性性能评分

针对 AIDC 设计任务与 EPC 任务，DTS 在通过 L0–L4 后计算 **Performance Score**，作为诊断指标：

- **AIDC 设计任务**：
  - 物理性能指标：全年 PUE、总电费（CNY）、总碳排放（kg CO₂）、总水耗（m³）。
  - 经济指标：15 年 TCO、NPV、LCOE（由 `lifecycle.py` 计算）。
- **EPC 任务**：
  - 工期指标：P90 完工天数。
  - 成本指标：P90 总成本（含正常施工、加班、应急预案成本）。

**评分方式**：采用相对归一化以避免天花板效应：

$$\text{score}_i = \max\left(0, \min\left(1, \frac{v_i^{\text{baseline}} - v_i^{\text{agent}}}{v_i^{\text{baseline}} - v_i^{\text{reference}}}\right)\right)$$

其中 `baseline` 为 scaffold 内置的默认策略，`reference` 为人工编写的强参考策略。该公式确保最优参考方案得 1 分，基线策略得 0 分，Agent 的方案根据实际改善幅度得分。

对于 `co-design` 任务，Performance Score 同时包含约束满足度（如 PUE ≤ 阈值）和经济指标（TCO、NPV、LCOE），最终为加权和：

$$\text{Performance Score} = \lambda_{\text{performance}} \cdot \text{score}_{\text{performance}} + \lambda_{\text{lcc}} \cdot \text{score}_{\text{lcc}}$$

对于 `epc` 任务，Performance Score 为 P90 工期与 P90 成本的加权和：

$$\text{Performance Score} = \lambda_{\text{duration}} \cdot \text{score}_{\text{duration}} + \lambda_{\text{cost}} \cdot \text{score}_{\text{cost}}$$

**Performance Score 不计入 overall_score，仅用于 leaderboard 诊断和任务区分度分析。**

### 5.1.9 交付物检查（Deliverable Check）

**检查内容**：`piki generate` 能否成功产出期望的交付物。

- **生成成功**：`piki generate` 命令成功完成，无运行时错误。
- **期望交付物**：`task.yaml` 中 `expected_deliverables` 指定的交付物类型（BOM 表、3D 预览、布线图等）是否全部生成。

交付物缺失被视为 L0 失败的一种（生成产物不存在）。在通过 L0 后，DeliverableCritic 仍独立执行，用于诊断设计声明是否可被实例化为可制造/可视化的产物；**它不单独占用评分层**，也不计入 overall_score 的层权重。

### 5.1.10 DTS 层间关系

@tbl:dts-layers 总结了 DTS 各层的分析对象、模式、范围和延迟。

| 层 | 名称 | 分析对象 | 模式 | 关键检查 | 延迟 |
|----|------|---------|------|---------|------|
| L0 | 语法层 | YAML 文本 | 解析 | YAML 合法性、文件与交付物存在性 | <10ms |
| L1 | 语义层 | 字段值 | 断言 | Schema 校验、类型系统 | <50ms |
| L2 | 引用完整性 | 符号图 | 解析 | Part/端口引用可解析、无循环依赖 | <100ms |
| L3 | ASA 装配体静态分析 | 物理装配体 | 静态断言 | 功率预算、U位、端口兼容、散热间距 | <500ms |
| L4 | ADA 装配体动态分析 | 物理装配体 | 激励→响应→阈值 | AIDC 仿真合规 / CPML 施工排程 / 防火、承重、电压降 | 1-5s |
| L5 | 几何干涉、误差分析与可建性 | 物理装配体 | 几何断言 + 施工检查 | 3D 碰撞、rack 空间、吊装/VDC | 1-5s |
| L6 | 高精度物理仿真 | 物理场模型 | FEM/CFD（预留） | 气流、应力、电磁兼容 | — |
| — | Performance Score | 策略与设计/施工方案 | 相对归一化 | PUE、TCO、NPV、LCOE / P90 工期、P90 成本 | <100ms |
| — | Deliverable Check | 生成物文件 | 存在性断言 | piki generate 成功、期望文件齐全 | 数秒 |

Table: DTS 分层检查体系。{#tbl:dts-layers}

DTS 的关键设计特点：**低层通过后才执行高层**——如果 L0 失败，L1–L5 不再检测。这种"快速失败"设计在批量评测场景中显著降低时间成本。L3（ASA）和 L4（ADA）的区别在于：ASA 只看声明即可断言对错；ADA 需要施加激励并观察系统响应——但二者都是物理装配体层面的检查，区别于 L2 的符号图层面的引用完整性。

AIDC 任务同样遵循上述判定：设计类任务（operation / co-design）需 L0–L4 通过，详细设计任务（detailed-design）需 L0–L5 通过，EPC 任务需 L0–L4 通过；Performance Score 仅作为附加诊断指标。

## 5.2 Rubric 评估（LLM-as-Judge）

对于需要定性判断的任务维度（如 `comprehensive` 类型的设计合理性、BOM 完整性、布线美学），SD-HWE-Bench 支持可选的 **LLM-as-Judge rubrics** 评估。

- 每个任务的 `task.yaml` 中可定义 `rubrics` 列表，每项包含维度名称、评判标准和 1-5 打分描述。
- RubricCritic 调用独立的 LLM（默认 `deepseek-chat`）对 Agent 输出的 ADL 文件和交付物打分。
- **Rubrics 分数不计入 overall_score**——它仅作为诊断性参考，不用于 pass/fail 判定。
- 理由：LLM-as-Judge 的评分不确定性较高，不宜混入确定性评价体系。

## 5.3 评分聚合与 Pass@k

### 5.3.1 Overall Score

一个任务的 overall_score 由通过的确定性评分层按权重聚合：

$$\text{overall\_score} = \sum_{l \in \text{scoring\_layers}} w_l \cdot \mathbb{1}_{\{l\ \text{passed}\}}$$

其中 `scoring_layers` 来自 `task.yaml` 的覆盖配置（默认 `[L0, L1, L2, L3]`），权重来自 `settings.LAYER_WEIGHTS`：

| 层 | L0 | L1 | L2 | L3 | L4 | L5 | L6 |
|----|----|----|----|----|----|----|----|
| 权重 | 0.00 | 0.10 | 0.15 | 0.40 | 0.15 | 0.20 | 0.00 |

任务是否 resolved 的判定规则：

- **所有关键层（L0–L5）全部通过**且 **DeliverableCritic 通过**，视为 resolved；
- 任一层失败或交付物生成失败，即为 unresolved；
- Performance Score 和 Rubric 不影响 resolved 判定。

AIDC 任务同样遵循上述判定：L4 仿真合规失败即 unresolved；Performance Score 仅作为附加诊断指标。

### 5.3.2 Pass@k

Pass@k 是 SD-HWE-Bench 的主指标：对于每个任务，Actor 独立执行 k 次，只要至少 1 次 resolved 即认为该任务通过。Pass@k 按标准无偏估计计算 [@chen2021evaluating]：

$$\\text{pass@k} = \\mathbb{E}_{\\text{Tasks}}\\left[\\min\\left(1, \\frac{c}{n} \\cdot \\frac{n - c}{k - c}\\right)\\right]$$

其中 n 为每任务采样次数，c 为通过次数，k 为评估参数。

SD-HWE-Bench 默认报告 **pass@1** 和 **pass@5**。

## 5.4 评测上下文设置

借鉴 SWE-bench 的上下文实验设计，SD-HWE-Bench 定义三种上下文设置：

### 5.4.1 Full Context（完整上下文）

Agent 获得完整的 scaffold ADL 工程——即所有 PDL/PML/PLL 文件和 `piki.toml`。这模拟真实工程设计场景：设计者需要理解整个工程的当前状态才能做出修改。

**挑战**：对于大型 canonical 工程，完整上下文可能超过主流 LLM 的有效上下文窗口（通常 128K–200K tokens），或导致"上下文淹没"——模型在大量无关信息中丢失关键细节。

### 5.4.2 Oracle Context（Oracle 模块上下文）

Agent 仅获得 gold patch 涉及修改的 ADL 文件，以及这些文件直接引用的 Part 定义。这代表"能力上限"：如果 Agent 知道该修改什么，它的设计能力有多强？

**用途**：区分"找不到正确修改位置"和"不会做正确的修改"两种失败模式。

### 5.4.3 Collapsed Context（坍缩上下文）

Agent 仅获得 gold patch 被修改行 ±N 行的上下文。这测试 Agent 在极度有限信息下的推理能力。

**用途**：作为下界参考，评估"仅靠少量局部信息能否完成设计"。

@tbl:context-settings 对比三种设置。

| 设置 | Agent 获得的信息 | 测试目标 |
|------|-----------------|---------|
| Full Context | 完整 scaffold ADL 工程 | 端到端真实能力 |
| Oracle Context | 仅被修改模块 + 直接依赖 | 能力上限（定位瓶颈排除） |
| Collapsed Context | 被修改行 ±N 行 | 下界 / 局部推理能力 |

Table: 三种评测上下文设置。{#tbl:context-settings}

## 5.5 Repair Loop 协议

SD-HWE-Bench 支持 repair loop：Agent 根据 DTS 反馈迭代修复设计。

**协议**：Agent 在首次生成失败后，获得上一轮的完整 DTS 错误报告（含具体层、规则 ID、失败位置、错误描述），被要求修复失败项后重新提交。循环最多执行 R 轮（默认 R=5），或直到 DTS 全部通过。

**评分**：Repair 后的通过率记为 `pass@k (repair)`，与 no-repair 的 `pass@k` 对比，量化确定性反馈的因果价值。消融实验的详细设计和结果见 §7。

## 5.6 辅助指标

除 pass@k 外，SD-HWE-Bench 报告以下辅助指标：

- **%Apply**：Agent 生成的 patch 中实际上被应用（即修改了目标文件）的比例——过滤格式错误、输出不完整等无关失败。
- **DTS 层 Pass Rate**：各 DTS 层的独立通过率，用于定位瓶颈。
- **Avg. Cost**：每次 rollout 的平均 API 成本（token 消耗 × 单价）。
- **Avg. Time**：每次 rollout 的平均墙钟时间（含 Agent 推理 + DTS 检查）。
- **Repair Round Count**：repair 模式下达到 resolved 的平均轮数。
- **File F1**：Agent 修改的文件集合与 gold patch 文件集合的 F1 分数——定位能力指标。
- **Performance Score**：AIDC 任务的 PUE/TCO/NPV/LCOE 相对改善分数。
- **AIDC 物理-经济指标**：PUE、TCO（CNY）、NPV（CNY）、LCOE（CNY/kWh）、总电费、总碳排放、总水耗。
- **LCC 分解**：CAPEX/OPEX 比例、主要成本来源（IT 设备、冷却、电力、储能、光伏）、回本周期。

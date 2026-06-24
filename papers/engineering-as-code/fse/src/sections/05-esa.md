# 5. ESA：工程静态分析

Engineering Static Analysis（ESA）消费 ADL 声明并在设计提交前检查确定性规则，将合规审查从下游前移到上游门禁。

## 5.1 从 ACC 到 ESA

传统 ACC 运行在 CAD/BIM/IFC 模型上 [@eastman2009acc; @zhang2019acc]，存在三个问题：设计逻辑冻结为几何（信息损失）；违规发现时模型已高度耦合（修复成本高）；Agent 生成期间无法获得奖励信号（RLVR 不可行）。模型 ACC 还因缺少预期关系表示而产生几何碰撞假阳性，并依赖命名约定导致每项目翻模 [@xiao2025bimgraph]。

ESA 检查 ADL **声明**而非几何，直接获取 Part 身份、Family 类型和显式 Mate 关系，进行分层 L0–L4 检查。它类似于编译器类型检查器消费源代码，而非事后从二进制推断类型。

### 5.1.1 示例：机柜功率预算

**ACC 方法**：解析 BIM 模型、识别机柜与服务器、通过几何或命名约定判断归属、提取额定值并比较——每步都依赖模型质量和命名规范。

**ESA 方法**：规则遍历 `PDUFamily` 实例及其 `outputs`，累加所连负载的 `rated_power_w` 并与额定值比较。12 行 Python，独立于命名约定，对使用相同 Family 的任何项目有效，诊断精确指向超限输出和负载。

这不是速度对比，而是规则能否在不依赖每项目定制的条件下被编写的对比。

## 5.2 静态分析特征

ESA 共享软件静态分析的三个特征：**不执行物理仿真**（推理声明与约束）；**结果确定性**（相同 ADL 始终产生相同裁决）；**成本低廉**（毫秒到百毫秒，适合 pre-commit/CI）。它不能取代 CAE/CFD 或人工审查，但将低级确定性错误拦截在前端。

## 5.3 规则目录

piki 实现 64 条规则（62 条插件，2 条内置）。

| 插件 | 规则数 | 主要领域 |
|------|-------|---------|
| telecom | 28 | 电信机房、机架、PDU、线缆、光纤 |
| keyboard | 14 | 机械键盘装配、DFX |
| datacenter | 9 | 模块化集装箱、电源 |
| environments | 4 | 运行环境、材料兼容性 |
| manufacturing | 5 | 工艺、材料约束 |
| consumer_electronics | 3 | 小型电子产品连接 |
| 内置接口检查 | 2 | 接口类型存在性、方向一致性 |
| **合计** | **64** | — |

Table: piki 规则目录按插件分布。{#tbl:rule-catalog}

代表性电信规则：

| 规则 ID | 名称 | 层级 | 说明 |
|---------|------|-----|------|
| `INTERFACE-COMPAT-001` | 接口类型兼容性 | L2 | Mate/Connection 端点接口可配对 |
| `INTERFACE-CABLE-001` | 线缆-接口匹配 | L2 | `cable_type` 与端口接口类型一致 |
| `TELECOM-POWER-001` | PDU 功率预算 | L3 | 负载不超过容量阈值 |
| `TELECOM-RACK-001` | U 位冲突 | L3 | 同一机柜设备 U 位不重叠 |
| `TELECOM-COLLISION-001` | 机柜内 3D 碰撞 | L4a | 基于 AABB 的空间冲突检测 |
| `TELECOM-FLOOR-002` | 维护通道宽度 | L4a | 同排机柜间距满足最小值 |

Table: piki 电信场景代表性规则。{#tbl:telecom-rules}

规则通过 `@rule(rule_id, ...)` 装饰器注册，项目可在逻辑阶段仅启用 L2，布局阶段再启用 L3–L4a。

## 5.4 操作性纲领

ESA 遵循四条原则：**规则可豁免**（记录审计轨迹并触发强化验证）；**聚焦底线规则**（功率、U 位、间距等二值确定性条款）；**左移与信噪比优化**（在设计时拦截低级错误）；**AI 辅助规则库构建**（LLM 从规范文本提取规则草稿 [@yang2024llmacc; @nakhaee2024kgllm]）。

## 5.5 诊断、CI 与下游验证

ESA 产出统一 JSON 诊断，兼容 LSP，可驱动终端摘要、CI 面板、IDE 叠加和 PR bot。`piki check` 在电信样本上 <200ms 完成。

CI 管道按成本分层：L0 每次提交；L1–L4a 每次 PR；交付物在合并后构建；nightly 覆盖几何和 CAE/CFD。pre-commit 镜像廉价检查。

ESA 边界限于可从声明确定性检查的内容：L2–L3 和 L4a。L4b（精确碰撞）、L5（物理仿真）、L6（专家签审）属下游验证。`piki check` 通过后，CI 将 ADL 导出为 STEP/USD 调用 CAD/CAE；下游发现以兼容 Diagnostic 格式回流，但不合并到 ESA 规则库。

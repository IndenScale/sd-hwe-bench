# 4. ADL：装配体定义语言

ADL 是 EaC 的声明式、文本原生设计表示。它围绕三个正交子语言组织，分别回答"存在什么"、"部件如何耦合"和"它们放在哪里"。参考运行时 **piki** 加载 ADL、运行规则引擎并生成下游交付物，但 ADL 定义独立于工具。

## 4.1 设计目标

1. **文本原生**：Agent 和人类以纯文本读写设计意图，支持版本控制、差分和可编程生成。
2. **面向 Agent**：显式身份、引用和确定性验证，无 GUI 隐藏状态。
3. **正交性**：身份、关系、空间变更互不强制重写其他维度。

## 4.2 Part 与 PDL

**Part** 是工程描述的原子单元，语义完整、封装内部几何、通过有类型接口参与显式关系。**PDL（部件定义语言）** 在 **Family**、**Model**、**Instance** 三层上定义 Part 类型系统：Family 是 pydantic 模式（如 `ServerFamily` 要求 `height_u`、`tdp_w`、接口规格）；Model 提供默认值；Instance 覆盖默认值。运行时解析为 `Model.defaults + Instance.overrides` 并对照 Family 验证。关键决策：**Instance 文件不含布局信息**，布局在 PLL 中单独声明，使同一设备可在不同方案中复用。

## 4.3 PML：部件配合语言

PML 区分 **Mate**（设计耦合，约束两个 Part 如何配合）和 **Connection**（两个接口之间的信号/能量/物料流动，本身是一等 Instance）。Mate 存储在 `mates/<mate_type>/` 下（如 `rack-mount-19inch`、`power-iec-c14-c13`）。Mate/Connection 分离映射机械/电气可行性与功能拓扑正确性两个独立阶段，而 CAD/BIM 常将二者合并，难以独立验证。

## 4.4 PLL：部件布局语言

PLL 消除 PML 保留的自由度：连续自由度（平移、旋转）和离散状态，以及自由 Part 的全局位姿（绝对坐标或 `parent` + `transform` 链）。当前实现为**装配体类骨骼建模**：键盘样本中 `CASE-01` 为根，PCB、定位板等通过 `parent: CASE-01` 声明骨架层级，Mate 文件独立表达焊接、卡扣约束，保持三层正交。PLL 边界：连续 DOF 求解精度为主轴近似，尚未扩展管线/缆索等 1D 路径。

## 4.5 正交性的好处

PDL/PML/PLL 分别位于 `instances/`、`mates/`、`layouts/` 中，带来：**增量验证**（Agent 可先通过 L0–L2，再处理 PML/PLL）；**并行编辑**（Git 冲突限制在同一决策维度）；**语义 diff**（变更维度直接可读，便于审查和 RLVR 奖励归因）。

## 4.6 与 SysML v2 和 BIM/IFC 的比较

| 维度 | SysML v2 [@omg2024sysml] | BIM / IFC [@buildingsmart2023ifc] | ADL（piki） |
|------|--------------------------|-----------------------------------|-------------|
| 真相源 | 模型仓库 | 中心模型文件 / IFC | 文本文件（YAML） |
| 版本控制 | 模型版本 | 文件版本 | Git 行级历史 |
| 身份与空间 | 混合 | 几何即身份 | Instance 与 Layout 文件级分离 |
| 关系 | `connection` / `interaction` | 隐含于几何 | `Mate` + `Connection` 显式分离 |
| 验证 | 模型检查 | 事后碰撞检测 | ESA L0–L4a，毫秒级 |
| 目标用户 | 人类（GUI） | 人类（GUI） | Agent + 人类（文本） |

Table: ADL 与 SysML v2、BIM/IFC 的对比。{#tbl:adl-comparison}

SysML v2 和 BIM 面向人类 GUI 用户，真相源难以差分、分支和自动验证；IFC 将身份、几何和关系耦合 [@liu2023ifcversion]。ADL 以文本为唯一真相源，CAD/BIM 成为下游消费者。



# 4. ADL：装配体定义语言

ADL 是 Engineering as Code 的声明式设计表示。它被有意设计为文本原生：设计意图以 YAML 编写，以代码验证，而非在 CAD 或 BIM GUI 内被捕获为几何操作。ADL 围绕三个正交子语言组织，将"存在什么"、"部件如何耦合"以及"它们放在哪里"分离。

## 4.1 设计目标

ADL 追求三个目标：

1. **文本原生表示**。Agent 和人类可以以纯文本编写和阅读设计意图，实现版本控制、差分和可编程生成。
2. **面向 Agent 的语法**。文件具有显式身份、引用和确定性验证。不存在依赖 GUI 会话的隐藏状态。
3. **身份、关系与空间的正交性**。某维度的变更不应强制重写另一维度的文件。

参考运行时是 **piki**，一个加载 ADL 声明、运行分层规则引擎并生成下游交付物的开源引擎。然而 ADL 的定义独立于任何单一工具。

## 4.2 Part 作为工程原子

在 ADL 中，**Part** 是工程描述的原子单元。Part 不仅仅是一个几何体；它是一个语义完整的实体，暴露有类型的接口并参与显式关系。Part 由以下要素定义：

- **Family**（模式与值域约束）
- **Model**（带有默认值的具体实现）
- **Instance**（可覆盖默认值的部署实体）
- 一组有类型的 **Interface**
- 可选的内部几何，除非需要高精度分析，否则保持隐藏

Part 抽象建立在四个性质之上：

1. **语义完整性**。服务器 Part 类型为 `ServerFamily`，携带 `height_u`、`tdp_w`、`psu_count` 等字段。泵 Part 携带 `flow_rate` 和 `head`。类型检查由插件注册的 pydantic 模式执行。
2. **封装性**。内部几何被隐藏；只有标准化接口对下游消费者可见。
3. **关系内建性**。服务器在装配体中的角色通过关系表达：它是 `rack-mount-19inch` Mate 中的 `child`；光模块是 `sfp28-cage` Mate 中的 `child`。
4. **多视图投影能力**。同一 Part 可投影到 CAD（USD/glTF）、CAE（热或结构模型）、ERP（BOM 条目）和生命周期目录，而不改变其核心声明。

## 4.3 PDL：部件定义语言

PDL 在三个层次上定义 Part 类型系统：**Family**、**Model** 和 **Instance**。

**Family**。Family 是一个 pydantic `BaseModel` 类，声明某类 Part 的模式和值域约束。例如 `ServerFamily` 要求 `id`、`height_u`（1–48）、`tdp_w`（>0）和接口规格列表。Family 是代码，而非配置；由插件注册。

**Model**。Model 为 Family 提供具体默认值。示例 model 文件：

```yaml
model: dell-r750
family: ServerFamily
brand: Dell
mpn: PowerEdge R750
height_u: 2
tdp_w: 600
psu_count: 2
```

**Instance**。Instance 是可覆盖 Model 默认值的部署实体：

```yaml
id: SRV-01
model: dell-r750
family: ServerFamily
status: planned
```

运行时，解析值计算为 `Model.defaults + Instance.overrides`，然后对照 Family 模式验证。Instance 的身份从文件名衍生（`SRV-01.yaml` → `SRV-01`）。一项关键设计决策是**Instance 文件不包含布局信息**；布局在 PLL 中单独声明。这种分离意味着同一设备可在不同设计方案的多个位置使用，无需复制其定义。

## 4.4 PML：部件配合语言

PML 描述 Part 之间的关系，区分两类：**Mate** 和 **Connection**。

**Mate** 表达设计耦合：约束两个 Part 如何配合或共同工作。Mate 存储为 `mates/<mate_type>/` 下的独立 YAML 文件。例如：

```yaml
type: rack-mount-19inch
parent: RACK-A02
child: SRV-01
at:
  u_start: 10
  u_span: 2
constrains:
  - field: depth_mm
    operator: "<="
    value_ref: depth_mm
```

引擎在加载时验证这些约束。已注册的 Mate 类型包括 `sfp28-cage`、`power-iec-c14-c13` 和 `lc-connector`。

**Connection** 表达两个接口之间的信号、能量或物料流动。Connection 本身是一个一等 Instance：

```yaml
id: CONN-ACCESS-SRV01
family: PortConnectionFamily
from_port: ACCESS-SW-01/10GE1/0/1
to_port: SRV-01/eth0
cable_type: OM4-LC-LC
```

Mate/Connection 的分离映射到两个独立的设计阶段：机械或电气可行性（Mate）和功能拓扑正确性（Connection）。CAD/BIM 系统常将它们合并为一个对象，使得无法在不涉及另一维度的情况下验证其中之一。

## 4.5 PLL：部件布局语言

PLL 的本质是**消除自由度**——包括 PML 配合中为保持可操作性而保留的几何自由度，以及装配体中无 Mate 认领的自由 Part 的全空间自由度。

PLL 按优选级链条工作。（1）对于在 PML 中存在 Mate 的 Part，被 Mate 认领为 child 的 Part，其位姿主要由 PML 配合约束求解器确定；PLL 提供参数化的自由度补全——为 Mate 中保留的连续自由度（平移、旋转、螺旋）和离散状态（正插/反插/拔出）赋予具体取值（`at.u_start`、`at.t`、`at.state`）。配合求解器支持面贴合（face）、轴配合（axis）和槽配合（slot）三类约束，均携带连续 DOF 参数（距离、转动角度、推入距离）。（2）对于装配体中无 Mate 认领的自由 Part，PLL 以全局位姿赋值作为弱约束——通过绝对坐标（`position_x/y/z_mm`）、网格定位（`grid_id`/`grid_position`）或相对坐标链（`parent` + `transform`）为自由 Parts 提供初始放置。

当前 ADL 已实现**装配体类骨骼建模**。Layout 中的 `parent` + `transform` 链明确区分装配结构（骨架）与子零件位姿，PML 中的 Mate 关系则在此骨架上叠加配合约束。键盘样本演示了此模式：`CASE-01` 作为装配根 Part，`PCB-01`、`PLATE-01`、`BATT-01` 等子 Parts 通过 `parent: CASE-01` 声明骨架层级，Mate 文件独立表达焊接、卡扣、螺丝柱等配合约束。这种双层分离使骨架修改（如外壳变体）与配合修改（如替换连接件类型）互不污染，保持了 PDL/PML/PLL 的正交性。

当前 PLL 实现的已知边界：连续 DOF 的几何求解精度当前为主轴近似，尚未扩展到管线/缆索等 1D 连续路径拓扑。这些留给未来求解器精度增强和外部 CAE 工具处理。

## 4.6 正交性

PDL、PML 和 PLL 的正交性是 ADL 的核心设计原则。每个子语言位于独立的文件中：PDL 在 `instances/` 和 `models/`，PML 在 `mates/`，PLL 在 `layouts/`。因为命名空间分离，某维度的变更不重写另一维度的文件。

**增量验证**。Agent 可首先生成 PDL 声明并通过 L0–L2 检查，然后再处理 PML 约束和 PLL 空间规则。这与编译器的分阶段错误反馈相匹配。

**并行编辑**。设备工程师编辑 `instances/SRV-01.yaml`，布局工程师编辑 `layouts/layout.yaml`，机械工程师编辑 `mates/rack-mount/RACK-A02-SRV-01.yaml` 可以同时进行。Git 合并冲突仅在同一决策维度变更时发生。

**语义 diff**。`instances/` 的 diff 表示"某些设备身份或属性变更"；`mates/` 的 diff 表示"某些配合变更"；`layouts/` 的 diff 表示"某些位置变更"。例如：

```diff
- position_u: 10
+ position_u: 12
```

明确地是一个布局变更，而 `instances/SRV-01.yaml` 中 `tdp_w` 的变更则是一个电气变更。这种可解释性同时支持人类代码审查和 RLVR 训练中的自动奖励归因。

## 4.7 与 SysML v2 和 BIM/IFC 的比较

ADL、SysML v2 和 BIM/IFC 均致力于工程系统的形式化，但它们在真相源形态、协作单元和目标用户等假设上存在根本差异。

| 维度 | SysML v2 [@omg2024sysml] | BIM / IFC [@buildingsmart2023ifc] | ADL（piki） |
|------|--------------------------|-----------------------------------|-------------|
| 真相源形态 | 模型仓库 | 中心模型文件 / IFC 交换 | 文本文件（YAML + TOML） |
| 版本控制单元 | 模型版本 | 文件版本 | Git 行级历史 |
| 核心操作单元 | 模型元素 | 几何对象 / IFC 实体 | 文件（Instance、Mate、Layout） |
| 身份与空间 | 混合在 part/occurrence 中 | 几何即身份 | Instance 与 Layout 文件级分离 |
| 部件间关系 | `connection` / `interaction` | 隐含于几何约束 | `Mate` + `Connection` 二元分离 |
| 验证方式 | 模型检查 | 碰撞检测（事后） | ESA L2–L4a + 加载期 L0–L1 检查，毫秒级 |
| 目标用户 | 人类系统工程师（GUI） | 人类设计师（GUI） | AI Agent + 人类工程师（文本） |

SysML v2 和 BIM 主要是面向人类工程师的建模环境。其真相源位于难以差分、分支和自动验证的仓库或大型中心文件中。IFC 尤其将身份、几何和关系耦合在一个允许多种等价序列化的图中，使行级版本控制困难 [@liu2023ifcversion]。

ADL 反转了这些优先级。它面向 Agent-人类协作，将文本作为唯一真相源，并使验证成为一等关注。CAD 和 BIM 不被消除；它们成为 ADL 声明的下游消费者，用于可视化、碰撞检测和制造。

## 4.8 核心语法摘要

以下语法概括了 ADL 的核心构造。

```text
Project       ::= piki.toml (ModelFile | InstanceFile | MateFile | LayoutFile | CatalogFile)*

ModelFile     ::= "model:" id
                  "family:" FamilyName
                  Field*
                  ("interfaces:" InterfaceSpec*)?

InstanceFile  ::= "id:" id
                  ("family:" FamilyName | "model:" ModelName)
                  Field*
                  ("interfaces:" InterfaceSpec*)?

InterfaceSpec ::= "- id:" id
                  "interface_type:" Type
                  ("direction:" "input" | "output" | "bidirectional")?
                  ("local_transform:" Transform)?

MateFile      ::= "type:" MateType
                  "parent:" Ref
                  "child:" Ref
                  ("at:" Map)?
                  ("constrains:" MateConstraint*)?
                  ("pairings:" InterfacePairing*)?

MateConstraint::= "- field:" Field
                  "operator:" "<=" | ">=" | "<" | ">" | "==" | "!="
                  "value_ref:" FieldOrConstant
                  ("message:" String)?

LayoutFile    ::= LayoutEntry*
LayoutEntry   ::= "- instance:" id
                  (AbsolutePose | RelativePose | GridPose)

AbsolutePose  ::= ("position_x_mm:" num)+
RelativePose  ::= "parent:" id
                  "transform:" Transform
GridPose      ::= "grid_id:" id
                  ("grid_position:" [String, String]
                  | "row_id:" String "bay_index:" Int)

Transform     ::= "translation:" [num, num, num]
                  ("rotation:" [num, num, num])?
                  ("scale:" [num, num, num])?

Ref           ::= id | id "/" interface_id
```

语法未捕获的关键语义约束包括：`InstanceFile` 不得包含布局字段；`LayoutEntry` 必须使用绝对、相对或网格位姿之一且仅一；`Ref` 中的接口引用必须解析为已存在的接口。

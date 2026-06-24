<!-- markdownlint-disable MD041 -->
<!--
# 07 Adl Vs Sysml Ifc
位置：第 5.6 节 与 SysML v2 和 BIM/IFC 的比较
字数：约 298 词
目标：正文
-->

ADL、SysML v2 和 BIM/IFC 都旨在形式化工程系统，但它们在事实来源、协作单元和目标用户的假设上存在根本差异。下表总结了 ADL 的设计依据。

| 维度 | SysML v2 | BIM / IFC | ADL (piki) |
|---|---|---|---|
| 事实来源 | 模型仓库 | 中心模型文件 / IFC 交换 | 文本文件（YAML + TOML） |
| 版本控制单元 | 模型版本 | 文件版本 | Git 行级历史 |
| 核心操作单元 | 模型元素 | 几何对象 / IFC 实体 | 文件（Instance、Mate、Layout） |
| 身份与空间 | 混合在 part/occurrence 中 | 几何即身份 | Instance 与 Layout 在文件级分离 |
| 部件间关系 | `connection` / `interaction` | 隐含于几何约束 | `Mate` + `Connection` 双重分离 |
| 校验 | 模型检查 | 几何碰撞检测（事后） | ESA 规则引擎 L2–L4a + ADL 加载期校验 L0–L1，毫秒级 |
| 目标用户 | 人类系统工程师（GUI） | 人类设计师（GUI） | AI 智能体 + 人类工程师（文本） |

SysML v2 和 BIM 主要是面向人类工程师的建模环境。它们的事实来源位于仓库或大型中心文件中，难以进行差异比较、分支和自动校验。特别是 IFC，将身份、几何和关系耦合在一个允许多种等价序列化的图中，使得行级版本控制变得困难 [@liu2023ifcversion]。

ADL 颠倒了这些优先级。它以智能体–人类协作为目标，将文本视为唯一事实来源，并将校验作为一等关切。CAD 和 BIM 没有被取代；它们成为 ADL 声明的下游消费者，用于可视化、碰撞检测和需要几何保真度的制造。这一定位类似于芯片设计中 Verilog 网表与物理版图之间的关系。

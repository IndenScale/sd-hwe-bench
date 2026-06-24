# 7. 相关工作

## 7.1 RLVR 与工程基准

RLVR 文献证明确定性验证信号可驱动 Agent 能力提升：DeepSeek-R1 [@deepseek2025r1]、SWE-RL [@sweagent2025swerl]、Multi-SWE-bench [@multiswebench2025]。这些工作确立 RLVR 因果链的后半段；EaC 关注前半段——缺少结构化表示时 RLVR 无法启动。

工程 AI 基准中，AEC-Bench 评估 AI 审阅图纸而非生成 [@galanos2026aecbench]；EngDesign 在 CAD/BIM 工作流任务上评估模型，不要求"Design as Code" [@engdesign2025]。EDA 基准（VerilogEval [@liu2023verilogeval]、ChipBench [@chipbench2025]、AMS-IO-Bench [@liu2025amsio]）已受益于"Circuit as Code"，为 SD-HWE-Bench 提供上界参考。ACC 社区 [@eastman2009acc; @zhang2019acc] 及 LLM 规范-规则转换工作 [@fuchs2024llmregs; @yang2024llmacc; @nakhaee2024kgllm] 仍在设计完成后运行，受困于几何假阳性和翻模开销。

## 7.2 声明式建模与 AI4E 路线

**SysML v2** 面向人类 GUI 建模，真相源在模型仓库中 [@omg2024sysml]；ADL 面向 Agent-人类文本协作，真相源在 YAML 中。**BIM/IFC** 将身份、几何和关系耦合，行级版本控制困难 [@buildingsmart2023ifc; @liu2023ifcversion]。**IaC** 提供"X as Code + static analysis"的直接类比 [@morris2022iac; @quattrocchi2023iacsurvey; @chiari2024iacstatic]。

AI4E 路线主要有 **CUA**（GUI 操作 CAD，界面脆弱、验证缺失）和 **CAD-MCP**（结构化工具接口，但绑定专有内核、未解决真相源）。EaC 从表示层重建：以可计算工程描述为中心，CAD/CAE 成为下游消费者，Agent 直接操作真相源。

## 7.3 系统化对比

| 维度 | ACC | CUA | CAD-MCP | BIM/IFC | SysML v2 | **EaC** |
|------|-----|-----|---------|---------|----------|--------|
| 真相源 | CAD/BIM 模型 | CAD GUI | CAD 内核 | 中心模型文件 | 模型仓库 | **YAML 文本** |
| 验证时机 | 设计完成后 | 无 | 工具级 | 设计完成后 | 模型级 | **设计时** |
| 验证速度 | 秒至分钟 | — | 依赖工具 | 分钟级 | 模型检查级 | **毫秒级** |
| 版本控制 | 文件级 | 文件级 | 文件级 | 模型版本 | 模型版本 | **Git 行级** |
| Agent 友好度 | 否 | 间接 | 部分 | 否 | 部分 | **是** |
| RLVR 兼容性 | 否 | 否 | 否 | 否 | 部分 | **是** |
| 检查语义层级 | 命名约定 | — | 工具 API | 属性集 | 模型元素 | **Family 类型系统** |
| 假阳性抑制 | 无 | — | — | 无 | 部分 | **Mate 排除** |

Table: EaC 与主要相关工作的系统化对比。{#tbl:related-work}

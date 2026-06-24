# 2. 背景与动机

## 2.1 RLVR 因果链

代码、数学和芯片设计共享一个模式：**结构化、可检查的表示 → 快速确定性反馈 → RLVR 有效**。

- **数学**：DeepSeekMath/R1 在可验证步骤上训练，PRM 优于 ORM [@shao2024deepseekmath; @deepseek2025r1; @lightman2023letsverify]。
- **代码**：SWE-RL 以测试通过/失败为奖励信号训练 Agent [@sweagent2025swerl]。
- **芯片**：DRC/LVS 提供可计算反馈，支撑布局 Agent 训练 [@mirhoseini2020rlchip; @liu2025amsio]。

## 2.2 工程表示的缺陷

物理工程仍依赖 CAD/BIM/IFC，将功能身份、几何实现和工具状态耦合。这对 AI Agent 造成**信息损失**（意图冻结为几何后需逆向提取 [@eastman2009acc; @zhang2019acc]）、**反馈延迟**（ACC 在设计完成后运行）和**无训练信号**（RLVR 闭环断裂）。近期 LLM 规范解读工作仍在设计下游运行 [@fuchs2024llmregs; @yang2024llmacc; @nakhaee2024kgllm]。

基于模型的 ACC 还有两项结构性缺陷：**纯几何碰撞产生大量假阳性**（无法区分预期贯穿与真实冲突）；**命名依赖导致翻模开销**（规则需按项目适配，难以形成标准化基准）。根源是几何表示语义贫乏。

## 2.3 启示与缺口

IaC 证明"X as Code + static analysis"可行 [@chiari2024iacstatic; @morris2022iac; @quattrocchi2023iacsurvey]；芯片 Verilog + DRC 证明文本表示可作为逻辑真相源 [@ieee1364]。工程领域缺少**上游的、文本原生的、可被机器检查的设计表示**。EaC 填补这一缺口。

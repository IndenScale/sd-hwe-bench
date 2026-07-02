# Physical Engineering as Code Evaluation Substrate Paper Instructions

本目录是 Physical Engineering as Code 评估底座论文的写作真相源。

## 投稿路线（v4 pivot）

当前版本以 **NeurIPS Evaluations & Datasets** 路线为主。论文不再只 sell “三重鸿沟”问题框架，而是提出 **Physical Engineering as Code (PEaC)**：将 Engineering as Code (EaC) 范式实例化为 physical engineering evaluation 的 **executable substrate**，把工程状态、约束、诊断、修复和情境化知识组织成可复现评测闭环。

三重鸿沟仍是理论框架，但服务于 substrate 贡献：

1. **表征鸿沟**解释为什么 physical engineering evaluation 需要可提交、可 diff、可检查的工程状态。
2. **约束鸿沟**解释为什么 evaluation substrate 必须有可执行 critic、局部诊断和 repair loop。
3. **知识鸿沟**解释为什么 physical engineering evaluation 不能止步于合规，还要让设备曲线、气候、电价、成本和施工风险进入优化目标。

AI Data Center Design 是 reference domain / stress test，而不是单纯应用案例。AIDC 同时包含设备选型、布局、电力、冷却、储能、光伏、施工排程、运营调度、气候、电价和成本，适合展示 PEaC 如何 bridge representation, constraint, and knowledge gaps。

### 当前阶段：arXiv + workshop / E&D preprint

短期目标是形成一篇可以公开占位的中文/英文稿：

- **arXiv**：发布 PEaC executable substrate、三重鸿沟 framing、AIDC reference implementation 和三组实验协议。
- **workshop / position**：优先投 AI agents、evaluation、AI for engineering、AI for science、AI4EDA、agentic software engineering、AIware 等方向。
- **NeurIPS E&D 准备**：补齐表征、约束和 AIDC 知识实验后，转为 empirical evaluation substrate paper。

### 补实验后的主目标

首选 NeurIPS 2027 Evaluations & Datasets Track。

理由：本文真正卖点是 evaluation science 与 executable substrate，而不是单纯 dataset 规模。NeurIPS E&D 接受 evaluation protocol、benchmark methodology、failure mode analysis、可复现 artifact 和 benchmark substrate；这与本文的 pseudo-correctness、可执行约束、repair saturation 和 AIDC Pareto-frontier 叙事高度匹配。

最低实验门槛：

- 公开 PEaC-Bench artifact、ADL 文件、DTS checker 和 baseline scripts。
- 至少 3-5 个模型/Agent baseline。
- 表征实验：MCP / CUA / OpenSCAD / ADL 不必全部做到工业级，但必须有可测对照。
- 约束实验：NL-only vs Docs-only vs Executable 必须有 pass rate、pseudo-correctness rate、omission density 和 repair curve。
- 失败分析：按 constraint layer、omission type、repair saturation 统计。
- 复现性：容器、task spec、scoring protocol、data card 或 artifact note。

### 备选主会路线

- **ASE / FSE / ICSE**：可行，但需要重写成 agentic software engineering / executable specification evaluation paper。标题和主张应收窄为 pseudo-correctness、repair loop、executable critics，而不是泛化为工程 AI 总论。
- **MLSys**：只有在平台系统、throughput、cost、orchestration、可扩展任务生成等系统结果足够强时再考虑。
- **DAC / ICCAD / DATE**：暂不作为主目标。除非 AIDC/DTCO 或 system-level design automation 实验非常硬，否则传统 EDA reviewer 可能认为本文缺少芯片/EDA flow/PPA/verification 等核心结果。

### 一句话策略

**当前稿件：PEaC executable substrate 的 arXiv/workshop 版。补齐表征、约束与 AIDC 知识实验后：主投 NeurIPS E&D。若转 SE 圈：改写为 physical engineering evaluation / executable specification paper。AIDC/DTCO 做强后，再考虑 MLSys 或设计自动化 venue。**

## 核心主张（v4）

工程 AI 发展缓慢，不是因为工程任务天然无法评估，也不是因为模型单点推理能力完全不足，而是因为系统级工程缺少可供 agent 反复提交、检查、诊断、修复和优化的 evaluation substrate。

本文提出 Physical Engineering as Code 作为这种底座：工程状态以文本原生、版本化、可检查的 ADL 表达；工程正确性由 DTS 分层 critic 判定；repair loop 将错误反馈转化为可消费诊断；AIDC reference implementation 将设备曲线、气候、电价、成本和施工风险纳入评估目标。

PEaC-Bench 在本论文中是 PEaC substrate 的当前实现和证据载体。

本文的主张强度来自三层递进，而不是 benchmark 规模：

1. **从 benchmark prompt 到工程提交对象**：表征鸿沟解释为什么物理工程评估需要可闭环表征。
2. **从自然语言正确到可执行正确**：约束鸿沟解释为什么 pseudo-correctness 普遍存在，以及为什么 repair loop 需要可定位 critic。
3. **从规则合规到前沿最优**：知识鸿沟解释为什么系统级工程评估需要 PDK-like、可优化的知识基础设施。

因此，本论文必须避免写成“我们提出一个小规模 benchmark”。正确叙事是：**我们提出 Physical Engineering as Code 作为 physical engineering evaluation 的 executable substrate，并用 AI Data Center Design 展示它如何 bridge representation, constraint, and knowledge gaps。**

## 实验轴

### 约束鸿沟实验

这是当前最容易形成硬证据的一组实验，但它不是“优先级编号”，而是三重鸿沟中的一个实证轴：

- NL-only：仅任务描述中的自然语言约束。
- Docs-only：任务描述 + 多部规范目录，但无提交前自动检查。
- Executable：同样规范 + DTS/piki check + repair loop。

必须报告：

- pass@1 / pass@k / repair 后 pass rate。
- pseudo-correctness rate。
- omission density。
- top omission constraints。
- repair saturation curve。

### 表征鸿沟实验

目标不是证明 ADL 全面优于所有工具，而是证明不同表征是否能形成可复现工程评估闭环。当前收敛为一个单零件 / 工装夹具 OpenSCAD 建模任务：MCP、CUA 与 ADL + OpenSCAD 都应能完成任务，差异体现在提交确定性、语义约束覆盖、错误定位、repair 和归档重评能力。

- MCP：通过工具/API 查询、生成或检查 OpenSCAD 工件。
- CUA：通过 GUI/CAD-like 交互完成几何建模并导出工件。
- ADL + OpenSCAD：用 ADL 描述规格语义和工程约束，再生成或约束 OpenSCAD 几何。

必须报告：

- task formalization cost。
- submission determinism。
- feedback latency。
- error localization。
- repairability。
- scoring coverage。

### 知识鸿沟 / AIDC DTCO probe

作为前沿价值 case study，不要求一开始做大。对比：

- Fixed Design：设备和布局固定，只优化调度。
- Equipment-only：可优化冷机、储能、变压器、光伏等设备选型。
- Schedule-only：设备固定，可优化调度策略。
- Joint DTCO：设备选型 + 布局 + 调度联合优化。

必须报告：

- PUE / TCO / SLA violation / CAPEX / OPEX。
- CAPEX-TCO 或 CAPEX-SLA Pareto frontier。
- 当地气候、电价、设备价格和设备曲线对结果的影响。
- joint optimization 是否使 Pareto frontier 外移。

## 目录约定

- `src/sections-zh/`：中文创作源文件。
- `src/dist/draft-full.zh.md`：组装后的中文全文，由 `scripts/assemble_peac_eval_substrate.py` 生成。
- `src/sections-zh/meta.yaml`：标题、摘要和关键词元数据。

## 写作约束

- 优先写中文源文件，英文版待主张稳定后翻译。
- 不在本目录重复维护 PEaC-Bench 任务定义；任务、评分器、runs 与 leaderboard 的真相源仍在代码库根目录。
- 任何实验数字必须来自真实脚本、run artifact 或可复现计算；占位内容必须明确标注为待实验。
- 本论文避免被写成“又一个 benchmark paper”；每章都应服务于 PEaC substrate 主张。
- 不把 workshop/position 版本写成退而求其次的弱稿；它应当是三重鸿沟 framing 的清晰公开版本。
- 主会版本必须以实验一和实验二为硬证据，实验三作为前沿价值 probe；不要用 AIDC DTCO 的未完成大叙事替代可复现核心实验。

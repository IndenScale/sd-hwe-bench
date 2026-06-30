# Engineering AI Gaps Paper Instructions

本目录是“三重鸿沟”论文的独立写作真相源，不直接改写 `papers/sd-hwe-bench/`。

## 投稿路线（v3 pivot）

当前版本不按主会 full paper 直接冲刺。本文现在的强项是**问题框架、评估议程和实验设计**：表征鸿沟、约束鸿沟、知识鸿沟，以及 SD-HWE-Bench 作为可执行实验平台。但正文仍有多处“待补实验”，因此当前形态更接近 **vision / position + benchmark proposal + experiment design**，还不是完整 empirical benchmark paper。

### 当前阶段：arXiv + workshop / position

短期目标是形成一篇可以公开占位的中文/英文稿：

- **arXiv**：优先发布三重鸿沟 framing、SD-HWE-Bench 作为 executable testbed 的设计、以及三组实验协议。
- **workshop / position**：优先投 AI agents、evaluation、AI for engineering、AI for science、AI4EDA、agentic software engineering、AIware 等方向的 workshop 或 position track。
- **不硬投主会 full paper**：在表征实验和约束实验补齐前，不把本文包装成完整 benchmark/data paper。

### 补实验后的主目标

补齐实验一和实验二后，首选 NeurIPS 2027 Evaluations & Datasets Track。

理由：本文真正卖点是 evaluation science，而不是单纯 dataset 规模。NeurIPS E&D 接受 evaluation protocol、benchmark methodology、failure mode analysis 和可复现评估 substrate；这与本文的 pseudo-correctness、可执行约束和 repair saturation 叙事高度匹配。

最低实验门槛：

- 公开 SD-HWE-Bench 任务、ADL 文件、DTS checker 和 baseline scripts。
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

**当前稿件：arXiv + workshop/position。补齐表征实验和约束实验后：主投 NeurIPS E&D。若转 SE 圈：改写为 agentic engineering evaluation / executable specification paper。AIDC/DTCO 做强后，再考虑 MLSys 或设计自动化 venue。**

## 核心主张（v3）

工程 AI 发展缓慢，不是因为工程任务天然无法评估，也不是因为模型单点推理能力完全不足，而是因为系统级工程缺少三类基础设施：

1. **表征鸿沟**：缺少可计算、可 diff、可验证、可修复的工程设计表征。
2. **约束鸿沟**：自然语言规范无法稳定阻止 pseudo-correctness；只有可执行约束才能形成严肃评估与 repair/RLVR 闭环。
3. **知识鸿沟**：前沿工程优化依赖设备、材料、工艺、气候、电价、供应链等情境化知识，而这些知识通常没有像半导体 PDK 那样被形式化并进入优化循环。

SD-HWE-Bench 在本论文中是实验平台和证据载体，而不是论文主角。现有 `papers/sd-hwe-bench/` 保持为 benchmark technical report。

本文的主张强度来自三层递进，而不是 benchmark 规模：

1. **从 toy benchmark 到可计算工程任务**：表征鸿沟解释为什么工程 AI benchmark 发展慢。
2. **从自然语言正确到可执行正确**：约束鸿沟解释为什么 pseudo-correctness 普遍存在，以及为什么 repair loop 能在可执行约束下迅速饱和。
3. **从规则合规到前沿最优**：知识鸿沟解释为什么保守规则不足以支撑 DTCO，系统级工程需要 PDK-like 知识基础设施。

因此，本论文必须避免写成“我们提出一个小规模 benchmark”。正确叙事是：**我们提出工程 AI 评估的三重鸿沟框架，并用 SD-HWE-Bench 作为 executable testbed 展示如何验证这些鸿沟。**

## 实验优先级

### P0：约束鸿沟实验

这是最关键、最容易形成硬证据的一组实验。优先完成：

- NL-only：仅任务描述中的自然语言约束。
- Docs-only：任务描述 + 多部规范目录，但无提交前自动检查。
- Executable：同样规范 + DTS/piki check + repair loop。

必须报告：

- pass@1 / pass@k / repair 后 pass rate。
- pseudo-correctness rate。
- omission density。
- top omission constraints。
- repair saturation curve。

### P1：表征鸿沟实验

目标不是证明 ADL 全面优于所有工具，而是证明不同表征是否能形成可复现工程评估闭环。对比：

- MCP：外部工具/API/文档接口。
- CUA：GUI 操作路径。
- OpenSCAD：code-like geometry。
- ADL：声明式工程对象 + 引用 + DTS。

必须报告：

- task formalization cost。
- submission determinism。
- feedback latency。
- error localization。
- repairability。
- scoring coverage。

### P2：知识鸿沟 / AIDC DTCO probe

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
- `src/dist/draft-full.zh.md`：组装后的中文全文，由 `scripts/assemble_engineering_ai_gaps.py` 生成。
- `src/sections-zh/meta.yaml`：标题、摘要和关键词元数据。

## 写作约束

- 优先写中文源文件，英文版待主张稳定后翻译。
- 不在本目录重复维护 SD-HWE-Bench 任务定义；任务、评分器、runs 与 leaderboard 的真相源仍在代码库根目录。
- 任何实验数字必须来自真实脚本、run artifact 或可复现计算；占位内容必须明确标注为待实验。
- 本论文避免被写成“又一个 benchmark paper”；每章都应服务于三重鸿沟主张。
- 不把 workshop/position 版本写成退而求其次的弱稿；它应当是三重鸿沟 framing 的清晰公开版本。
- 主会版本必须以实验一和实验二为硬证据，实验三作为前沿价值 probe；不要用 AIDC DTCO 的未完成大叙事替代可复现核心实验。

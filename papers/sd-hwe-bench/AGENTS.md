# SD-HWE-Bench 论文开发说明

> 本目录是 SD-HWE-Bench 数据集/基准论文的投稿真相源。
> 中文创作版本见 `src/sections-zh/`，英文版待翻译。

---

## 投稿目标

### 首选：NeurIPS 2027 Evaluations & Datasets Track

- **截稿时间**：预计 2027-05（以官方 CFP 为准）。
- **匹配理由**：
  - NeurIPS E&D Track 接收新 benchmark、评估方法论和 AI4Science 数据集。
  - 2026 年更名后强调「evaluation as scientific study」，与 SD-HWE-Bench 的 no-repair vs repair ablation、错误模式分析、分层诊断价值高度契合。
  - 给足时间窗口：从现在到截稿约 10 个月，可从 19 task 扩展到 30+、跑多模型 baseline、构建 container 复现包。

### 冲刺选项：ICLR 2027 Datasets & Benchmarks Track

- **截稿时间**：预计 2026-09/10。
- **条件**：如果 8 月中旬前能跑完 19 task × 3 model baseline 并完成 ablation，可尝试。
- **风险**：时间极紧，只作为冲刺选项；达不到条件果断放弃。

### 稳妥选项：ICML 2027 Datasets Track / NeurIPS 2028

- **作用**：如果 ICLR 冲刺失败、NeurIPS 2027 也错过，作为自然 fallback。

---

## 当前状态（2026-06-25）

| 维度 | 当前状态 | 目标状态 |
|---|---|---|
| 任务数量 | 19 个 telecom 任务 | 19+（telecom 域已足够），可选扩展到 30+ |
| Actor 基线 | Kimi(pass@1=100%)、OpenAI(deepseek-v4-pro/flash) | Kimi + DeepSeek-V4 + 1 个开源模型 pass@5 |
| 实验轮次 | pass@1 smoke + repair pilot | pass@5 + no-repair vs repair ablation |
| 容器环境 | Docker image 已构建（1.58GB），--sandbox docker 可用 | ✅ 容器化完成 |
| 复现包 | 代码 + 任务集 + image 就绪 | Container + code + 数据 + 脚本 |
| 论文正文 | 中文初稿（1197 行，10 节 + 4 附录） | 英文 NeurIPS E&D 格式完整稿件 |

---

## 论文核心贡献

1. **SD-HWE-Bench**：一个面向 AI Agent 的声明式硬件工程 benchmark。
2. **任务集**：19 个 telecom 任务——5 个 POC 手工任务覆盖 5 种 task_type + 14 个 canonical 增量任务（从 piki Git 历史自动提取）。
3. **评价协议**：L0-L4 分层静态分析 + deliverable 生成检查 + LLM-as-Judge rubrics。
4. **基线结果**：Kimi、DeepSeek Pro/Flash 的 pass@1 对比；repair loop 有效性验证。
5. **消融实验**：ESA feedback（repair loop）vs. no-repair，验证可计算表示层对 Agent 生成质量的因果价值。
6. **复现包**：container image + 代码 + 任务集 + runs/ 归档。

---

## 本目录约定

- `AGENTS.md`：本文件，投稿目标与开发约定。
- `src/sections-zh/`：中文初稿章节（01-10 + appendix/A-D + Z-glossary），meta.yaml 驱动元数据。
- `index.md`：中文初稿全文（已不维护，以 src/ 分段文件为准）。
- `dist/`：生成产物（当前 `sd-hwe-bench.zh.md` 为合并后的中文稿件）。
- `assets/references/`：参考文献（SWE-Bench、SWE-Bench Multimodal 等结构分析）。

**与代码库的关系**：

- benchmark 实现和任务集真相源在 `/Users/indenscale/workspace/sd-hwe-bench/`。
- 论文写作真相源在本目录。
- 不要在论文目录里重复维护任务定义。

---

## 下一步

1. **翻译英文版**：从 `src/sections-zh/` 翻译为 `src/sections-en/`
2. **补全实验**：19 task × Kimi × pass@5 container 模式
3. **写 ablation 章节**：no-repair vs repair 对比分析
4. **准备复现包**：container image + 一键复跑脚本
5. **确定最终格式**：NeurIPS / ICLR LaTeX 模板

---

## 风险与备选

- **NeurIPS 2027 E&D 若未接受**：转投 ICML 2028 / NeurIPS 2028，或先上 arXiv 建立优先权。
- **实验不及预期**：若 Kimi pass@5 在 14 canonical 任务上表现不佳，调整分析重点（错误模式 > 分数）。

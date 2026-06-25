# SD-HWE-Bench 论文开发说明

> 本目录是 SD-HWE-Bench 数据集/基准论文的英文投稿真相源。  
> 中文创作版本见相邻目录 `papers/sd-hwe-bench.zh/`。

---

## 投稿目标

### 首选：NeurIPS 2027 Evaluations & Datasets Track

- **截稿时间**：预计 2027-05（以官方 CFP 为准）。
- **匹配理由**：
  - NeurIPS E&D Track（原 Datasets & Benchmarks Track）接收新 benchmark、评估方法论和 AI4Science 数据集。
  - 2026 年更名后强调“evaluation as scientific study”，与 SD-HWE-Bench 的 no-repair vs repair ablation、错误模式分析、分层诊断价值高度契合。
  - 给足时间窗口：从现在到截稿约 10 个月，可以从容扩展任务集、跑多模型基线、构建 container 复现包。

### 冲刺选项：ICLR 2027 Datasets & Benchmarks Track

- **截稿时间**：预计 2026-09/10。
- **条件**：如果 8 月中旬前能把任务扩展到 12–15 个、跑完 3–4 个模型基线并完成 ablation，可以尝试投稿。
- **风险**：时间极紧，只作为冲刺选项；若达不到条件，果断放弃，不降低质量硬投。

### 稳妥选项：ICML 2027 Datasets Track

- **截稿时间**：预计 2027-01。
- **作用**：如果 ICLR 冲刺失败，可作为自然 fallback；声望和周期都适中。

---

## 论文核心贡献

1. **SD-HWE-Bench**：一个面向 AI Agent 的声明式硬件工程 benchmark。
2. **任务集**：覆盖 telecom / datacenter / mechanical 等子领域，每个任务包含 scaffold、reference solution、task metadata 和评分 rubric。
3. **评价协议**：L0–L4 分层静态分析 + deliverable 生成检查 + LLM-as-Judge rubrics。
4. **基线结果**：Kimi、DeepSeek Pro、GPT-4o/Claude 等 Agent 的 pass@1 / pass@5 对比。
5. **消融实验**：ESA feedback（repair loop）vs. no-repair，验证可计算表示层对 Agent 生成质量的因果价值。
6. **复现包**：container image、代码、任务集、runs/ 归档，支持一键复跑。

---

## 当前状态与差距

| 维度 | 当前状态 | 目标状态 |
|---|---|---|
| 任务数量 | 5 个 telecom 任务 | 15–20+，覆盖 2–3 个领域 |
| Actor 基线 | kimi、openai:deepseek-v4-pro | 3–4 个主流 Agent/API 模型 |
| 实验轮次 | pass@1 smoke | pass@5 + ablation |
| 容器环境 | `--sandbox none` | Docker/Podman container + 固定 image |
| 复现包 | 无 | container + code + 数据 + 脚本 |
| 论文正文 | 无 | NeurIPS E&D 格式完整稿件 |

---

## 本目录约定

- `AGENTS.md`：本文件，投稿目标与开发约定。
- `src/`：论文正文 Markdown / LaTeX 源文件（待创建）。
- `assets/`：论文插图、表格数据（待创建）。
- `Makefile`：构建入口（可选，待创建）。

**与代码库的关系**：
- benchmark 实现和任务集真相源在 `/Users/indenscale/workspace/sd-hwe-bench/`。
- 论文写作真相源在 `/Users/indenscale/workspace/sd-hwe-bench/papers/sd-hwe-bench/`。
- 不要在论文目录里重复维护任务定义；引用代码库中的路径即可。

---

## 下一步

1. 确定论文大纲（Introduction → Related Work → Benchmark Design → Tasks → Evaluation Protocol → Baselines → Ablation → Limitations → Conclusion）。
2. 选择并扩展任务集：优先在 telecom 内补齐 10 个任务，再评估是否加入 datacenter/mechanical。
3. 固化容器环境：构建 `sd-hwe-bench-piki` image，确保所有评分在 container 内可复现。
4. 跑完多模型基线：Kimi、DeepSeek Pro、GPT-4o/Claude 的 pass@5。
5. 完成 no-repair vs repair ablation。
6. 准备 replication package。

---

## 风险与备选

- **NeurIPS 2027 E&D Track 若未被接受**：转投 ICML 2028 / NeurIPS 2028，或先上 arXiv 建立优先权。
- **任务扩展不及预期**：若 8 月中旬前无法达到 12–15 个任务，则放弃 ICLR 冲刺，专注 NeurIPS 2027。

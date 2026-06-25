# FSE 2027 / AI Benchmark 投稿策略与实验补充备忘录

> 创建日期：2026-06-24  
> 目标 1：FSE 2027 Vision Track（Engineering as Code 概念/愿景论文）  
> 目标 2：NeurIPS 2027 Evaluations & Datasets Track（SD-HWE-Bench 基准数据集论文；冲刺 ICLR 2027，稳妥 ICML 2027）  
> FSE 投稿截止：2026-10-02

## 两个投稿目标的定位

| | FSE 2027 Vision Track | AI 会议 Dataset / Benchmark Track |
|---|---|---|
| 论文主题 | Engineering as Code：为什么 AI 需要可计算的工程表示层 | SD-HWE-Bench：一个用于评估 AI 在声明式硬件工程任务上的 benchmark |
| 目标社区 | 软件工程（SE） | 机器学习 / AI |
| 推荐会议 | FSE 2027 Vision Track | **首选 NeurIPS 2027 E&D Track**；冲刺 ICLR 2027；稳妥 ICML 2027 |
| 核心贡献 | 新范式、问题定义、初步证据、研究路线图 | 数据集/任务集、评价协议、多模型基线结果、复现包 |
| 实验要求 | 足以支撑愿景即可，不追求大规模 benchmark | 必须达到 AI benchmark track 的规模和严谨性 |
| 当前进度 | 概念清晰，缺 Agent 实证 | 只有 5 个任务，基础设施刚跑通 |

## 当前结论

**不立即用当前版本投稿 FSE 2027 Vision Track。**

当前稿件的 ADL / ESA 设计已经清晰，三个 sample 全过、违规注入 15/15 检出也验证了 checker 的能力；但论文核心假说 —— Information Representation Hypothesis（表示层缺失是工程 AI 瓶颈）—— 还缺少 agent 层面的实证。直接投稿容易被审稿人质疑“只验证了 checker，没验证 AI 因此变强”。

**建议：先补一个最小可行的 Agent 实验，再投 FSE 2027 Vision Track。** 若 8 周内实验无法落地，再考虑转投 NIER/position track 或先上 arXiv。

**SD-HWE-Bench 作为 AI 会议 Dataset / Benchmark Track 投稿，当前差距更大**：任务数量、领域覆盖、容器化复现、多模型基线都远远不够。它**不是 FSE 投稿目标**，而是独立的 AI benchmark 论文；是否赶得上下一个 AI 会议周期，需要单独评估。

## 需要补齐的证据链

| 已验证                                   | 待验证                               |
| ---------------------------------------- | ------------------------------------ |
| ADL 能表达真实工程设计（3 samples）      | Agent 能否从自然语言生成 ADL         |
| ESA 能检错、低延迟、零假阳性（违规注入） | 快速 ESA 反馈是否提升 Agent 生成质量 |
| 表示层在语法/语义层面可工作              | 表示层对 AI 训练信号的价值（P1）     |

## 建议的最小实验设计

### 1. 基线：多 Actor × 多任务 pass@k

- **任务**：5 个 telecom 任务（instance-declare / layout-design / connection-design / mating-design / comprehensive）
- **工具**：新增 `sd-hwe-bench run-repair`，默认最多 20 轮 repair，支持 Agent 通过 marker 文件主动报告完成/失败/预算耗尽。
- **Actor**：2 个 Actor
  - `kimi`（默认模型 `kimi-code/kimi-for-coding`）
  - `openai:deepseek-v4-pro`（DeepSeek OpenAI-compatible API）
- **Pass@k**：每个任务每个 Actor 跑 5 次独立 rollout
- **指标**：
  - 每层（L0–L4）的 pass 率
  - overall pass@1 / pass@5
  - deliverable 生成率（BOM、port-map、rack-panel 等）
  - 平均 actor_elapsed_s
  - repair 轮数分布与终止原因（success / done_but_failed / give_up / info_gap / no_solution / budget_exceeded / actor_error）

### 2. 核心 Ablation：ESA 反馈是否提升生成质量（验证 P1）

- **对照组**：Agent prompt 中只给任务描述 + ADL 规范，**不提供 `piki check` 的诊断输出**。
- **实验组**：Agent prompt 中加入上一轮 `piki check --format json` 的错误诊断，允许 1–2 轮 self-repair。
- **模型**：固定 `kimi` 默认模型做 ablation（成本可控后再用 `openai:deepseek-v4-pro` 跑交叉验证）。
- **指标**：对比 pass@1、L2/L3 错误数、修复后通过率。
- **预期叙事**：
  - 若实验组显著更好 → 直接支撑 P1。
  - 若提升有限 → 强调“即使现有 agent 仍不稳定，但 EaC 提供了可解释、可迭代的反馈通道，这是 CAD/BIM 不具备的”。

### 3. 错误分层分析

- 统计所有失败 rollout 中 L0/L1/L2/L3/L4 的失败分布。
- 识别最普遍的失败模式（如接口类型错误、U 位冲突、连接缺失）。
- 用于支撑 ESA 分层诊断的价值和后续规则库建设方向。

## 实验执行 checklist

- [x] 修复 reference solution / piki 引擎版本漂移，使 5 个 telecom task 的 solution 在本地 piki 下 L1–L4 全绿。
- [ ] 冻结 5 个 telecom task 的 `task.yaml`、scaffold 和 solution（待可行性测试后最终确认）。
- [x] 新增 `sd-hwe-bench run-repair` 命令，支持最多 20 轮 repair 与主动终止 marker。
- [x] 实现 baseline（无 ESA 反馈）prompt variant 与 `run-repair --no-repair` 对照模式。
- [x] 修复 `uv run` 自动把 piki/adl 回退到旧 git 版本的问题（通过 `tool.uv.sources` 锁定本地 editable）。
- [x] 测试套件全绿：`tests/` 49/49 通过。
- [ ] 确认 `sd-hwe-bench run-repair` 在 container 模式下对 Kimi / DeepSeek API 稳定可用（当前 Docker 未运行，使用 `--sandbox none`）。
- [x] 完成 5 tasks × 2 actors × pass@1 的可行性测试。
- [ ] 根据冒烟结果调整任务难度梯度和/或 prompt（instance-declare 必须显式要求 layout，deliverable checklist 需要加入 prompt）。
- [ ] 修复 OpenAIActor 内部默认走 `auto` sandbox 导致的 Docker 连接 warning。
- [ ] 跑完 5 tasks × 2 actors × 5 passes = 50 个 rollout，归档到 `runs/fse-poc-2026/`。
- [ ] 跑完 ablation：1 model × 5 tasks × 2 条件（no-repair vs repair）× 3 passes = 30 个 rollout。
- [ ] 汇总 manifest.json，产出表格和失败案例。
- [ ] 更新论文 §6（Evaluation）和 §3.2.2（Predictions），把实验结果接回假说。
- [ ] 准备 replication package（匿名 GitHub / Zenodo 链接）。

## 环境与 reference solution 修复（2026-06-24）

在启动正式 Agent 实验前，先修复了任务/引擎/测试套件的一致性：

| 问题 | 根因 | 修复 |
| ---- | ---- | ---- |
| `TELECOM-COLLISION-001` 在所有 5 个 telecom solution 中报设备冲突 | 旧 git 版 `adl/geometry/provider.py` 把 rack U 高映射到 Z 轴，但 AABB 碰撞检测仍按深度（`hd`）判断 Z 轴重叠，导致假阳性 | 通过 `tool.uv.sources` 锁定本地 `workspace/piki/adl` editable |
| `MATE-002` 报 PDU rack-mount child family 为空 | 旧 git 版 piki 在 PDU 无 model 时未正确解析 family | 同上，使用本地 piki 源码 |
| `uv run pytest` 中 `test_reference_solution_passes` 失败 | `uv run` 会根据 `uv.lock` 把手动 `uv pip install -e` 的本地 piki/adl 回退到 git 版 | 在 `pyproject.toml` 增加 `[tool.uv.sources]`，将 `adl`/`piki` 指向 `../piki/adl` 和 `../piki` 的 editable 路径，并重新 `uv lock` |

验证结果：
- `tasks/telecom/*/solution` 全部 `piki check` 通过（0 错误，30 规则全绿）。
- `uv run pytest tests/ -q`：49/49 通过。
- `uv run piki check ...` 与 `.venv/bin/piki check ...` 行为一致。

## 第一次全量冒烟测试结果（2026-06-24）

**配置**：`--sandbox none`，`--max-repair 2`（即最多 3 轮），`--passes 1`，5 telecom tasks × 2 actors。

| Task | kimi | openai:deepseek-v4-pro |
| ---- | ---- | ---------------------- |
| instance-declare-001 | ❌ 65% | ❌ 10% |
| layout-design-001 | ✅ 85% | ❌ 30% |
| connection-design-001 | ✅ 100% | ❌ 85% |
| mating-design-001 | ✅ 85% | ✅ 85% |
| comprehensive-001 | ✅ 100% | ❌ 30% |
| **Pass@1** | **4/5 = 80%** | **1/5 = 20%** |

### 关键发现

1. **Kimi 在这个工具链下明显强于 DeepSeek-v4-pro**：Kimi 4/5 通过，DeepSeek 仅 mating-design 通过。
2. **`instance-declare-001` 是两个 Actor 共同的陷阱题**：
   - Kimi 生成了 6 个 instance YAML，但**没有写 `layouts/layout.yaml`**，导致 `TELECOM-COLLISION-001` 报所有设备空间冲突（无 layout 时设备默认落回原点）。
   - DeepSeek 生成的 instance 字段不完整（缺 `pdu_id`、`rack_id`、`capacity_w`），直接触发 piki 内部 `AttributeError`。
   - **启示**：在当前 rule set 下，"只声明实例"是不够的，必须同时给出 layout/mating 才能通过几何检查。这要么说明任务难度梯度设计有问题，要么需要在 prompt 里显式要求"即使 instance-declare 也要包含 layout"。
3. **DeepSeek 的退化模式**：
   - `layout-design-001` 只拿到 30%：没创建 RACK-A01 / PDU-A / PDU-B，导致大量 FK 错误。
   - `connection-design-001` 拿到 85%：piki L1–L4 全绿，但**缺少交付物 `port-map.csv`**（Agent 声明 done 但 generate 未产出或路径不对）。
   - `comprehensive-001` 拿到 30%：缺少 4 个 rack-mount mate 文件，且 PDU 缺少 `rack_id`。
4. **OpenAIActor 内部重复跑 `piki check` 且默认走 `auto` backend**：日志里不断出现 Docker 连接失败 warning，不影响评分但拖慢速度，后续应改为与 `run-repair` 一致的 `none` backend 或彻底移除内部检查。

### 对实验设计的启示

- **主实验可以锁定 Kimi 作为主力 Actor**，DeepSeek Pro 仅作交叉验证或成本敏感场景。
- **任务难度梯度需要调整**：`instance-declare-001` 不应卡在 L4 几何检查（除非明确要求写 layout），否则会和 `layout-design` 难度倒挂。
- **prompt 需要补强**：在 initial prompt 里明确告诉 Agent"任何涉及机柜内设备的任务都必须提供 `layouts/layout.yaml`，否则碰撞检查会失败"。
- **交付物生成是独立瓶颈**：`connection-design-001` 的 DeepSeek rollout 规则全绿但缺 `port-map`，说明 Agent 不清楚 `piki generate` 的交付物要求，需要在 prompt 里加入 deliverable checklist。

## Pilot 结果（2026-06-24）

已新增 `sd-hwe-bench run-repair` 并完成机械验证：

| 配置 | 结果 |
|---|---|
| `openai:deepseek-v4-flash --no-repair` | 30%：生成 6 个 YAML，但缺失 RACK/PDU 引用 |
| `openai:deepseek-v4-flash --max-repair 2` | 10%：repair 轮收到诊断后模型改坏了文件，出现 piki 内部异常 |
| `kimi` repair | Turn 0 超时/挂起，已停止 |

**关键观察**：
1. Repair loop 工具本身跑通了：评分 → 生成诊断 → 重新 prompt → 再评分 → 记录终止原因。
2. DeepSeek Flash 能力偏弱，不适合作为 FSE 论文主实验的主力模型；主实验改用 Kimi 与 DeepSeek Pro。
3. 当 Agent 输出导致 piki 内部异常时，诊断里会混入 traceback，已优化 repair prompt 只抽取 `rule_id`/`name`/`message`/`file`。
4. Docker 当前未运行，sandbox 自动 fallback 到 host piki；正式实验前需要启动 Docker 或使用 `--sandbox none` 并记录环境。

## 时间安排（从今天 2026-06-24 到 10-02，约 14 周）

| 阶段    | 时间        | 任务                                                |
| ------- | ----------- | --------------------------------------------------- |
| W1–W2   | 06/24–07/07 | 锁定 task/prompt/container，修复 harness 不稳定问题 |
| W3–W6   | 07/08–08/04 | 跑完主实验 50 rollout + ablation 30 rollout         |
| W7–W8   | 08/05–08/18 | 数据分析、失败模式归类、产出图表                    |
| W9–W10  | 08/19–09/01 | 更新论文 §6、§3.2.2、§8；整理 replication package   |
| W11–W12 | 09/02–09/15 | 内部审阅、改稿、latex 编译与格式检查                |
| W13–W14 | 09/16–10/02 | 缓冲、最终润色、投稿                                |

## 风险与备选

| 风险                 | 应对                                                                      |
| -------------------- | ------------------------------------------------------------------------- |
| 实验跑不通或结果太弱 | 降低为“可行性/错误分析”叙事，不夸大 pass rate；或改投 NIER/position track |
| Actor 调用不稳定     | 优先保证 Kimi 默认模型完整跑完；DeepSeek API 作为补充 |
| 篇幅超出 18+4        | 把详细任务定义和失败案例放附录，正文只保留关键表格和洞察                  |
| 投稿前做不完         | 启动“Plan B”：用当前版本改投 NIER 或先上 arXiv                            |

## 下一步

1. 启动 Docker 或在固定 `--sandbox none` 环境下跑 5 tasks × 2 actors × pass@1 的可行性测试。
2. 根据可行性测试结果，决定是否把实验规模放大到 pass@5。
3. 用选定模型跑 no-repair vs repair ablation（5 tasks × 3 passes）。
4. 汇总数据后更新论文 §6 与 §3.2.2。

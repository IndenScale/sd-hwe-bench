# SD-HWE-Bench Agent Instructions

本文件记录 SD-HWE-Bench 项目当前阶段的关键概念、目标与开发约定。

---

## 0. 北极星目标

> **完成 SD-HWE-Bench 的写作并发表。**

一切技术决策、任务优先级和资源投入都服务于这一最终目标，同时必须兼顾推进速度与技术债务。基础设施中的**核心 API、任务/评分器接口、Actor 抽象、容器运行环境等顶层特性必须保持稳定和完整**，确保论文实验可复现、结果可信；在此前提下，对论文主线没有直接增益的锦上添花工作（如 CI 自动化构建、额外的校验规则、 prematurely 的分布式调度等）可暂缓，避免过度工程。

---

### 0.1 WBS 与里程碑

| 里程碑 | 目标 | 完成标准 | 当前状态 |
|---|---|---|---|
| M0. 发表目标锁定 | 确定分篇发表策略、目标会议/期刊、截稿时间、两篇论文的核心贡献点 | ✅ 已确定分篇。论文 A（EaC 概念篇）目标：arXiv 预印本 → ICSE/ASE NIER track（首选）或 Automation in Construction / JCISE（备选）。论文 B（SD-HWE-Bench 实验篇）目标：M3 实验完成后投 ML 会（ICLR/NeurIPS benchmark track）。详细投稿策略见 papers/engineering-as-code/AGENTS.md | 已完成 |
| M1. POC 跑通 | 5 个 telecom 任务 × 3 个 CLI Actor × pass@5，流程闭环、结果可归档 | 任意 Actor 能端到端完成 5 个任务，评分器输出稳定，runs/ 归档可汇总 | 进行中 |
| M2. 任务集扩展与框架稳定 | 任务集从 5 个扩展到 30+，覆盖多种难度和 HWE 类型；任务/评分器接口冻结 | 30+ 任务通过测试，新增任务无需改代码即可接入，接口文档化 | 未开始 |
| M3. 基准实验与 Leaderboard | 在稳定容器/评分环境中跑完全量实验，产出可发表的 Leaderboard 和错误分析 | 全量实验 rerun 通过，主要模型分数、失败模式、样例分析就绪 | 未开始 |
| M4. 论文 A 定稿 | Engineering as Code 概念论文定稿（含 ADL、ESA、EPM/AssemblyHub、SD-HWE-Bench 定位） | 概念论文达到 arXiv/期刊投稿标准 | 初稿已完成，改进中（添加对比矩阵、聚焦贡献等） |
| M5. 论文 B 定稿 | SD-HWE-Bench 实验论文定稿（含方法、实验、分析、附录） | 实验论文达到投稿标准，实验可复现包就绪 | 未开始 |
| M6. 投稿与发表 | 按目标刊物流程投稿论文 A/B，处理审稿意见，最终接收/发表 | 两篇论文均完成投稿，至少一篇接收或达到发表条件 | 未开始 |

**发表策略**：采用**分篇发表**。论文 A（Engineering as Code 概念篇）已起草初稿，建立 ADL / ESA / EPM / AssemblyHub 的理论框架，并明确 SD-HWE-Bench 是 EaC 范式下的首个 RLVR 竞技场；论文 B（SD-HWE-Bench 实验篇）聚焦评测设计、实验结果和与现有 ACC / AEC-Bench 的范式对比。

**术语体系**：统一使用 **Engineering as Code（EaC）** 作为顶层范式；**ADL** 作为设计语言；**Part** 作为工程原子，对应 piki 的 Instance；**ACC（Automated Compliance Checking）** 指代现有事后合规检查路径；**ESA（Engineering Static Analysis）** 指代 EaC 主张的工程静态分析（将规则检查前移到设计生成阶段）。不再使用 X-CCA、X-DRC 等非标准术语。

**当前阶段（M1）的下一步**：完成 POC 流程闭环，同时推进论文 A/B 的迭代。然后立即转向 M2 的任务集扩展与框架稳定。M2 必须将核心 API 与任务/评分器接口冻结；而 CI/CD 自动化构建、DeliverableCritic 额外校验规则等增强类工作，在接口稳定前可暂缓，避免过早固化。

---

## 1. 当前阶段目标：POC 跑通

### 1.1 POC 范围

- **领域**：telecom（电信机柜部署）单领域。
- **任务**：5 个不同层级/类型的任务，覆盖从简单到复杂的工程设计能力：
  1. `telecom/instance-declare-001` — 实例声明
  2. `telecom/layout-design-001` — 布局设计
  3. `telecom/connection-design-001` — 连接设计
  4. `telecom/mating-design-001` — 配合设计
  5. `telecom/comprehensive-001` — 综合设计
- **Actor**：三种 CLI/API Agent 各跑 5 轮（pass@5）：
  - `kimi:kimi-code/k2.7`（Kimi Code CLI）
  - `gemini:gemini-3.1-pro`（Gemini CLI）
  - `codex:deepseek`（Codex CLI 调用 DeepSeek 后端）
- **成功标准**：
  - 每个 Actor 都能在 5 轮内完成每个任务的端到端流程（生成 YAML → piki check → piki generate → 评分）。
  - 评分器能正确输出 L0–L4 分层结果、交付物结果和 rubric 结果。
  - 运行结果能归档到 `runs/`，并能通过 `archive` / `leaderboard` 命令汇总。

### 1.2 非目标

- POC 阶段不追求高 Pass@1，只追求流程跑通、结果可复现、错误可诊断。
- 不扩展新领域（datacenter / mechanical / hvac / building）。
- 不实现自动化任务合成（任务仍为手工维护）。

---

## 2. 关键概念

### 2.1 任务（Task）

每个任务是一个自包含目录，结构如下：

```text
tasks/<domain>/<task-name>/
├── task.yaml          # 任务元数据、需求、评分层、rubrics
├── scaffold/          # Agent 可见的初始项目文件（只读）
│   ├── piki.toml
│   └── models/
├── solution/          # 参考方案（对 Agent 隐藏，用于验证和测试）
└── expected/          # 期望交付物（可选）
```

`task.yaml` 中必须明确定义：

- `task_id`：唯一标识，格式 `<domain>/<task-name>`
- `task_type`：`instance-declaration` | `layout-design` | `connection-design` | `mating-design` | `comprehensive` | `incremental`
- `difficulty`：`easy` | `medium` | `hard`
- `requirement`：自然语言需求
- `expected_files`：Agent 必须创建的 YAML 文件列表
- `scoring_layers`：本次任务启用的评分层（L0–L4）
- `expected_deliverables`：需要 `piki generate` 产出的交付物类型列表
- `rubrics`：可选的 LLM-as-Judge 评估维度

### 2.2 Actor

Actor 是执行设计任务的 Agent 驱动层。当前支持：

| Actor 规范 | 实现类 | 调用方式 | 说明 |
|---|---|---|---|
| `kimi[:model]` | `KimiActor` | `kimi -p <prompt>` | 直接修改工作目录 |
| `codex[:model]` | `CodexActor` | `codex exec ...` | 直接修改工作目录 |
| `gemini[:model]` | `GeminiActor` | `gemini --prompt ... --yolo` | 直接修改工作目录，需 git repo |
| `openai:MODEL` / `deepseek:MODEL` | `OpenAIActor` | OpenAI-compatible API | 解析 ````yaml` 代码块写入文件 |

POC 阶段重点验证前三者（Kimi / Gemini / Codex）的 CLI 模式。

### 2.3 Reviewer / Critic

Reviewer 由四层 Critic 组成，按顺序执行：

1. **SyntaxCritic（L0）**：YAML 合法性、项目非空、expected files 存在性。
2. **PikiCritic（L1–L4）**：调用 `piki check --format json`，将规则失败映射到：
   - L1：Schema 校验
   - L2：引用完整性
   - L3：业务规则（功率预算、U 位冲突、接口兼容等）
   - L4：几何检查（碰撞检测、深度越界等）
3. **DeliverableCritic（L5/L6）**：检查 `dist/` 下是否生成期望交付物。
4. **RubricCritic（LLM-as-Judge）**：按 task.yaml 中 rubrics 做定性评估（诊断性，不计入 overall_score）。

`score_task()` 是统一评分入口。

### 2.4 运行归档

每次 rollout 生成一个独立目录：

```text
runs/<timestamp>_<task-id>_<actor>_<model>/
├── manifest.json      # 运行元数据 + 评分结果
├── prompt.md          # 注入 Agent 的完整 prompt
├── trajectory.jsonl   # Actor 交互日志
└── workspace/         # Agent 实际输出的 piki 项目
```

归档是 POC 可复现性的核心。所有 POC 实验必须落盘到 `runs/`。

---

## 3. POC 阶段必须支持的能力

### 3.1 参数化启动

CLI `run` 命令必须支持通过参数控制实验配置，包括但不限于：

```bash
# 单任务单 Actor
sd-hwe-bench run telecom/comprehensive-001 --actor kimi:kimi-code/k2.7

# 多轮 pass@k
sd-hwe-bench run telecom/comprehensive-001 --actor kimi:kimi-code/k2.7 --passes 5

# 批量任务（前缀匹配）
sd-hwe-bench run telecom/ --actor gemini:gemini-3.1-pro --passes 5

# 指定沙箱后端（none / docker / podman）
sd-hwe-bench run telecom/comprehensive-001 --actor codex:deepseek --sandbox docker

# 启用 LLM rubrics
sd-hwe-bench run telecom/comprehensive-001 --actor kimi:kimi-code/k2.7 --rubrics --rubrics-model deepseek-chat

# 自定义运行目录
sd-hwe-bench run telecom/ --actor kimi:kimi-code/k2.7 --run-dir runs/poc-2026-06-20
```

参数化启动的目标：**同一份代码，通过不同参数组合跑完 POC 全部实验**。

### 3.2 Job 编排

Job 编排指“把多个（任务 × Actor × Pass）组合批量执行、归档、汇总”的能力。POC 阶段至少支持：

1. **批量任务发现**：`sd-hwe-bench list` 列出全部任务；`run <prefix>` 按前缀批量匹配。
2. **多轮独立执行**：`--passes N` 对同一任务跑 N 次独立 rollout，每次使用新的 `Workspace`。
3. **结果归档**：每次 rollout 生成独立目录，`manifest.json` 记录 task_id、actor、model、各层评分、交付物结果。
4. **结果汇总**：
   - `sd-hwe-bench archive` 列出所有 rollout。
   - `sd-hwe-bench leaderboard --update` 按 model 聚合 Pass@1 / Avg Score。
5. **可复现实验**：通过参数即可复跑相同实验，不依赖手工脚本或硬编码。

POC 阶段不强制要求分布式调度，但脚本化批量跑实验必须可行。

---

## 4. 容器策略（POC 阶段强制使用 Container）

### 4.1 决策

**POC 阶段所有评分和交付物生成必须在 container 中执行。**

本地 `none` 模式仅保留为快速调试和开发时的逃生通道，正式的 POC 实验、基线跑分和 leaderboard 数据都必须来自 container 环境。

### 4.2 理由

1. **可复现性**：消除本地 piki 版本、Python 环境、PATH 差异带来的噪音。
2. **Actor 间一致性**：Kimi / Gemini / Codex 三个 CLI Agent 各自独立修改工作目录，但 `piki check` / `piki generate` 统一由同一个 container image 执行，确保评分标准一致。
3. **CI/CD 就绪**：POC 验证通过的 image 和命令可直接用于 GitHub Actions，无需二次迁移。
4. **问题可诊断**：container 内环境固定，便于定位“是 Agent 输出错了”还是“本地引擎行为不同”。

### 4.3 技术路径

- 默认沙箱后端：`auto`，运行时会按 `docker` → `podman` → `none` 自动探测并回退。
- 镜像名：`sd-hwe-bench-piki:latest`。
- 构建上下文：piki 仓库根目录（monorepo 中为 `../piki`）。

```bash
# 从 monorepo 根目录构建 sandbox image
docker build -f sd-hwe-bench/Containerfile -t sd-hwe-bench-piki:latest piki/

# POC 实验示例（默认使用 auto，优先 container）
sd-hwe-bench run telecom/ --actor kimi:kimi-code/k2.7 --passes 5

# 显式指定 container 后端
sd-hwe-bench run telecom/ --actor gemini:gemini-3.1-pro --passes 5 --sandbox docker

# 仅当本机未安装 docker/podman 时，才回退到本地模式
sd-hwe-bench run telecom/comprehensive-001 --actor codex:deepseek --sandbox none
```

### 4.4 非目标

- POC 阶段不追求 container 启动速度；如果单次 `piki check` 起 container 较慢，可接受。
- 不强制要求 Kubernetes 或分布式容器调度；单节点 docker/podman 即可。

---

## 5. 开发约定

- 所有代码修改需保持 `tests/` 通过（当前 45/45 pass）。
- 新增任务必须包含完整的 `task.yaml`、`scaffold/`、`solution/`。
- 新增 Actor 必须继承 `Actor` 基类，实现 `run(prompt, workspace_root) -> ActorResult`。
- 新增 Critic 必须继承 `Critic` 基类，实现 `evaluate(workspace_root, task) -> CriticResult`。
- 不要同时维护两份 prompt 构建器：当前 `prompts.py` 与 `agents/prompt_builder.py` 内容重复，后续应统一。
- POC 实验数据统一归档到 `runs/`；分析脚本可放在 `scripts/` 或 `work/`。

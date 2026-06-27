# 6. 基线实验

本章报告 SD-HWE-Bench 的主实验结果。实验覆盖 46 个 telecom 任务（29 canonical + 5 POC + 5 复合 easy + 4 涌现约束 + 3 跨专业综合）（5 POC + 15 telecom-rack + 8 datacenter + 6 telecom-site）、3 个模型（Kimi k2.7、DeepSeek-v4-Flash、DeepSeek-v4-Pro）、2 种 Agent 框架（CLI native vs API proxy），在 pass@1 设置下完成全量评测。

## 6.1 实验设置

### 6.1.1 模型与 Actor

我们选取三组 Agent 配置作为 baseline：

| Actor 类型 | 模型 | 框架 | 说明 |
|-----------|------|------|------|
| CLI Native | Kimi k2.7 | kimi-code CLI | 直接文件系统操作，prompt 指引主动查阅规范文档 |
| CLI Native | DeepSeek-v4-Flash | Codex CLI (codex exec) | 同上，文件系统模式 |
| CLI Native | DeepSeek-v4-Pro | Codex CLI (codex exec) | 同上，文件系统模式 |
| API Proxy | DeepSeek-v4-Flash | OpenAI 兼容 API | YAML 代码块解析后写入，prompt 内联规范 |
| API Proxy | DeepSeek-v4-Pro | OpenAI 兼容 API | 同上 |

**CLI Native** Actor 通过 shell 命令行（kimi / codex exec）在工作目录中直接创建和修改 YAML 文件，workflow 指引 Agent 主动阅读 `docs/` 中的设计规范文档并执行 `piki check` 自检。**API Proxy** Actor 通过 OpenAI 兼容 API 调用模型，从响应中解析 YAML 代码块写入文件——该模式下设计规范被内联到 prompt 中（因 Agent 无法主动读取文件系统）。

所有实验使用各模型的默认温度和采样参数。

### 6.1.2 评测设置

- **上下文设置**：主实验使用 Full Context（完整 scaffold ADL 工程）。
- **Passes**：每个（任务 × Actor）组合独立执行 1 次（pass@1）。pass@5 待补跑。
- **DTS**：所有 piki check 在本地 Python 环境执行（`backend=none`），30 条规则覆盖 L0-L4 全部层次。
- **Repair**：主实验不启用 repair loop（no-repair）。Repair 效果的消融实验见 §7。
- **Rubrics**：LLM-as-Judge rubrics 作为可选诊断——rubrics 分数不计入 pass/fail。

### 6.1.3 指标

主实验报告以下指标：

- pass@1
- Avg Score（各层加权平均分）
- 各 DTS 层的独立通过率
- 平均墙钟时间（分钟）

## 6.2 主结果

@tbl:main-results 给出各模型在 SD-HWE-Bench 上的主结果。

| Actor + 模型 | 任务数 | pass@1 | Avg Score | L0 | L1 | L2a | L2b | L2c | L3 | L4 |
|-------------|--------|--------|-----------|----|----|----|----|----|----|----|
| CLI Kimi k2.7 | 20/20 | 100% | 89% | 100% | 100% | 100% | 100% | 100% | 100% |
| CLI DeepSeek-v4-Flash | 15/15 | 100% | 88% | 100% | 100% | 100% | 100% | 100% | 100% |
| CLI DeepSeek-v4-Pro | 15/15 | 100% | 88% | 100% | 100% | 100% | 100% | 100% | 100% |
| API DeepSeek-v4-Flash | 16/20 | 80% | 82% | 100% | 95% | 84% | 84% | 81% | 100% |
| API DeepSeek-v4-Pro | 18/20 | 90% | 84% | 95% | 86% | 86% | 81% | 100% | 100% |

Table: 主实验结果（Full Context, no-repair, pass@1）。CLI 数据来自 2026-06-27 实验（codex:deepseek-v4-* / kimi）；API 数据来自 2026-06-25 实验（deepseek:deepseek-v4-*，OpenAI 兼容 API 路径）。任务数差异系实验覆盖范围不同：CLI 路径覆盖新增的 datacenter 和 telecom-site 任务（15 个），API 路径覆盖原有 20 个任务（5 POC + 15 telecom-rack）。{#tbl:main-results}

### 6.2.1 关键发现：Actor Gap

实验结果揭示了一个显著的模式——**同一模型在不同 Actor 框架下的表现存在系统性差异**（我们称之为 Actor Gap）：

- DeepSeek-v4-Flash: CLI 100% vs API 80%（+20pp）
- DeepSeek-v4-Pro: CLI 100% vs API 90%（+10pp）

**根因分析**：

1. **文件系统交互能力**：CLI Actor 可以主动查阅 `docs/` 中的设计规范文档（如 rack-design-spec.md），在写作过程中实时参考正确的字段名、目录结构和约束规则；API Actor 依赖 prompt 中内联的规范文本，在长上下文生成中容易遗漏关键细节。

2. **自检循环（Self-Check）**：CLI Actor 的 workflow 指引其执行 `piki check` 验证产出——虽然当前 pass@1 实验中 self-check 平均轮次 < 0.5（说明自检未充分触发），但即使是单次生成，能通过 CLI 操作文件系统的 Agent 也比纯粹输出文本块的 Agent 更可能产出正确的文件结构。

3. **YAML 解析损耗**：API Actor 需要从模型响应中解析 YAML 代码块并写入文件——如果模型输出的 YAML 格式不规范（缩进错误、路径注释缺失），解析器可能丢失文件路径信息或生成错误文件。

**方法论意义**：Actor Gap 的存在说明 benchmark 的评测对象不仅仅是模型能力，也包含了 Agent 框架的工程质量。在设计 agentic benchmark 时，必须明确报告所使用的 Agent 框架及其与模型的交互方式，否则不同实验室的结果不可直接比较。

### 6.2.2 规则覆盖率

每个任务底层执行 30 条确定性规则（L1-L4），覆盖以下维度：

| 层次 | 规则数 | 典型规则 |
|------|--------|---------|
| L1 Schema | ~5 | YAML 语法、必填字段、类型校验 |
| L2a 标识/外键 | ~5 | 外键存在性（TELECOM-FK-001）、引用完整性（REFS-001/002）、标签唯一性（TAGS-001） |
| L2b 接口/端口 | ~7 | 端口所属设备（TELECOM-PORT-002）、连接端点（TELECOM-CONN-001）、接口兼容性（INTERFACE-COMPAT-001） |
| L2c 配合/目录 | ~4 | 配合类型匹配（MATE-001/002/003）、目录引用（CATALOG-001/002） |
| L3 工程约束 | ~5 | PDU 功率预算（TELECOM-POWER-001）、相线平衡（TELECOM-POWER-002）、线缆匹配（INTERFACE-CABLE-001） |
| L4 几何/空间 | ~4 | 3D 碰撞检测（TELECOM-COLLISION-001）、U 位冲突（TELECOM-RACK-001/002/003） |

Table: DTS 规则覆盖分布。总规则数 30 条，覆盖 L1+L2a+L2b+L2c+L3+L4 共 6 个评分层、9 个子类别。L2 拆分（v2）将原 16 条引用/接口/配合规则从单层 L2 拆为三个子层（L2a/L2b/L2c），避免单字段错误导致连锁扣分。{#tbl:rule-coverage}

## 6.3 难度分布与区分度

@tbl:difficulty-breakdown 按难度分解 pass@1。

| 难度 | 任务数 | Kimi CLI | DS-Flash CLI | DS-Pro CLI | DS-Flash API | DS-Pro API |
|------|--------|----------|-------------|-----------|-------------|-----------|
| easy | 18 | 100% | 100% | 100% | 94% | 94% |
| medium | 21 | 100% | 100% | 100% | 85% | 92% |
| hard | 7 | 100% | 100% | 100% | 25% | 50% |

Table: 按难度分解的 pass@1。API 路径在 hard 任务上区分度最大。{#tbl:difficulty-breakdown}

**分析**：

- **easy 任务（18 个）** 主要为 instance-declaration 类型——声明单个 Part 实例，生成 1-4 个 YAML 文件。即使 API 路径也仅有 1 个失败（字段名错误）。
- **medium 任务（21 个）** 涉及 mating-design / connection-design / layout-design——需要跨文件协调引用和配合关系。API Flash 85% vs CLI 100% 体现文件系统交互的差距。
- **hard 任务（7 个）** 为 comprehensive 综合设计——涉及跨机柜/跨系统的多专业协调。API Flash 仅 25%（1/4），API Pro 50%（2/4），是区分度最强的子集。

### 6.3.1 失败模式分布（API 路径）

@tbl:failure-dist 给出 API 路径在各 DTS 层的失败分布。

| Actor | L1 (Schema) | L2 (引用) | L3 (约束) | L4 (几何) |
|-------|------------|----------|----------|----------|
| API DS-Flash | 1 (5%) | 3 (15%) | 1 (5%) | 3 (15%) | 0 |
| API DS-Pro | 1 (5%) | 2 (10%) | 0 (0%) | 1 (10%) | 0 |

Table: API 路径失败按 DTS 层分布（20 tasks, pass@1）。CLI 路径无失败。{#tbl:failure-dist-api}

主要失败集中在 L2a（引用完整性——引用不存在的 Part ID、端口名缺失）和 L3（工程约束——PDU 功率超限、接口类型不匹配）。L2 拆分后，单字段错误不再连锁导致 L2b/L2c 同时失败，细化了失败信号。

## 6.4 逐任务详细结果

完整 34-task × 3-CLI-model 逐任务 leaderboard 见 leaderboard/results.md 和 leaderboard/results.json。

代表性任务：

- **telecom-rack-015**（跨机柜综合, hard）：三模型均 100% 通过，包含 18 个 expected_files 和 5 个 delivarbles，覆盖跨机柜光纤连接、SFP28 光模块配合、电源 IEC 配合等。
- **datacenter-008**（机房交付, hard）：包含 4 个 delivarbles（bom-csv / power-budget / port-map / cable-list），三模型均 100%。
- **comprehensive-001**（POC 综合, hard）：API Flash 100%、API Pro 36%。L2a（引用完整性, 5%）、L2b（接口兼容, 5%）、L3（工程约束, 40%）独立评分后，Pro 的 L2a+L2b+L3 三连失败清晰分离，不再聚合为单一 L2 扣分。

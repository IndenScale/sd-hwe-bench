# Canonical Project 设计规范指南

本指南说明如何为 SD-HWE-Bench 设计 canonical project，以便生成更贴近实际工程、具有模型区分度、且适合训练 Agent 查阅规范的数据集。

## 1. 设计目标

一个高质量的 canonical project 应当同时满足：

- **工程真实性**：任务描述像真实 issue，不会把所有技术细节讲清楚。
- **规范驱动性**：Agent 必须主动查阅项目中的设计规范，才能完成设计。
- **模型区分度**：不同能力的模型在规范理解、跨文件一致性、约束计算上表现差异明显。
- **可扩展性**：规范可按专业拆分，支持结构、电气、消防、防雷等多领域合规检查。

## 2. 目录结构

每个 canonical project 推荐采用如下结构：

```text
canonical/<domain>-<name>/
├── README.md                       # 项目说明与任务提取说明
├── task_manifest.yaml              # 任务序列与 requirement 定义
├── piki.toml                       # piki 项目配置
├── models/                         # 型号默认值
├── docs/                           # 项目设计规范（关键）
│   ├── index.md                    # 规范总览与索引
│   ├── disciplines/                # 各专业规范
│   │   ├── electrical.md
│   │   ├── structural.md
│   │   ├── fire-safety.md
│   │   └── lightning.md
│   └── thresholds.yaml             # 可解析的底线阈值
├── instances/                      # 实例声明（随 commit 演进）
├── layouts/                        # 布局
└── mates/                          # 配合约束
```

## 3. 规范文档编写原则

### 3.1 不要把技术细节写进 task description

`task_manifest.yaml` 中的 `requirement` 应当像真实工程 issue：

- 说明要做什么
- 说明功能/性能目标
- 不指定具体字段名、公式、阈值

**不好**：

```yaml
requirement: |
  声明 PDU-A，使用 capacity_w: 2000，rack_id: RACK-A01。
```

**更好**：

```yaml
requirement: |
  为机柜 RACK-A01 声明一路 PDU-A，额定容量 2000W。
```

字段名（`capacity_w`、`rack_id`）应当由 Agent 去规范文档中查找。

### 3.2 规范中应明确字段、公式与阈值

`docs/disciplines/` 中的各专业文档应包含：

- 本领域涉及的实体与字段名
- 计算公式
- 合规底线阈值
- 与其他专业的接口约定

示例（`docs/disciplines/electrical.md`）：

```markdown
## PDU 声明

PDU 实例必须包含：
- `rack_id`: 所属机柜 id
- `capacity_w`: 额定容量（W）

## 功率预算

机柜内设备总功耗不得超过 PDU 额定容量：

```
sum(device.tdp_w for device in rack) <= pdu.capacity_w * 0.8
```

底线阈值：负载率不得超过 80%。
```

### 3.3 多专业重复表述的处理

不同专业可能对同一指标有各自的底线。例如：

- 结构安全：机柜总承重 ≤ 额定承重
- 消防规范：单柜功率密度 ≤ 阈值
- 电气规范：PDU 负载率 ≤ 80%

规范文档应：

- 各专业分别说明自己的阈值
- `docs/thresholds.yaml` 汇总所有可解析阈值，供 Critic 自动检查

示例 `thresholds.yaml`：

```yaml
rack:
  max_load_ratio: 0.80        # 电气：PDU 最大负载率
  max_weight_kg: 800          # 结构：机柜最大承重
  max_power_density_w_per_u: 150  # 消防：每 U 功率密度
layout:
  min_u_gap_between_2u_devices: 1   # 布局：2U 设备间最小间隔
```

## 4. 让 Agent 主动查规范

### 4.1 PromptBuilder 引导

`PromptBuilder` 会自动在每个 task 的 prompt 中加入：

```markdown
## 项目设计规范

在执行设计任务前，请先查阅本项目的设计规范 `docs/` 目录。
所有设计决策应以规范为依据。未依据规范完成设计会被视为 Poor Practice。
```

对于 API 模式 Actor（DeepSeek/OpenAI），规范内容会内联到 prompt 中；
对于 CLI 模式 Actor（Kimi/Codex/Gemini），规范文件会保留在 workspace 中供其主动阅读。

### 4.2 评分时检查规范引用（可选）

未来可新增 `ComplianceCritic`：

- 读取 `docs/thresholds.yaml`
- 解析 Agent 输出的 YAML
- 自动计算并检查各专业底线
- 对未满足底线的设计给出具体违规项

## 5. 设计有区分度的任务

### 5.1 难度分层

| 层级 | 特点 | 示例 |
|---|---|---|
| Easy | 单文件、无跨引用、规范明确 | 声明一个机柜 |
| Medium | 多文件、需要查规范、有简单约束 | 声明 PDU 并正确挂载 |
| Hard | 跨专业约束、需要计算、多方案权衡 | 综合设计：满足功率/空间/成本约束 |

### 5.2 常见模型失败模式（可针对性设计）

- **字段名错误**：规范用 `capacity_w`，模型猜成 `power_capacity_w`
- **跨文件引用错误**：设备引用了不存在的 PDU 或机柜
- **单位混淆**：mm vs cm，W vs kW
- **约束计算错误**：未考虑 2U 设备占用连续 2U
- **忽略专业底线**：只满足功能，不满足消防/结构/电气阈值

### 5.3 设计能暴露模型短板的任务

- **隐式约束**：任务描述不直接说，但规范中明确。例如规范要求 PDU 必须声明 `rack_id`。
- **多专业冲突**：一个设计同时受电气和结构约束，模型需要在两者之间权衡。
- **反事实案例**：提供看似合理的默认值，但规范要求不同。例如 scaffold 中某模型用 `power_capacity_w`，但规范要求 `capacity_w`。

## 6. 示例：telecom-rack 规范演进

当前 `canonical/telecom-rack/docs/rack-design-spec.md` 已包含：

- U 位编号与占用规则
- PDU 字段规范
- 设备声明规范
- 设计流程

未来可扩展为：

```text
canonical/telecom-rack/docs/
├── index.md
├── disciplines/
│   ├── electrical.md      # 功率、PDU、接口
│   ├── structural.md      # 机柜承重、设备安装
│   ├── thermal.md         # 散热、功率密度
│   └── cabling.md         # 光纤、电缆规范
└── thresholds.yaml
```

## 7.  checklist

新建 canonical project 时，请确认：

- [ ] `task_manifest.yaml` 中的 requirement 只描述工程目标，不暴露字段名/公式/阈值
- [ ] `docs/` 目录包含完整的设计规范
- [ ] 规范中明确了 Agent 需要使用的字段名、目录结构和约束规则
- [ ] 如有多个专业，拆分为 `docs/disciplines/*.md`
- [ ] 如有可解析阈值，提供 `docs/thresholds.yaml`
- [ ] 重新运行 `tools/extract_tasks.py --validate` 确保 solution 通过 `piki check`
- [ ] 运行 `pytest tests/test_reference_solutions.py` 确认所有 reference solution 通过

## 8. 与现有工具的集成

- `tools/extract_tasks.py` 会自动把 `canonical/<project>/docs/` 复制到每个 task 的 `scaffold/` 和 `solution/`。
- `PromptBuilder` 会自动检测 `docs/rack-design-spec.md`（或 `docs/index.md`）并引导 Agent 查阅。
- 未来 `ComplianceCritic` 可读取 `docs/thresholds.yaml` 执行自动合规检查。

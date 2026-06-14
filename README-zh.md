# SD-HWE-Bench（软件定义硬件工程评测基准）

> **AI 能否像工程师一样，将模糊需求转化为正确、合规、可交付的设计声明？**
>
> SD-HWE-Bench 让这个问题变得可测量、可竞争、可复现。

---

## 这是什么？

SD-HWE-Bench 评测 AI 智能体在**声明式工程设计任务**上的能力。给定一段自然语言工程需求，智能体必须生成结构化的设计声明（YAML），使其通过自动规则校验，并产出有效的工程交付物。

它是硬件工程领域的 [SWE-Bench](https://www.swebench.com/)——一个标准化的、开放的、可自动评分的评测基准，驱动 AI 能力的跨越式提升。

### 任务范式

```
输入：自然语言工程需求
输出：结构化设计声明（piki YAML）
评分：L0-L4 规则检查通过率 + 交付物生成质量（Pass@k）
```

### 为什么硬件工程需要自己的 SWE-Bench？

软件工程的 RLVR（基于可验证奖励的强化学习）之所以奏效，是因为代码有编译器、linter 和测试套件——快、确定、可解释的验证器。硬件工程的约束比代码更丰富、更"硬"（物理定律不讲情面），但缺少让 AI 能消费这些约束的基础设施。

| HWE 现存的缺口 | SD-HWE-Bench 如何补齐 |
|---|---|
| 设计上下文散落在邮件、IM、人脑里 | 自包含的任务定义，含全部所需上下文 |
| CAD/BIM 数据 LLM 无法直接操作 | 文本原生的 YAML 声明，Agent 可读写、可 diff |
| 验证需要数小时（FEA/CFD） | 毫秒到秒级的规则引擎检查（L0-L4） |
| 没有结构化的任务定义 | 清晰的输入、输出结构和自动化评分规则 |

---

## 如何工作

```
┌──────────────┐
│ 自然语言需求   │  "为一个 42U 机柜设计计算节点部署方案……"
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  AI 智能体    │  生成 piki YAML 声明：
│              │  instances/、layouts/、mates/、connections/
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  piki check  │  L0：文件格式合法性
│  （规则引擎）  │  L1：Schema 校验
│              │  L2：引用完整性
│              │  L3：业务规则（功率预算、U 位冲突）
│              │  L4：几何检查（碰撞检测）
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  评分         │  Pass@k：所有规则通过？
│              │  部分得分：各层分别评分
│              │  交付物质量：BOM、端口表、机柜面板图？
└──────────────┘
```

---

## 任务分类

| 类别 | 说明 | 示例 |
|---|---|---|
| **实例声明** | 选择正确的 Family/Model，声明实例及属性 | 声明 8 台服务器，含正确 TDP、接口 |
| **布局设计** | 将实例放置到正确的物理位置 | 机柜 U 位分配，无冲突 |
| **连接设计** | 创建端口间连接，接口兼容 | 服务器 eth0 → 交换机 Gi1/0/1（SFP28） |
| **配合设计** | 定义物理耦合约束 | rack-mount、power-iec、lc-connector |
| **综合设计** | 端到端：实例 + 布局 + 连接 + 配合 | 从零设计完整机架部署 |
| **增量修改** | 修改已有设计以满足新需求 | 新增 2 台服务器，不破坏已有约束 |

---

## 评分体系

SD-HWE-Bench 使用与 piki 的 L0-L6 分层检查对齐的分层评分：

| 层级 | 检查内容 | 权重 |
|---|---|---|
| L0 | 文件格式合法性 | 门槛（必须通过） |
| L1 | Schema 校验 | 10% |
| L2 | 引用完整性 | 15% |
| L3 | 业务规则 | 40% |
| L4 | 几何检查 | 20% |
| 交付物 | 生成器输出有效性 | 15% |

**Pass@k**：k 次尝试中最优一次通过全部 L0-L4 检查的任务比例。

---

## 快速开始

### 前置条件

- Python >= 3.11
- [piki](https://github.com/indenscale/piki) >= 0.1.0（提供规则引擎）

### 安装

```bash
git clone https://github.com/indenscale/sd-hwe-bench.git
cd sd-hwe-bench
pip install -e ".[dev]"
```

### 运行任务

```bash
# 列出可用任务
sd-hwe-bench list --dataset .

# 运行单个任务（需要 task 路径下有 piki 项目）
sd-hwe-bench run telecom/rack-deploy-001 --dataset .

# 运行全部评测
sd-hwe-bench run --dataset . --dataset telecom
```

### 任务目录结构

```
tasks/telecom/rack-deploy-001/
├── task.yaml          # 任务元数据和需求
├── scaffold/          # 给 Agent 的起始文件（模型库、已有实例）
│   ├── piki.toml
│   ├── models/
│   └── instances/
├── solution/          # 参考答案（评测时对 Agent 隐藏）
│   ├── instances/
│   ├── layouts/
│   └── mates/
└── expected/          # 评分用的期望交付物
    └── bom.csv
```

---

## 覆盖领域

| 领域 | 状态 | 任务数 |
|---|---|---|
| **电信/数据中心** | Alpha | 5 |
| **暖通/流体** | 规划中 | — |
| **机械（消费电子）** | 规划中 | — |
| **电气** | 规划中 | — |

---

## 与 piki 的关系

SD-HWE-Bench 是独立的社区倡议。它使用 [piki](https://github.com/indenscale/piki) 作为默认的声明式建模语言和规则引擎，但 benchmark 的任务定义、评分方法和治理是独立的。

- piki 提供：YAML DSL、规则引擎（L0-L4 检查）、生成器管线
- SD-HWE-Bench 提供：任务数据集、评分框架、排行榜、社区治理

---

## 参与贡献

详见 [CONTRIBUTING-zh.md](CONTRIBUTING-zh.md)。欢迎：

- **任务提案**：新的工程设计场景，含需求和参考方案
- **领域插件**：新的工程领域（暖通、结构、电气）
- **评分改进**：更好的部分得分机制、交付物质量指标
- **排行榜提交**：跑你的 Agent 并提交结果

---

## 治理

SD-HWE-Bench 由社区治理。初期由 piki 核心团队维护，任务数超过 200 后迁移到技术委员会 + 领域维护者模式。

---

## 许可证

MIT — 详见 [LICENSE](LICENSE)。

---

## 引用

```bibtex
@misc{sd-hwe-bench,
  title = {SD-HWE-Bench: A Benchmark for Software-Defined Hardware Engineering},
  author = {SD-HWE-Bench Contributors},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/indenscale/sd-hwe-bench}
}
```

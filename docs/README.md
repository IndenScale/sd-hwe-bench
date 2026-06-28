# SD-HWE-Bench 文档索引

> 本目录存放 SD-HWE-Bench 项目的设计规范、评估方法论、架构决策记录与已知问题。

---

## 目录结构

```text
docs/
├── README.md                          # 本文档：索引与导航
├── conventions/                       # 工程规范与约定
│   └── adl-piki-convention.md         # ADL & Piki 工程约定参考
├── guides/                            # 设计与贡献指南
│   └── canonical-project-design.md    # Canonical Project 设计规范指南
├── evaluation/                        # 评估方法论与评分规则
│   ├── methodology.md                 # SD-HWE-Bench 评估方法论
│   └── scoring.md                     # SD-HWE-Bench 评分规则
├── adr/                               # 架构决策记录 (Architecture Decision Records)
└── issues/                            # 已知问题与限制
```

---

## 快速导航

### 如果你是 Agent / 参赛者

先阅读：

- [`conventions/adl-piki-convention.md`](conventions/adl-piki-convention.md) — 所有实体类型、目录约定、字段定义和跨文件引用规则。
- [`evaluation/scoring.md`](evaluation/scoring.md) — 评分层、权重、Pass/Fail 判定规则。

### 如果你是数据集 / 规范贡献者

先阅读：

- [`guides/canonical-project-design.md`](guides/canonical-project-design.md) — 如何设计高质量的 canonical project。
- [`evaluation/methodology.md`](evaluation/methodology.md) — 任务组织、实验协议与基线说明。

### 如果你想了解项目演进

- [`adr/`](adr/) — 关键架构决策记录。
- [`issues/`](issues/) — 当前已识别的局限与待解决问题。

---

## 文档命名约定

- 目录使用小写、单数形式：`guide/` 保持为 `guides/`（与 `adr/`、`issues/` 一致）。
- 文件名使用小写、连字符分隔：`methodology.md`、`canonical-project-design.md`。
- 不再使用全大写文件名（旧 `METHODOLOGY.md`、`SCORING.md` 已迁移）。

# 参与贡献 SD-HWE-Bench

## 任务贡献流程

1. **提案**：使用下方模板提交 Task Proposal Issue。
2. **审核**：领域维护者审核需求的技术正确性。
3. **实现**：创建任务目录，含 scaffold、solution 和期望输出。
4. **验证**：确保 `sd-hwe-bench run` 在参考方案上产生一致的评分。
5. **提交**：发起 PR。技术委员会审核评分可复现性。
6. **合并**：任务加入数据集，纳入下一版本发布。

## 任务提案模板

```markdown
### 领域
[telecom / datacenter / mechanical / hvac / 其他]

### 任务类型
[instance-declaration / layout-design / connection-design / mating-design / comprehensive / incremental]

### 自然语言需求
[Agent 将看到的需求——清晰、自包含、含全部上下文]

### 期望输出结构
- instances/：[应声明哪些实例]
- layouts/：[应定义哪些布局]
- mates/：[应定义哪些配合]
- connections/：[应定义哪些连接]

### 适用规则
- 适用的 L0-L4 规则
- 期望的生成器交付物
- 部分得分的考量
```

## 任务目录结构

```text
tasks/{领域}/{任务id}/
├── task.yaml              # 任务元数据 + 需求
├── scaffold/              # 给 Agent 的起始文件
│   ├── piki.toml
│   ├── models/            # 可用型号库
│   └── instances/         # 已有实例（增量任务用）
├── solution/              # 参考答案（不给 Agent）
│   ├── instances/
│   ├── layouts/
│   ├── mates/
│   └── connections/
└── expected/              # 期望的生成器输出
    └── bom.csv
```

## 领域插件

新增工程领域时：

1. 创建 piki 插件，含 Family/Model 定义和规则
2. 贡献至少 10 个该领域的 benchmark 任务
3. 申请成为领域维护者

## 代码规范

- Python 3.11+，遵循 ruff 规则
- 任务 YAML 必须为合法的 piki 格式
- 所有任务必须包含完整的 `task.yaml` 元数据

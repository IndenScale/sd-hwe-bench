# 附录 B：Prompt 模板

## B.1 Agent 初始 Prompt 结构

主实验中使用的 prompt 由三个组件构成：

1. **系统提示**：将 Agent 角色定义为「电信硬件工程设计助手」，指定工作目录和 piki 工具链。
2. **piki 快速参考**：约 200 行嵌入式 ADL 语法和目录约定文档。
3. **任务需求**：`task.yaml` 中的 `requirement` 字段。

## B.1.1 piki 快速参考（摘录）

完整的 piki 快速参考嵌入在 `src/sd_hwe_bench/prompts.py` 中，包含：

- 目录约定（`instances/devices/`、`instances/ports/`、`layouts/` 等）
- 字段名陷阱警告（`capacity_w` vs `power_capacity_w`，PDU 必须有 `rack_id`）
- 每种 Instance 类型的 YAML 模板（device、port、transceiver、fiber、port connection、layout、mate）
- piki 命令参考（`piki check`、`piki generate`）
- 设计规范文档指针（提醒 Agent 阅读 `docs/`）

参考代码：约 860 行（`src/sd_hwe_bench/prompts.py`）。

## B.2 Repair Prompt 结构

Repair 循环 prompt 在初始 prompt 基础上追加：

1. **上一轮 DTS 错误**：按 L0–L5 层分类，每层最多 10 条错误。
2. **修复指令**：「根据以上 piki check 错误修复工程文件。仅修改有错误的文件，不要重写整个工程。」
3. **终止条件**：Agent 通过写入标记文件声明终止——`.done`（修复完成）、`.give_up`（放弃）、`.info_gap`（信息不足）、`.no_solution`（无解）。

## B.3 Prompt 演进历史

| 版本 | 变更 | 原因 |
|------|------|------|
| v1 | 初始 prompt | POC 阶段 |
| v2 | 新增 `capacity_w` vs `power_capacity_w` 警告 | API Actor 在此字段频繁失败 |
| v3 | 新增 `rack_id` 必填提示、piki check 自检指令 | L2 外键错误率高 |

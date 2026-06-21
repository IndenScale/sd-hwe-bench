<!-- markdownlint-disable MD041 -->
<!--
# 07 Piki Check Output
位置：附录 III-G — piki check 输出示例
字数：约 320 词
目标：附录
-->

# `piki check` 输出示例

本附录展示截至 2026-06-20，`piki check` 在 `samples/01-telecom-expansion` 上的输出。该命令执行 ADL 加载期校验（L0–L1）与 ESA 规则检查（L2–L4a），在笔记本电脑上约 170–200 毫秒完成，返回退出码 0，因为唯一失败级别的诊断是一个警告。

## 人类可读摘要

```text
[PASS] INTERFACE-COMPAT-001: 接口类型兼容性检查
[PASS] INTERFACE-CABLE-001: 线缆类型与接口匹配检查
[PASS] TELECOM-POWER-001: PDU 功率预算检查
[PASS] TELECOM-RACK-001: U 位冲突检查
[PASS] TELECOM-RACK-002: 机柜容量检查
[PASS] TELECOM-COLLISION-001: 机柜内设备 3D 碰撞检测
[PASS] TELECOM-CONN-002: 连接端口类型兼容性检查
[PASS] TELECOM-CONN-003: 连接线缆类型匹配检查
[PASS] TELECOM-WEIGHT-001: 机柜承重检查
[FAIL] TELECOM-FLOOR-002: 机柜维护通道宽度检查
       机柜 RACK-A01 与 RACK-A02 同排间距 -600.0mm 小于要求 600.0mm
...
============================================================
总计: 0 错误, 1 警告, 29 通过
============================================================
```

## JSON 摘要（`piki check --format json`）

```json
{
  "passed": true,
  "error_count": 0,
  "warning_count": 1,
  "pass_count": 29,
  "results": [
    {
      "rule_id": "TELECOM-FLOOR-002",
      "name": "机柜维护通道宽度检查",
      "passed": false,
      "message": "机柜 RACK-A01 与 RACK-A02 同排间距 -600.0mm 小于要求 600.0mm",
      "file": "",
      "severity": "WARNING"
    }
  ]
}
```

## 诊断结构的下游消费

相同的诊断结构由 `adl/src/adl/validation/validator.py` 产生的 LSP 兼容 `Diagnostic` 对象，以及 `src/piki/core/engine/checker.py` 中的 `RuleResult.to_diagnostic()` 方法输出。这意味着单一实现可以服务：

- 终端用户（人类可读摘要）；
- CI 仪表板（JUnit XML 或 JSON）；
- IDE 覆盖层（LSP 诊断）；
- PR 审查机器人（GitHub Checks API）。

该警告将问题定位到两个具体对象（`RACK-A01`、`RACK-A02`）、一个具体测量值（`-600.0mm`）和一个被违反的阈值（`600.0mm`）。在完整的 IDE 集成中，该诊断将被固定到 `layouts/layout.yaml` 中声明两个机柜位置的行上，实现与代码 lint 类似的编辑时反馈。

这一输出形态体现了 ESA 的设计目标：具体、快速、可定位、可被自动化工具消费。

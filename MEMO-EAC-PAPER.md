# EaC 论文投稿推进备忘录

> 最后更新：2026-06-21 CST
> 目标：FSE 2026 投稿截止 2026-10-02

## 当前评估状态

| 样本 | 初始状态 | 当前状态 |
|------|---------|---------|
| 01-telecom-expansion | ✅ 0 errors, 1 warning | ✅ 0 errors, 1 warning |
| 02-modular-datacenter | ❌ 12 errors | ✅ 0 errors, 13 pass |
| 03-mechanical-keyboard | ❌ 4 errors | ✅ 0 errors, 27 pass |

三个样本全部通过 L2–L4a 检查。

---

## 已修复的 Bug（共 3 项）

### 1. LAYOUT-001 空字符串判空缺陷

- **文件**：`adl/src/adl/models/layout.py`
- **修复**：`if v is not None` → `if v is not None and v != ""`
- **影响**：修复 sample 02 (×11) + sample 03 (×4) 共 15 个 error

### 2. Lowering pass 缺失 transform 字段解析

- **文件**：`adl/src/adl/compiler/passes/lowering.py`
- **修复**：提取 `fields["transform"]` 解析为 `Transform` 对象传入 `LayoutEntryHIR`，新增 `_unwrap_hir()` 辅助函数
- **影响**：修复相对坐标链完全失效（sample 02 中 4 台 GPU 虚假碰撞）

### 3. DC-COLLISION-001：方舱 cooler 位置导致虚假碰撞

- **文件**：`samples/02-modular-datacenter/layouts/layout.yaml`
- **修复**：cooler Y→1000（坐地），X→10000（独立区域）
- **影响**：sample 02 最后一个碰撞消除

---

## 违规注入实验 ✅

在 `samples/v--violation-injection`（sample 01 副本）注入 15 个违规，覆盖 4 个类别。

**检出结果**：`piki check` → 11 错误 + 5 警告 = 16 违规信号

- **ESA 检出率**：15/15（100%）
- **假阳性**：0
- **检查延迟**：<100ms（热缓存）

### 违规 → 检出映射

| 类别 | 数量 | 检出规则 |
|------|-----|---------|
| L2 接口不匹配 | 4 | TELECOM-CONN-002, TELECOM-CONN-003, TELECOM-CONN-001 |
| L2 引用完整性 | 3 | TELECOM-FK-001, TELECOM-CONN-001, MATE-003 |
| L3 功率预算 | 4 | TELECOM-POWER-001, TELECOM-FK-001, TELECOM-POWER-002 |
| L3/L4a 空间冲突 | 4 | TELECOM-RACK-001, TELECOM-RACK-002, TELECOM-RACK-003, TELECOM-COLLISION-001, TELECOM-FLOOR-001, TELECOM-FLOOR-002, MATE-003 |

---

## 论文中标注「进行中」的剩余项

| 项目 | 状态 | 说明 |
|------|------|------|
| 样本通过 | ✅ 全部完成 | 三个样本零错误 |
| 违规注入实验 | ✅ 完成 | 15/15 全部检出，零假阳性 |
| ACC 基线对比 | 🔄 待搭建 | IFC 导出 + ACC 工具 |
| SD-HWE-Bench | 🔄 设计完成 | 任务套件编写中 |

---

## 开发环境

```bash
cd ~/workspace/piki
uv sync
uv run python -m piki check samples/<sample-name>
uv run pytest tests/ -x -q
```

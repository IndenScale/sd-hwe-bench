"""Prompt building for Actor rollout."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from sd_hwe_bench.settings import settings

_PIKI_QUICKREF = """\
## Piki 快速参考

piki 是声明式系统建模框架。工程师用 YAML 声明设计意图，`piki check` 自动校验，`piki generate` 生成交付物。

### 目录约定（务必遵守）
- `instances/devices/` — 设备实例（**不能放在 `instances/` 根目录**）
- `instances/ports/` — 端口实例（独立文件）
- `instances/transceivers/` — 光模块实例
- `instances/fibers/` — 光纤实例
- `instances/port_connections/` — 端口连接实例
- `instances/pdus/` — PDU 实例
- `instances/racks/` — 机柜实例
- `layouts/` — 布局文件（`layouts/layout.yaml`）
- `mates/` — 配合文件（位于 workspace 根目录）
- `models/` — 型号默认值（已在 scaffold 中提供，**不要修改**）
- `piki.toml` — 项目配置（已在 scaffold 中提供，**不要修改**）
- `dist/` — `piki generate` 输出的交付物目录

如果 scaffold 中的设备文件被错误地放在 `instances/` 根目录，请将它们移动到 `instances/devices/`。

### 设备 Instance（`instances/devices/*.yaml`）
```yaml
id: SRV-01
family: ServerFamily
model: generic-server
name: "服务器-01"
status: installed
interfaces:
  - id: eth0
    interface_type: SFP28
    direction: bidirectional
```

### ⚠️ 关键字段名陷阱（务必遵守）

1. **PDU 用 `capacity_w`，不是 `power_capacity_w`**：
   scaffold 中的 `instances/racks/RACK-A01.yaml` 可能包含 `power_capacity_w` 字段，
   但 **PDU 实例必须使用 `capacity_w`**。写成 `power_capacity_w` 会导致 SCHEMA 校验失败。

2. **PDU 必须有 `rack_id`**：
   每个 PDU 实例必须声明 `rack_id` 字段指向所属机柜。缺少 `rack_id` 会导致外键引用错误
   （`TELECOM-FK-001`）。

3. **Layout 中的 PDU 也需要 `rack_id`**：
   `layouts/layout.yaml` 中每个 PDU 条目同样需要 `rack_id` 字段。

### 端口 Instance（`instances/ports/*.yaml`）
```yaml
id: SRV-01-eth0
family: PortFamily
device_id: SRV-01
port_name: eth0
port_type: SFP28
status: installed
```

### 光模块 Instance（`instances/transceivers/*.yaml`）
```yaml
id: SFP28-SR-S01-ETH0
family: TransceiverFamily
model: sfp28-sr-25g
status: installed
```

### 光纤 Instance（`instances/fibers/*.yaml`）
```yaml
id: FIBER-S01-SW01
family: FiberPatchCordFamily
from_port: SRV-01/eth0
to_port: SW-01/Gi1/0/1
fiber_type: OM4-LC-LC
length_m: 2.0
status: installed
```

### 端口连接 Instance（`instances/port_connections/*.yaml`）
```yaml
id: CONN-S01-SW01
family: PortConnectionFamily
from_port: SRV-01/eth0
to_port: SW-01/Gi1/0/1
cable_type: OM4-LC-LC
length_m: 2.0
status: installed
```

### Layout（`layouts/layout.yaml`）
字段名必须是 `rack_id`、`position_u`、`pdu_id`：
```yaml
- instance: SRV-01
  rack_id: RACK-A01
  position_u: 10
  pdu_id: PDU-A
- instance: SW-01
  rack_id: RACK-A01
  position_u: 20
  pdu_id: PDU-B
```

**重要**：只要任务里出现机柜（rack）和设备/PDU，就必须为每个设备实例和每个 PDU 都创建一条 layout 记录。
没有 layout 时，所有设备会被认为挤在原点，导致 `TELECOM-COLLISION-001` 空间冲突检查失败。

### Mate（`mates/<mate-type>/*.yaml`）
统一使用 `type`、`parent`、`child`：

机柜安装：
```yaml
type: rack-mount-19inch
parent: RACK-A01
child: SRV-01
at:
  u_start: 10
  u_span: 2
constrains:
  - field: depth_mm
    operator: "<="
    value_ref: depth_mm
    message: "SRV-01 深度超过 RACK-A01 机柜深度，无法安装"
```

电源 IEC 配合：
```yaml
type: power-iec-c14-c13
parent: PDU-A/outlet-1
child: SRV-01/power-a
```

SFP28 笼式配合：
```yaml
type: sfp28-cage
parent: SRV-01/eth0
child: SFP28-SR-S01-ETH0/host
```

LC 光纤头配合：
```yaml
type: lc-connector
parent: SFP28-SR-S01-ETH0/line
child: FIBER-S01-SW01/end-a
```

### 推荐工作流
1. 阅读 scaffold 中的 `piki.toml` 和 `models/`，确认已有实例。
2. 按正确目录结构创建/补充 YAML 文件。
3. 运行 `piki check`。
4. 如果有错误，根据报错修复 YAML 或调整文件位置。
5. 运行 `piki generate` 生成交付物到 `dist/`。
6. 再次运行 `piki check` 确认最终无错误。

### 提交前检查清单（每次创建 `.sdhwe.done` 前必读）
- [ ] 所有要求的 instance YAML 已创建，且放在正确的子目录（`instances/devices/`、`instances/ports/`、`instances/pdus/`、`instances/racks/` 等），不在 `instances/` 根目录。
- [ ] 如果任务涉及机柜和设备/PDU，`layouts/layout.yaml` 已包含每条设备/PDU 的 `rack_id`、`position_u`、`pdu_id`。
- [ ] 所有 `mates/` 文件已创建（rack-mount、power、fiber、transceiver 等）。
- [ ] 已运行 `piki check` 且 0 错误。
- [ ] 如果任务要求交付物，已运行 `piki generate`，且 `dist/` 下出现对应的 `.csv` / `.svg` 文件。
"""


_ADL_PIKI_CONVENTION = """\
# ADL & Piki 工程约定参考 (Convention Reference)

> 本文档是 SD-HWE-Bench 的正式规范参考，描述 piki 框架中所有实体类型、目录约定、字段定义和跨文件引用规则。Agent 必须在设计过程中严格遵守此文档。

---

## 1. 目录约定 (Directory Convention)

所有产出文件必须放在以下目录中。目录选择由实体类型决定，**放错目录会导致评分失败**。

### 1.1 实例目录 (`instances/`)

| 目录 | 实体类型 | Family | 说明 |
|------|---------|--------|------|
| `instances/devices/` | 服务器、交换机 | `ServerFamily` | 计算/网络设备实例 |
| `instances/racks/` | 机柜 | `RackFamily` | 标准机柜实例 |
| `instances/pdus/` | PDU | `PduFamily` | 电源分配单元实例 |
| `instances/ports/` | 端口 | `PortFamily` | 设备端口实例（独立文件） |
| `instances/transceivers/` | 光模块 | `TransceiverFamily` | SFP/SFP+ 等光模块实例 |
| `instances/fibers/` | 光纤/馈线 | `FiberFamily`, `FiberPatchCordFamily` | 物理线缆实例 |
| `instances/port_connections/` | 端口连接 | `PortConnectionFamily` | 逻辑端口连接实例 |
| `instances/antennas/` | 天线 | `FacilityFamily` | 基站天线实例 |
| `instances/cables/` | 线缆 | `FiberPatchCordFamily` | 馈线/跳线实例 |
| `instances/grounding/` | 接地/防雷 | `FacilityFamily` | 接地极、SPD 实例 |

### 1.2 顶层目录

| 目录 | 说明 |
|------|------|
| `rooms/` | 机房和机柜排定义（如 `DC-ROOM-01.yaml`, `ROW-A.yaml`） |
| `facilities/` | 基础设施设施实例（如 `COOLER-ROW-A.yaml`） |
| `layouts/` | 布局文件（**必须命名为 `layout.yaml`**） |
| `mates/` | 配合文件，按配合类型分目录 |
| `models/` | 型号定义（scaffold 提供，**不可修改**） |
| `docs/` | 设计规范文档（scaffold 提供，只读） |
| `spaces/` | 空间定义 |
| `dist/` | `piki generate` 输出目录（自动生成） |

### 1.3 Mate 子目录

| 目录 | Mate 类型 | 说明 |
|------|----------|------|
| `mates/rack-mount/` | `rack-mount-19inch` | 设备/PDU 安装到机柜 |
| `mates/rack-in-row/` | `rack-in-row` | 机柜部署到排 |
| `mates/power-iec/` | `power-iec-c14-c13` | PDU 输出口连接设备电源口 |
| `mates/sfp28-cage/` | `sfp28-cage` | 光模块插入设备端口 |
| `mates/lc-connector/` | `lc-connector` | 光纤接头连接光模块 |
| `mates/cable-connection/` | `cable-connection` | 线缆连接天线/设备 |
| `mates/cable-tray-over-row/` | `cable-tray-over-row` | 走线架盖排 |
| `mates/grounding/` | `grounding` (type TBD) | 接地连接 |
| `mates/must-clear/` | `must-clear` | 禁止空间干涉约束 |

---

## 2. 实体字段定义 (Entity Field Reference)

### 2.1 Model（型号定义，`models/` 下）

#### ServerFamily — 计算/网络设备型号
```yaml
model: generic-server       # 型号标识符
family: ServerFamily        # 家族
name: "服务器-01"            # 可读名称
height_u: 2                 # 设备高度 (U)
tdp_w: 500                  # 热设计功耗 (W)
psu_count: 2                # 电源模块数量
psu_redundancy: true        # 电源是否冗余
depth_mm: 750               # 深度 (mm)
width_mm: 445               # 宽度 (mm)
height_mm: 89               # 高度 (mm)
weight_kg: 22.0             # 重量 (kg)
```

#### RackFamily — 机柜型号
```yaml
model: standard-rack
family: RackFamily
total_u: 42                 # 总 U 位数
power_capacity_w: 10000     # 额定供电容量 (W)
depth_mm: 1000
width_mm: 600
weight_kg: 150.0
max_load_kg: 1000           # 最大承重 (kg)
cooling_capacity_w: 8000    # 制冷容量 (W)
maintenance_front_mm: 1200  # 前维护空间 (mm)
maintenance_rear_mm: 1000   # 后维护空间 (mm)
```

#### PduFamily — PDU 型号
```yaml
model: dc-pdu-3phase-32a
family: PduFamily
height_u: 0                 # PDU 通常不占 U 位
tdp_w: 0
psu_count: 0
psu_redundancy: false
depth_mm: 50
width_mm: 50
height_mm: 1800
weight_kg: 6.0
```

#### TransceiverFamily — 光模块型号
```yaml
model: sfp28-sr-25g
family: TransceiverFamily
form_factor: SFP28
speed_gbps: 25
reach: SR
wavelength_nm: 850
```

#### FacilityFamily — 基础设施型号
```yaml
model: in-row-cooler-30kw
family: FacilityFamily
facility_type: cooler       # 设施类型: cooler / antenna / ground-rod / spd
width_mm: 600
depth_mm: 1100
height_mm: 2000
weight_kg: 350.0
```

#### FiberPatchCordFamily — 线缆型号
```yaml
model: om4-lc-lc-3m
family: FiberPatchCordFamily
cable_type: OM4-LC-LC
length_m: 3.0
```

### 2.2 Instance（实例定义，`instances/` 下）

#### 设备实例 (`instances/devices/`)
```yaml
id: SRV-01                  # 唯一标识符（必填）
family: ServerFamily        # 家族（必填，或省略则从 model 推导）
model: generic-server       # 引用型号（必填）
name: "服务器-01"            # 可读名称
status: installed           # 状态
interfaces:                 # 接口列表
  - id: eth0
    interface_type: SFP28
    direction: bidirectional
  - id: power-a
    interface_type: IEC-C14
    direction: input
```

#### 机柜实例 (`instances/racks/`)
```yaml
id: RACK-A01
family: RackFamily
model: standard-rack
name: "主列头柜-A01"
location: 机房A-A列         # 物理位置（可选）
power_capacity_w: 2000      # 实际分配的供电容量
```

#### PDU 实例 (`instances/pdus/`) ⚠️ 关键陷阱！
```yaml
id: PDU-A
family: PduFamily
# ⚠️ 使用 capacity_w，不是 power_capacity_w！
capacity_w: 2000            # 额定输出容量 (W) — 必须用 capacity_w
rack_id: RACK-A01           # 所属机柜（必填）
name: "PDU-A（主路）"
interfaces:
  - id: outlet-1
    interface_type: IEC-C14
    direction: output
```

#### 端口实例 (`instances/ports/`)
```yaml
id: SRV-01-eth0             # 命名: {设备ID}-{端口名}
family: PortFamily
device_id: SRV-01           # 所属设备（必填）
port_name: eth0             # 端口名（必填）
port_type: SFP28            # 端口类型
status: installed
```

#### 光模块实例 (`instances/transceivers/`)
```yaml
id: SFP28-SR-S01-ETH0
family: TransceiverFamily
model: sfp28-sr-25g
name: "SFP28 SR 25G"
status: installed
```

#### 光纤实例 (`instances/fibers/`)
```yaml
id: FIBER-S01-SW01
family: FiberPatchCordFamily
model: om4-lc-lc-3m
name: "SRV-01 ↔ SW-01"
status: installed
# 注意：光纤不包含 from_port/to_port —— 由 port_connection 或 lc-connector mate 表达
```

#### 端口连接实例 (`instances/port_connections/`)
```yaml
id: CONN-S01-SW01
family: PortConnectionFamily
from_port: SRV-01/eth0      # 格式: {设备ID}/{端口名}
to_port: SW-01/Gi1/0/1
cable_type: OM4-LC-LC
length_m: 2.0
status: installed
```

#### 天线实例 (`instances/antennas/`)
```yaml
id: ANT-01
family: FacilityFamily
model: panel-antenna-4t4r
facility_type: antenna
name: "扇区1天线"
```

#### 接地/防雷实例 (`instances/grounding/`)
```yaml
id: GROUND-ROD-01
family: FacilityFamily
model: ground-rod-copper-2m
facility_type: ground-rod
name: "主接地极"
```

### 2.3 机房/排/设施 (`rooms/`, `facilities/`)

#### 排定义 (`rooms/ROW-A.yaml`)
```yaml
id: ROW-A
family: RackRowFamily
name: "A列机柜排"
rack_slots: 4              # 该排机柜位数
```

#### 设施 (`facilities/`)
```yaml
id: COOLER-ROW-A
family: FacilityFamily
model: in-row-cooler-30kw
facility_type: cooler
```

### 2.4 Mate（配合定义，`mates/` 下）

#### rack-mount-19inch — 设备安装到机柜
```yaml
type: rack-mount-19inch
parent: RACK-A01             # 机柜 ID
child: SRV-01                # 设备 ID
at:
  u_start: 10                # 起始 U 位
  u_span: 2                  # 占用 U 位数
constrains:                  # 物理约束检查
  - field: depth_mm
    operator: "<="
    value_ref: depth_mm
    message: "设备深度超过机柜深度"
```

#### rack-in-row — 机柜部署到排
```yaml
type: rack-in-row
part_a_id: ROW-A
part_b_id: RACK-A01
attributes:
  bay_index: 0               # 该排在排中的位置索引
```

#### power-iec-c14-c13 — PDU 供电
```yaml
type: power-iec-c14-c13
parent: PDU-A/outlet-1       # 格式: {PDU ID}/{接口ID}
child: SRV-01/power-a        # 格式: {设备ID}/{接口ID}
```

#### sfp28-cage — 光模块插入
```yaml
type: sfp28-cage
parent: SRV-01/eth0          # 格式: {设备ID}/{端口名}
child: SFP28-SR-S01-ETH0/host
```

#### lc-connector — 光纤接头
```yaml
type: lc-connector
parent: SFP28-SR-S01-ETH0/line
child: FIBER-S01-SW01/end-a
```

#### cable-connection — 线缆连接
```yaml
type: cable-connection
part_a_id: FEEDER-RRU01-ANT01
part_b_id: ANT-01
```

#### cable-tray-over-row — 走线架
```yaml
type: cable-tray-over-row
part_a_id: ROW-A
part_b_id: COOLER-ROW-A
```

#### must-clear — 禁止干涉
```yaml
type: must-clear
part_a_id: ANT-01
part_b_id: RRU-01
description: "天线与 RRU 不得碰撞"
```

---

## 3. 跨文件引用规则 (Cross-File Reference Rules)

### 3.1 ID 命名约定

- **设备 ID**：大写缩略词 + 编号，如 `SRV-01`、`SW-01`、`BBU-01`
- **端口 ID**：`{设备ID}-{端口名}`，如 `SRV-01-eth0`
- **光模块 ID**：`{型号缩写}-{设备ID缩写}-{端口名}`，如 `SFP28-SR-S01-ETH0`
- **机柜 ID**：`RACK-{位置}`，如 `RACK-A01`、`RACK-B03`
- **PDU ID**：`PDU-{机柜后缀}`，如 `PDU-A`、`PDU-B`

### 3.2 引用链

```
Room/Row → RACK → PDU/Device → Port → Transceiver → Fiber/Connection
```

- `rooms/ROW-A.yaml` 被 `mates/rack-in-row/` 引用
- `instances/racks/RACK-A01.yaml` 被 `instances/pdus/` 的 `rack_id` 引用
- `instances/devices/SRV-01.yaml` 被 `instances/ports/` 的 `device_id` 引用
- `instances/ports/SRV-01-eth0.yaml` 被 `mates/sfp28-cage/` 的 `parent` 引用
- `instances/transceivers/*.yaml` 被 `mates/sfp28-cage/` 的 `child` 引用

### 3.3 必须满足的引用完整性

1. 任何被引用的 ID 必须在其他文件中已声明（`FK-001`）
2. `rack_id` 必须指向存在的 `instances/racks/*.yaml`（`TELECOM-FK-001`）
3. `device_id` 必须指向存在的 `instances/devices/*.yaml`（`REFS-001`）
4. Mate 中的 `parent`/`child`/`part_a_id`/`part_b_id` 必须指向已声明的实例

---

## 4. Layout 约定（`layouts/layout.yaml`）

```yaml
# 每条记录对应一个装在机柜中的设备或 PDU
- instance: SRV-01           # 设备/PDU ID
  rack_id: RACK-A01          # 所在机柜（必填）
  position_u: 10             # 起始 U 位（必填）
  pdu_id: PDU-A              # 供电 PDU（必填）

- instance: PDU-A
  rack_id: RACK-A01
  position_u: 0
  pdu_id: PDU-A              # PDU 自身的 pdu_id 指向自己
```

**注意**：只要任务涉及机柜和设备/PDU，就必须为每个设备和 PDU 各创建一条 layout 记录。缺失 layout 会导致 `TELECOM-COLLISION-001` 检查失败。

---

## 5. 推荐工作流

1. 阅读 scaffold 中的 `docs/*.md` 设计规范和 `piki.toml` 配置
2. 确认 scaffold 中已有的 `models/` 和 `instances/` 文件，不要重复
3. 按本参考文档的目录约定创建新的 YAML 文件
4. 运行 `piki check` 验证
5. 修复所有错误后运行 `piki generate` 生成交付物到 `dist/`
6. 再次运行 `piki check` 确认最终无错误

"""

REPAIR_MARKERS = {
    "done": ".sdhwe.done",
    "give_up": ".sdhwe.give_up",
    "info_gap": ".sdhwe.info_gap",
    "no_solution": ".sdhwe.no_solution",
}

_REPAIR_MARKER_INSTRUCTIONS = """\
## 主动终止标记

本轮任务允许你在以下情况主动创建标记文件，系统会立即停止并记录原因：

- `.sdhwe.done` — 你认为任务已完成（系统仍会验证）。
- `.sdhwe.give_up` — 你确认当前能力不足以完成该任务。
- `.sdhwe.info_gap` — 任务描述或 scaffold 缺少关键信息，无法继续。
- `.sdhwe.no_solution` — 需求本身相互矛盾，不存在合法设计解（例如提供的构件无法同时满足强度和重量约束）。

你可以在标记文件里写一句简短说明。不要在没有充分尝试前随意放弃。
"""


class PromptBuilder:
    """Build prompts for Actor rollout."""

    def __init__(self, piki_ref_path: Path | None = None):
        self.piki_ref_path = piki_ref_path

    def _load_design_spec(self, scaffold_dir: Path) -> str | None:
        """Load the project design spec if present in the scaffold."""
        spec_path = scaffold_dir / "docs" / "rack-design-spec.md"
        if spec_path.exists():
            return spec_path.read_text(encoding="utf-8")
        return None

    def build(
        self,
        task_metadata: dict[str, Any],
        scaffold_dir: Path,
        require_generator: bool = True,
        output_mode: Literal["cli", "api"] = "cli",
        repair_mode: bool = False,
        baseline_mode: bool = False,
    ) -> str:
        """Build the full prompt injected into the actor.

        Args:
            task_metadata: Parsed task.yaml as dict.
            scaffold_dir: Path to the task's scaffold/ directory.
            require_generator: Whether to emphasize deliverable generation.
            output_mode: "cli" for agents that mutate the working directory
                directly; "api" for agents that return YAML code blocks.
            repair_mode: Include repair-loop instructions and termination markers.
            baseline_mode: Baseline prompt with no ESA feedback / no markers.
        """
        parts: list[str] = []

        task_id = task_metadata.get("task_id", "unknown")
        task_name = task_metadata.get("name", "Unnamed")
        task_type = task_metadata.get("task_type", "comprehensive")
        difficulty = task_metadata.get("difficulty", "medium")
        plugins = task_metadata.get("plugins", [])

        parts.append(
            "You are a hardware engineering design agent. Your task is to "
            "complete a declarative engineering design using piki.\n\n"
            f"**Task**: {task_name} ({task_id})\n"
            f"**Type**: {task_type} | **Difficulty**: {difficulty}\n"
            f"**Plugins**: {', '.join(plugins)}"
        )

        parts.append(_ADL_PIKI_CONVENTION)

        # Project design specification: agents must consult engineering standards
        # before making design decisions. For CLI agents this is a file in the
        # workspace; for API agents we inline the spec so it is actually visible.
        design_spec = self._load_design_spec(scaffold_dir)
        if design_spec:
            parts.append("## 项目设计规范\n")
            parts.append(
                "在执行设计任务前，请先查阅本项目的设计规范 `docs/rack-design-spec.md`。 "
                "所有设计决策（字段名、U 位分配、目录结构等）都应以规范为依据。 "
                "未依据规范完成设计会被视为 Poor Practice。\n"
            )
            if output_mode == "api":
                parts.append(design_spec)
            else:
                parts.append(
                    "规范文件已放在 workspace 的 `docs/rack-design-spec.md`，请主动阅读并引用。\n"
                )

        # Optional full piki reference
        if self.piki_ref_path and self.piki_ref_path.exists():
            parts.append("## Piki 完整参考\n")
            parts.append(self.piki_ref_path.read_text(encoding="utf-8"))

        # Scaffold info
        parts.append("## Scaffold 中已有的文件（只读，请勿修改）\n")
        if scaffold_dir.exists():
            for f in sorted(scaffold_dir.rglob("*")):
                if f.is_file():
                    rel = f.relative_to(scaffold_dir)
                    parts.append(f"- `{rel}`")
                    # Include small scaffold files inline for context
                    if (
                        f.suffix in (".yaml", ".yml", ".toml")
                        and f.stat().st_size < settings.SCAFFOLD_INLINE_MAX_BYTES
                    ):
                        parts.append(f"\n`{rel}`:\n```yaml")
                        parts.append(f.read_text(encoding="utf-8"))
                        parts.append("```\n")
        else:
            parts.append("- (无 scaffold)")

        # Requirement
        requirement = task_metadata.get("requirement", "")
        parts.append(f"\n## 设计需求\n\n{requirement}")

        # Expected outputs
        expected = task_metadata.get("expected_files", [])
        deliverables = task_metadata.get("expected_deliverables", [])

        parts.append("\n## 需要产出的文件\n")
        if expected:
            parts.append("必须创建以下 YAML 文件：\n")
            for f in expected:
                parts.append(f"- `{f}`")
        if deliverables:
            parts.append("\n必须生成交付物（执行 `piki generate`）：\n")
            for d in deliverables:
                parts.append(f"- `{d}`")

        # Output instructions
        if output_mode == "api":
            parts.append(
                "\n## 输出要求\n\n"
                "1. 输出每个文件为一个独立的 ```yaml 代码块。\n"
                "2. 每个代码块的第一行必须是一个文件路径注释，例如 "
                "`# instances/devices/SRV-01.yaml`。\n"
                "3. 务必把设备实例放在 `instances/devices/`，不要放在 `instances/` 根目录。\n"
                "4. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
                "5. 只产出与任务相关的文件，不要额外发挥。\n"
                "\n请开始完成这个工程设计任务，输出所有需要的 YAML 文件。"
            )
        elif baseline_mode:
            parts.append(
                "\n## 输出要求\n\n"
                "1. 作为设计 agent，请直接在 workspace 目录中创建/修改 YAML 文件；"
                "不需要在 stdout 中输出完整 YAML。\n"
                "2. 务必把设备实例放在 `instances/devices/`，不要放在 `instances/` 根目录。\n"
                "3. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
                "4. 不要运行 `piki check`、`piki generate` 或任何外部验证命令；"
                "系统会在你提交后统一验证。\n"
                "5. 只产出与任务相关的文件，不要额外发挥。\n"
                "\n请开始完成这个工程设计任务。"
            )
        elif repair_mode:
            parts.append(
                "\n## 输出要求\n\n"
                "1. 作为设计 agent，请直接在 workspace 目录中创建/修改 YAML 文件；"
                "不需要在 stdout 中输出完整 YAML。\n"
                "2. 务必把设备实例放在 `instances/devices/`，不要放在 `instances/` 根目录。\n"
                "3. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
                "4. 系统会在你每次提交文件后运行 `piki check` 并返回诊断；"
                "你可以根据诊断继续修改，也可以主动报告完成或失败。\n"
                "5. 只产出与任务相关的文件，不要额外发挥。\n"
                "\n请开始完成这个工程设计任务。"
            )
            parts.append(_REPAIR_MARKER_INSTRUCTIONS)
        else:
            parts.append(
                "\n## 输出要求\n\n"
                "1. 作为设计 agent，请直接在 workspace 目录中创建/修改 YAML 文件；"
                "不需要在 stdout 中输出完整 YAML。\n"
                "2. 务必把设备实例放在 `instances/devices/`，不要放在 `instances/` 根目录。\n"
                "3. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
                "4. 完成后必须先执行 `piki check`，确认无错误后再执行 `piki generate`。\n"
                "5. 如果任务要求交付物，执行 `piki generate` 后检查 `dist/` 下是否出现对应的 `.csv` / `.svg` 文件；"
                "若未出现，先修复 `piki check` 报错再重新生成。\n"
                "6. 只产出与任务相关的文件，不要额外发挥。\n"
                "\n请开始完成这个工程设计任务。"
            )

        if require_generator and not repair_mode and not baseline_mode:
            parts.append(
                "\n**重要**：评分时会检查 `dist/` 下的交付物文件（如 bom.csv、"
                "power-budget.csv、port-map.csv、rack-panel-*.svg）是否已生成。"
                "如果 `piki check` 有错误，`piki generate` 可能失败，请务必先修复所有错误。"
            )

        return "\n".join(parts)

    def build_repair_turn(
        self,
        task_metadata: dict[str, Any],
        project_dir: Path,
        score: Any,
        turn: int,
        max_repair: int,
        diagnostics: list[dict] | None = None,
    ) -> str:
        """Build a self-contained repair prompt for turn N of a repair loop.

        The prompt includes the original requirement, the current workspace
        files, and the diagnostics from the last `piki check`. It is designed
        to be consumed by a stateless CLI actor (Kimi/Gemini) that can inspect
        the workspace directly.
        """
        task_id = task_metadata.get("task_id", "unknown")
        task_name = task_metadata.get("name", "Unnamed")
        requirement = task_metadata.get("requirement", "")

        parts: list[str] = []
        parts.append(
            "You are a hardware engineering design agent. You are continuing "
            "a declarative engineering design task in piki.\n\n"
            f"**Task**: {task_name} ({task_id})\n"
            "Review the requirement and the current workspace, then fix the errors."
        )

        parts.append("## 设计需求\n\n" + requirement)

        # List current files (excluding marker files and hidden/git internals)
        files = sorted(
            p.relative_to(project_dir)
            for p in project_dir.rglob("*")
            if p.is_file()
            and not p.name.startswith(".")
            and ".git" not in str(p.relative_to(project_dir)).split(os.sep)
        )
        parts.append("\n## 当前 workspace 中的文件\n")
        if files:
            for f in files:
                parts.append(f"- `{f}`")
        else:
            parts.append("- (无文件)")

        # Format diagnostics from the last score
        parts.append("\n## 上次 `piki check` 的诊断\n")
        has_errors = False
        if diagnostics:
            for d in diagnostics[: settings.REPAIR_PROMPT_MAX_DIAGNOSTICS]:
                has_errors = True
                rule = d.get("rule_id", "")
                name = d.get("name", "")
                msg = str(d.get("message", "")).splitlines()[0]
                file = d.get("file", "")
                parts.append(f"- `{rule}` {name}: {msg}" + (f" (文件: {file})" if file else ""))
        else:
            for layer in ("L0", "L1", "L2", "L3", "L4", "L5"):
                ls = score.layers.get(layer)
                if not ls:
                    continue
                if ls.errors:
                    has_errors = True
                    parts.append(f"\n**{layer}** ({'通过' if ls.passed else '未通过'}):")
                    max_errors = settings.REPAIR_PROMPT_MAX_ERRORS_PER_LAYER
                    for err in ls.errors[:max_errors]:
                        parts.append(f"- {err}")
                    if len(ls.errors) > max_errors:
                        parts.append(f"- ... 还有 {len(ls.errors) - max_errors} 条错误")
        if not has_errors:
            parts.append("所有检查已通过。如果交付物尚未生成，请运行 `piki generate`.")

        remaining = max_repair - turn + 1
        parts.append(f"\n## 剩余轮次\n\n当前是第 {turn} 轮修复，最多还有 {remaining} 轮。")

        parts.append(
            "\n## 操作要求\n\n"
            "1. 直接修改 workspace 中的 YAML 文件以修复上述错误。\n"
            "2. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
            "3. 如果你认为任务已经完成，创建 `.sdhwe.done`。\n"
            "4. 如果你确认无法完成，创建 `.sdhwe.give_up`、`.sdhwe.info_gap` 或 `.sdhwe.no_solution`。\n"
            "5. 只产出与任务相关的文件，不要额外发挥。"
        )
        parts.append(_REPAIR_MARKER_INSTRUCTIONS)

        return "\n".join(parts)

    def build_self_check_turn(
        self,
        task_metadata: dict[str, Any],
        project_dir: Path,
        diagnostics: list[dict],
        turn: int,
        max_rounds: int,
    ) -> str:
        """Build a self-check continuation prompt.

        Injected after the agent submits ``.sdhwe.done`` but ``piki check``
        still reports errors.  The prompt shows only the diagnostics (no full
        score object) and asks the agent to fix the remaining issues.
        """
        task_id = task_metadata.get("task_id", "unknown")
        task_name = task_metadata.get("name", "Unnamed")

        parts: list[str] = []
        parts.append(
            "You are a hardware engineering design agent. You marked the task "
            "as done, but `piki check` still found errors in your design.\n\n"
            f"**Task**: {task_name} ({task_id})\n"
            "Review the diagnostics below and fix the remaining issues in the "
            "workspace YAML files."
        )

        # Diagnostics only — concise, no file listing
        parts.append("\n## `piki check` 诊断\n")
        for d in diagnostics[: settings.REPAIR_PROMPT_MAX_DIAGNOSTICS]:
            rule = d.get("rule_id", "")
            name = d.get("name", "")
            msg = str(d.get("message", "")).splitlines()[0]
            file = d.get("file", "")
            parts.append(f"- `{rule}` {name}: {msg}" + (f" (文件: {file})" if file else ""))

        remaining = max_rounds - turn + 1
        parts.append(
            f"\n## 剩余自检轮次\n\n"
            f"这是第 {turn} 轮自检修复，最多还有 {remaining} 轮。"
        )

        parts.append(
            "\n## 操作要求\n\n"
            "1. 直接修改 workspace 中的 YAML 文件以修复上述错误。\n"
            "2. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
            "3. 修复完成后重新创建 `.sdhwe.done`。\n"
            "4. 如果你确认当前错误无法在当前轮次内解决，创建 `.sdhwe.give_up`。\n"
            "5. 只修复与诊断相关的文件，不要改动已通过检查的部分。"
        )

        return "\n".join(parts)

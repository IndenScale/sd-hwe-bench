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

#### PDU 实例 (`instances/pdus/`) ⚠️ 关键陷阱

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

```text
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

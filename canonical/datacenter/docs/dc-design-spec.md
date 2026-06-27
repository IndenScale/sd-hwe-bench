# 数据中心设计规范

本规范是 Canonical Datacenter Project 的工程标准。所有设计任务必须遵循本规范。

## 0. 项目目录结构

```text
canonical-datacenter/
├── piki.toml
├── models/
│   ├── devices/       # 计算节点、存储节点、ToR 交换机
│   ├── racks/         # 数据中心 42U 机柜
│   ├── power/         # 三相 PDU
│   └── cooling/       # 列间精密空调
├── instances/
│   ├── devices/
│   ├── racks/
│   ├── pdus/
│   ├── ports/
│   ├── transceivers/
│   ├── fibers/
│   └── port_connections/
├── rooms/             # 机房定义
├── facilities/        # 基础设施（空调等）
├── spaces/            # 空间区域（冷热通道等）
├── layouts/           # 机柜布局
├── mates/
│   ├── rack-mount/
│   ├── power-iec/
│   ├── sfp28-cage/
│   ├── lc-connector/
│   ├── rack-in-row/
│   ├── cable-tray-over-row/
│   └── must-clear/
└── docs/
    └── dc-design-spec.md
```

## 1. 机柜与排

### 1.1 机柜实例
文件路径：`instances/racks/<RACK-ID>.yaml`

机柜 model: `dc-rack-42u`，42U，1000mm 深，600mm 宽。

### 1.2 机柜排 (RackRow)
文件路径：`rooms/<ROW-ID>.yaml`

```yaml
id: ROW-A
family: RackRowFamily
name: "A 排"
row_index: 0
rack_count: 4
rack_inline_spacing_mm: 600
```

### 1.3 机柜入排配合
文件路径：`mates/rack-in-row/<ID>.yaml`

```yaml
id: ROW-A-RACK-A01
type: rack-in-row
part_a_id: ROW-A
part_b_id: RACK-A01
attributes:
  bay_index: 0
```

## 2. PDU 声明规范

文件路径：`instances/pdus/<PDU-ID>.yaml`

```yaml
id: PDU-A01-A
rack_id: RACK-A01
family: PduFamily
model: dc-pdu-3phase-32a
capacity_w: 22080
interfaces:
  - id: outlet-1
    interface_type: IEC-C14
    direction: output
```

- **容量字段名**: `capacity_w`，不是 `power_capacity_w`
- **必须声明** `rack_id`
- 每机柜双路 PDU（A 路 + B 路）

## 3. 设备声明规范

文件路径：`instances/devices/<DEVICE-ID>.yaml`

计算节点: `compute-node-2u`, 2U, 500W TDP, 双电源冗余
存储节点: `storage-node-4u`, 4U, 800W TDP, 双电源冗余
ToR 交换机: `tor-switch-48p-25g`, 1U, 250W TDP, 双电源冗余

## 4. U 位规则

- 2U 设备间至少间隔 1U
- 4U 设备间至少间隔 1U
- 跨类型设备间至少间隔 1U
- ToR 交换机通常部署在机柜顶部 (U40-U42 区域)

## 5. 常见错误速查

| 错误 | 根因 | 正确做法 |
|------|------|----------|
| L1: PDU 字段不存在 | `power_capacity_w` | `capacity_w` (§2) |
| L2: PDU 未关联机柜 | 缺少 `rack_id` | 添加 `rack_id` |
| U 位冲突 | 未留间隔 | §4 规则 |
| L2: 引用失败 | 设备/PDU 映射错误 | 核对 id |

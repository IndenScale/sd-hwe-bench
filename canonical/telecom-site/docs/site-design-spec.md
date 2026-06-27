# 基站站点设计规范

本规范是 Canonical Telecom Site Project 的工程标准。

## 1. 户外机柜
文件路径：`instances/racks/<ID>.yaml`，model: `outdoor-cabinet-ip65`

## 2. PDU 声明
文件路径：`instances/pdus/<ID>.yaml`
- family: PduFamily
- 容量字段名: **`capacity_w`**（不是 `power_capacity_w`）
- **必须声明 `rack_id`**
- 接口类型 `IEC-C14`，方向 `output`

## 3. 设备声明
文件路径：`instances/devices/<ID>.yaml`
- BBU: model `bbu-5900`, 2U, 350W, CPRI 光口

## 4. U 位规则
- 不同设备间至少间隔 1U，禁止 U 位重叠

## 5. 天线/RRU
文件路径：`instances/antennas/<ID>.yaml`，family: FacilityFamily

## 6. 防雷接地
SPD→接地极 cable-connection 配合，接地线 16mm²

## 7. 馈线
BBU↔RRU CPRI 光口连接，RRU↔天线射频馈线

## 常见错误
| 错误 | 根因 | 正确 |
|------|------|------|
| L1: 字段不存在 | power_capacity_w | capacity_w (§2) |
| L2: 引用失败 | 缺少 rack_id | 添加 rack_id |

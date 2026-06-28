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

## 8. 天线参数规范

### 8.1 增益（Gain）

天线增益 dBi 表示辐射功率集中程度。板状天线典型 15-21dBi，抛物面天线 25-40dBi，全向天线 2-10dBi。

### 8.2 波束宽度

- **水平波束宽度**：决定扇区覆盖角度。定向天线典型 33° / 65° / 90°
- **垂直波束宽度**：影响覆盖距离。值越小覆盖越远，典型 5°-15°

### 8.3 下倾角（Downtilt）

总下倾角 = 机械下倾 + 电调下倾。用于控制覆盖半径，公式：

```text
tilt_deg = arctan(h_antenna_m / d_target_m) + vertical_beamwidth_deg / 2
```

其中 h_antenna_m 为天线中心高度，d_target_m 为目标覆盖距离。

### 8.4 风载荷

天线安装必须考虑风载荷。公式：

```text
F_wind_N = 0.5 * ρ * v² * C_d * A
```

其中 ρ=1.225 kg/m³（空气密度），v 为设计风速 m/s，C_d 为阻力系数（平板取 1.2），A 为迎风面积 m²。F_wind_N 不得超过 model 中 max_wind_load_n。

## 9. 链路预算（Link Budget）

### 9.1 基本公式

接收功率 dBm：

```text
Prx_dbm = Ptx_dbm + Gtx_dbi - Ltx_db - Lpath_db + Grx_dbi - Lrx_db
```

其中：

- Ptx_dbm：发射功率（RRU 每通道）
- Gtx_dbi / Grx_dbi：发射/接收天线增益
- Ltx_db / Lrx_db：发射/接收端馈线损耗
- Lpath_db：路径损耗

### 9.2 路径损耗（Okumura-Hata 模型）

适用于 150-2000MHz，距离 1-20km，城市环境：

```text
Lpath_urban_db = 69.55 + 26.16*log10(f_MHz) - 13.82*log10(hb_m) 
                  - a(hm_m) + (44.9 - 6.55*log10(hb_m))*log10(d_km)
```

其中：

- f_MHz：中心频率
- hb_m：基站天线高度（30-200m）
- hm_m：移动台天线高度（取 1.5m）
- d_km：距离
- a(hm_m)：移动台天线修正因子。对中型城市：
  `a(hm) = (1.1*log10(f) - 0.7)*hm - (1.56*log10(f) - 0.8)`

### 9.3 接收灵敏度与裕量

BBU 接收灵敏度典型值：-102 dBm（QPSK）。链路裕量要求 ≥ 10dB：

```text
margin_db = Prx_dbm - sensitivity_dbm
margin_db >= 10
```

## 10. 扇区规划（Sector Planning）

### 10.1 三扇区标准配置

标准宏站使用三扇区覆盖 360°：

- 扇区 α（Sector-A）：方位角 0°，主导小区方向正北
- 扇区 β（Sector-B）：方位角 120°
- 扇区 γ（Sector-C）：方位角 240°
每扇区 1 副定向天线 + 1 台 RRU。

### 10.2 覆盖半径计算

基于链路预算反算覆盖半径：

```text
给定 margin_db = 10dB，求解 d_km：
Prx_dbm = Ptx_dbm + Gtx_dbi - Ltx_db + Grx_dbi - Lrx_db - Lpath_db(d_km)
要求 Prx_dbm - sensitivity_dbm >= 10
```

使用 Okumura-Hata 逆推 d_km，取满足条件的最大 d 作为覆盖半径。

### 10.3 扇区间重叠

相邻扇区覆盖应有 10-15% 重叠，确保切换区。重叠宽度：

```text
overlap_m = 2 * d_coverage_m * sin(π/6)  ≈ 0.518 * d_coverage_m
```

### 10.4 频率规划

推荐 1×3×1 复用（每扇区不同频点），避免同频干扰。

## 11. 塔桅选型与风载荷校核

### 11.1 塔桅选型约束

新建站点需选择合适塔型。30m 角钢格构式塔参数：

- 基底宽度 3.0m，塔顶宽度 0.8m
- 最大天线挂载数 6 副
- 单挂点最大载荷 80kg
- 总载荷上限 400kg
- 设计风速 40m/s，生存风速 55m/s

### 11.2 天线风载荷计算

每副天线的迎风面积 A = width_mm × height_mm / 1e6（㎡）。平板天线阻力系数 Cd = 1.2。

单副天线风载荷：F_wind_single_N = 0.5 × 1.225 × v² × 1.2 × A

塔身风载荷：F_wind_tower_N = 0.5 × 1.225 × v² × 1.0 × tower_projected_area_m2

其中塔身投影面积近似为 (base_width + top_width) / 2 × height。

### 11.3 倾覆力矩校核

倾覆力矩（对基底）：M_overturn_Nm = Σ(F_wind_i × h_mount_i) + F_wind_tower × (height_m / 2)

抗倾覆力矩：M_resist_Nm = (total_payload_kg + tower_self_weight_kg) × 9.81 × (base_width_m / 2)

其中塔身自重（30m 角钢格构式）≈ 3500kg。

安全系数：FS_overturn = M_resist / M_overturn ≥ 1.5

### 11.4 输出要求

风载荷校核报告：`reports/wind-load-report.yaml`

```yaml
tower_model: lattice-angle-steel-tower-30m
design_wind_speed_ms: 40.0
antennas:
  - id: ANT-01
    wind_force_n: <calculated>
    mount_height_m: 28.0
  ...
tower_wind_force_n: <calculated>
overturning_moment_nm: <calculated>
resisting_moment_nm: <calculated>
safety_factor: <calculated>
pass: true/false
```

## 12. BBU 散热冗余设计

### 12.1 热载荷计算

机柜内所有设备的总 TDP：P_total_w = Σ P_device_i

### 12.2 冷却需求

户外机柜（outdoor-cabinet-ip65）自带冷却容量 cooling_capacity_w。

有效冷却比：η_cooling = cooling_capacity_w / P_total_w

散热冗余要求：η_cooling ≥ 1.2（20% 冗余）

若 η_cooling < 1.2，须添加强制通风或额外冷却单元。

### 12.3 BBU 热节流风险

BBU 热节流温度 50°C。机柜内部温升估算：
ΔT_cabinet = P_total_w / (h × A_surface)

其中 h ≈ 5 W/(m²·K)（自然对流），A_surface 为机柜外表面积：
A_surface_m2 = 2 × (W × H + W × D + H × D)（机柜宽 W、高 H、深 D，单位 m）

机柜内部温度 T_internal = T_ambient_max + ΔT_cabinet

BBU 热节流风险：T_internal > thermal_throttle_temp 时触发降频。

### 12.4 输出要求

散热分析报告：`reports/thermal-report.yaml`

```yaml
total_tdp_w: <sum>
cooling_capacity_w: <from cabinet model>
cooling_ratio: <η_cooling>
cooling_pass: true/false
cabinet_surface_area_m2: <calculated>
temp_rise_c: <calculated>
internal_temp_c: <ambient_max + ΔT>
thermal_throttle_risk: true/false
```

## 13. 频谱干扰协调

### 13.1 邻频干扰分析

扇区间频点间隔 Δf = f_sector_j - f_sector_i。要求 Δf ≥ 10MHz 避免邻频干扰。

ACIR（邻信道干扰比）：
ACIR_db = -10 × log10(10^(-ACLR_db/10) + 10^(-ACS_db/10))

其中 ACLR（邻信道泄漏比）取 45dB，ACS（邻信道选择性）取 33dB。

### 13.2 覆盖重叠区干扰

相邻扇区覆盖重叠区接收信号强度差：
ΔRSSI_db = RSSI_serving_db - RSSI_interferer_db

其中 RSSI_serving = EIRP - Lpath(d_overlap)
RSSI_interferer = EIRP - Lpath(d_coverage - d_overlap × cos(beamwidth/2))

若 ΔRSSI < 6dB，则重叠区存在切换干扰风险，需调整下倾角或降低干扰扇区发射功率。

### 13.3 输出要求

干扰分析报告：`reports/interference-report.yaml`

```yaml
sector_pairs:
  - sectors: [alpha, beta]
    frequency_separation_mhz: <calculated>
    acir_db: <calculated>
    overlap_rssi_delta_db: <calculated>
    risk: true/false
  - sectors: [beta, gamma]
    ...
  - sectors: [gamma, alpha]
    ...
overall_risk: true/false
```

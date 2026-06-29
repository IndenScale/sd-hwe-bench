# 附录 A：任务详情

表 A.1 列出 SD-HWE-Bench 当前版本全部 37 个 telecom 任务。

| # | Task ID | 名称 | 类型 | 难度 |
|---|---------|------|------|------|
| 1 | `aidc-conceptual-design-001` | AIDC 60MW 概念设计-调度联合优化 | co-design | hard |
| 2 | `aidc-detailed-design-001` | AIDC 60MW 详细设计 | detailed-design | hard |
| 3 | `aidc-epc-001` | AIDC 60MW EPC 施工排程与风险响应 | epc | hard |
| 4 | `comprehensive-001` | 综合设计-完整机柜部署 | comprehensive | hard |
| 5 | `connection-design-001` | 连接设计-服务器上联 | connection-design | medium |
| 6 | `dc-stage1-foundation-rackmount-deploy-thermal` | 数据中心基础阶段：机柜排、机柜、PDU 与计算节点声明 | comprehensive | medium |
| 7 | `dc-stage2-foundation-rackmount-deploy-thermal` | 数据中心机柜入排配合阶段 | comprehensive | medium |
| 8 | `dc-stage3-foundation-rackmount-deploy-thermal` | 数据中心设备部署阶段：RACK-A01 完整部署 | comprehensive | hard |
| 9 | `dc-stage4-foundation-rackmount-deploy-thermal` | 数据中心散热阶段：列间空调声明与布线配合 | comprehensive | medium |
| 10 | `dc-stage5-spine-leaf-topology` | 数据中心网络阶段：Spine-Leaf 组网全互联设计 | comprehensive | hard |
| 11 | `edge-dc-design-001` | 边缘数据中心设计-调度联合优化 | co-design | medium |
| 12 | `instance-declare-001` | 实例声明-服务器部署 | instance-declaration | easy |
| 13 | `layout-design-001` | 布局设计-机柜部署 | layout-design | easy |
| 14 | `mating-design-001` | 配合设计-机柜装配与供电 | mating-design | medium |
| 15 | `rack-stage1-init-deploy-connect-verify` | 机柜初始化阶段：机柜声明、PDU 部署与布局分配 | comprehensive | medium |
| 16 | `rack-stage2-init-deploy-connect-verify` | 设备部署阶段：服务器与交换机声明、rack-mount 配合 | comprehensive | medium |
| 17 | `rack-stage3-init-deploy-connect-verify` | 连接与配合阶段：端口声明、光纤连接、光模块与连接器配合 | comprehensive | hard |
| 18 | `rack-stage4-init-deploy-connect-verify` | 扩展验证阶段：电源配合与跨机柜扩容 | comprehensive | hard |
| 19 | `site-stage1-tower-feeder-grounding` | 基站塔桅阶段：天线塔、设备方舱、天线与防雷系统声明 | comprehensive | hard |
| 20 | `site-stage2-tower-feeder-grounding` | 基站馈线阶段：馈线声明与射频连接 | comprehensive | medium |
| 21 | `site-stage3-tower-feeder-grounding` | 基站接地与综合阶段：电源、接地、线槽与综合配合 | comprehensive | medium |
| 22 | `site-stage4-rf-params-coverage-planning` | 基站射频阶段：天线参数配置、链路预算与扇区规划 | comprehensive | hard |
| 23 | `site-stage5-wind-load-tower-analysis` | 基站结构阶段：塔桅选型与风载荷校核 | comprehensive | hard |
| 24 | `site-stage6-thermal-redundancy-analysis` | 基站热管理阶段：BBU 散热冗余与热节流风险评估 | comprehensive | hard |
| 25 | `site-stage7-interference-coordination` | 基站频谱阶段：三扇区邻频干扰与覆盖重叠干扰协调分析 | comprehensive | hard |
| 26 | `telecom-cross-001` | 跨专业综合：地板载荷约束下的机柜部署 | comprehensive | hard |
| 27 | `telecom-cross-002` | 跨专业综合：散热约束下的机柜规划 | comprehensive | hard |
| 28 | `telecom-cross-003` | 跨专业综合：供电容量规划和设备部署 | comprehensive | hard |
| 29 | `telecom-easy-compound-001` | 声明三台服务器设备 | instance-declaration | easy |
| 30 | `telecom-easy-compound-002` | 声明所有端口实例 | instance-declaration | easy |
| 31 | `telecom-easy-compound-003` | 声明光模块、光纤和端口连接 | connection-design | easy |
| 32 | `telecom-easy-compound-004` | 创建 rack-mount、SFP28-cage 和 LC-connector 配合 | mating-design | easy |
| 33 | `telecom-easy-compound-005` | 创建电源 IEC 配合并验证完整系统 | comprehensive | easy |
| 34 | `telecom-emergent-001` | 涌现约束：添加第三路 PDU | instance-declaration | medium |
| 35 | `telecom-emergent-002` | 涌现约束：声明第二个机柜 | instance-declaration | medium |
| 36 | `telecom-emergent-003` | 涌现约束：部署存储节点 | comprehensive | medium |
| 37 | `telecom-emergent-004` | 涌现约束：遵循 U 位间隔惯例 | layout-design | medium |

Table: SD-HWE-Bench 完整任务列表。{#tbl:task-list}

## A.1 任务来源

全部 37 个任务从 6 个 Canonical 工程的 commit 历史中提取或基于其构建：

| Canonical 工程 | 任务数 | 领域 | 描述 |
|----------------|--------|------|------|
| `canonical/telecom-rack` | 4 | 电信机柜 | 42U 机柜扩容，PDU/设备/光纤/跨机柜 |
| `canonical/datacenter` | 5 | 数据中心 | 数据中心机房，ToR 组网，地板载荷 |
| `canonical/telecom-site` | 7 | 电信基站 | 户外基站，天线/RRU/防雷/馈线/结构/热管理/频谱 |
| `canonical/datacenter-hall` | 1 | AIDC | 14.8kW 小机房设计-调度联合优化 |
| `canonical/datacenter-hall-60mw` | 1 | AIDC | 60MW 大型 AI 数据中心概念设计-调度联合优化 |
| `canonical/aidc-detailed` | 2 | AIDC | 60MW AIDC 详细设计与 EPC 施工排程 |

## A.2 代表性任务结构

以 `rack-stage1-init-deploy-connect-verify` 为例，任务目录结构如下：

```text
tasks/telecom/rack-stage1-init-deploy-connect-verify/
├── task.yaml          # 任务元数据（含 scoring_layers）
├── scaffold/          # Agent 可见初始工程
│   ├── instances/devices/
│   └── ...
├── solution/          # 参考方案（Agent 不可见）
└── expected/          # 期望交付物（可选）
```

`task.yaml` 包含：任务名称、类型、难度、需求描述、评分层配置。
评分层可在任务级别覆盖——例如 compound-001 不含 L3（工程约束）层，AIDC 任务启用 L4 仿真合规层。

## A.3 难度分布

| 难度 | 数量 | 占比 | 代表性任务 |
|------|------|------|-----------|
| easy | 7 | 19% | telecom-easy-compound-001~005, instance-declare-001, layout-design-001 |
| medium | 14 | 38% | rack-stage1~2, dc-stage1~2/site-stage2~3, connection-design-001, mating-design-001, telecom-emergent-001~004, edge-dc-design-001 |
| hard | 16 | 43% | comprehensive-001, rack-stage3~4, dc-stage3/5, site-stage1/4~7, telecom-cross-001~003, aidc-conceptual-design-001, aidc-detailed-design-001, aidc-epc-001 |

Table: 当前版本难度分布。{#tbl:difficulty-dist}

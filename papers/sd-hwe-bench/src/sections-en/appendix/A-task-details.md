# Appendix A: Task Details

Table A.1 lists all 33 telecom tasks in SD-HWE-Bench v3.

| # | Task ID | Name | Type | Difficulty |
|---|---------|------|------|------------|
| 1 | `comprehensive-001` | 综合设计-完整机柜部署 | comprehensive | hard |
| 2 | `connection-design-001` | 连接设计-服务器上联 | connection-design | medium |
| 3 | `dc-stage1-foundation-rackmount-deploy-thermal` | 数据中心基础阶段：机柜排、机柜、PDU 与计算节点声明 | comprehensive | medium |
| 4 | `dc-stage2-foundation-rackmount-deploy-thermal` | 数据中心机柜入排配合阶段 | comprehensive | medium |
| 5 | `dc-stage3-foundation-rackmount-deploy-thermal` | 数据中心设备部署阶段：RACK-A01 完整部署 | comprehensive | hard |
| 6 | `dc-stage4-foundation-rackmount-deploy-thermal` | 数据中心散热阶段：列间空调声明与布线配合 | comprehensive | medium |
| 7 | `dc-stage5-spine-leaf-topology` | 数据中心网络阶段：Spine-Leaf 组网全互联设计 | comprehensive | hard |
| 8 | `instance-declare-001` | 实例声明-服务器部署 | instance-declaration | easy |
| 9 | `layout-design-001` | 布局设计-机柜部署 | layout-design | easy |
| 10 | `mating-design-001` | 配合设计-机柜装配与供电 | mating-design | medium |
| 11 | `rack-stage1-init-deploy-connect-verify` | 机柜初始化阶段：机柜声明、PDU 部署与布局分配 | comprehensive | medium |
| 12 | `rack-stage2-init-deploy-connect-verify` | 设备部署阶段：服务器与交换机声明、rack-mount 配合 | comprehensive | medium |
| 13 | `rack-stage3-init-deploy-connect-verify` | 连接与配合阶段：端口声明、光纤连接、光模块与连接器配合 | comprehensive | hard |
| 14 | `rack-stage4-init-deploy-connect-verify` | 扩展验证阶段：电源配合与跨机柜扩容 | comprehensive | hard |
| 15 | `site-stage1-tower-feeder-grounding` | 基站塔桅阶段：天线塔、设备方舱、天线与防雷系统声明 | comprehensive | hard |
| 16 | `site-stage2-tower-feeder-grounding` | 基站馈线阶段：馈线声明与射频连接 | comprehensive | medium |
| 17 | `site-stage3-tower-feeder-grounding` | 基站接地与综合阶段：电源、接地、线槽与综合配合 | comprehensive | medium |
| 18 | `site-stage4-rf-params-coverage-planning` | 基站射频阶段：天线参数配置、链路预算与扇区规划 | comprehensive | hard |
| 19 | `site-stage5-wind-load-tower-analysis` | 基站结构阶段：塔桅选型与风载荷校核 | comprehensive | hard |
| 20 | `site-stage6-thermal-redundancy-analysis` | 基站热管理阶段：BBU 散热冗余与热节流风险评估 | comprehensive | hard |
| 21 | `site-stage7-interference-coordination` | 基站频谱阶段：三扇区邻频干扰与覆盖重叠干扰协调分析 | comprehensive | hard |
| 22 | `telecom-cross-001` | 跨专业综合：地板载荷约束下的机柜部署 | comprehensive | hard |
| 23 | `telecom-cross-002` | 跨专业综合：散热约束下的机柜规划 | comprehensive | hard |
| 24 | `telecom-cross-003` | 跨专业综合：供电容量规划和设备部署 | comprehensive | hard |
| 25 | `telecom-easy-compound-001` | 声明三台服务器设备 | instance-declaration | easy |
| 26 | `telecom-easy-compound-002` | 声明所有端口实例 | instance-declaration | easy |
| 27 | `telecom-easy-compound-003` | 声明光模块、光纤和端口连接 | connection-design | easy |
| 28 | `telecom-easy-compound-004` | 创建 rack-mount、SFP28-cage 和 LC-connector 配合 | mating-design | easy |
| 29 | `telecom-easy-compound-005` | 创建电源 IEC 配合并验证完整系统 | comprehensive | easy |
| 30 | `telecom-emergent-001` | 涌现约束：添加第三路 PDU | instance-declaration | medium |
| 31 | `telecom-emergent-002` | 涌现约束：声明第二个机柜 | instance-declaration | medium |
| 32 | `telecom-emergent-003` | 涌现约束：部署存储节点 | comprehensive | medium |
| 33 | `telecom-emergent-004` | 涌现约束：遵循 U 位间隔惯例 | layout-design | medium |

Table: Complete task list for SD-HWE-Bench v3. {#tbl:task-list}

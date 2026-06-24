<!-- markdownlint-disable MD041 -->
<!--
# 04 Pml
位置：第 5.3 节 PML：部件装配语言
字数：约 173 词
目标：正文
-->

PML 描述 Part 之间的关系，并区分两类：**Mate** 和 **Connection**。这一区分记录在 ADR-005 和 ADR-006 中，并在 `adl/src/adl/models/mating.py` 和 `src/piki/core/engine/checker.py` 中实现。

**Mate** 表达设计耦合：它约束两个 Part 如何配合或协同工作。Mate 是 `mates/<mate_type>/` 中的独立 YAML 文件。例如，`samples/01-telecom-expansion/mates/rack-mount/RACK-A02-SRV-01.yaml` 声明：

```yaml
type: rack-mount-19inch
parent: RACK-A02
child: SRV-01
at:
  u_start: 10
  u_span: 2
constrains:
  - field: depth_mm
    operator: "<="
    value_ref: depth_mm
```

引擎在加载时校验这些约束。电信插件中的其他 Mate 类型包括 `sfp28-cage`、`power-iec-c14-c13` 和 `lc-connector`；所有插件共注册了 33 种 Mate 类型。

**Connection** 表达两个 Interface 之间的信号、能量或物质流。Connection 本身是一等 Instance。在 `samples/01-telecom-expansion/instances/port_connections/CONN-ACCESS-SRV01.yaml` 中：

```yaml
id: CONN-ACCESS-SRV01
family: PortConnectionFamily
from_port: ACCESS-SW-01/10GE1/0/1
to_port: SRV-01/eth0
cable_type: OM4-LC-LC
```

Mate/Connection 的拆分直接对应两个独立的设计阶段：机械或电气可行性（Mate）和功能拓扑正确性（Connection）。CAD/BIM 通常将它们合并到一个对象中，这使得无法在不涉及另一阶段的情况下验证其中一个阶段。

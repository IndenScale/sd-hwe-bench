<!-- markdownlint-disable MD041 -->
<!--
# 03 Pdl
位置：第 5.2 节 PDL：部件定义语言
字数：约 205 词
目标：正文
-->

PDL 通过三个层次定义 Part 类型系统：**Family**、**Model** 和 **Instance**。这一层次结构是 ADL 存在层在 piki 中的实现，并在 `piki/docs/concepts/01-core-concepts.md` 中说明。

**Family** 是一个 pydantic `BaseModel` 类，声明某类 Part 的 schema 和值约束。例如，`src/piki/extensions/telecom/plugin.py` 中的 `ServerFamily` 要求 `id`、`height_u`（1–48）、`tdp_w`（>0）以及 `Interface` 规范列表。Family 由插件注册；它们是代码，而非配置。

**Model** 为 Family 提供具体默认值。在 `samples/01-telecom-expansion/models/devices/dell-r750.yaml` 中：

```yaml
model: dell-r750
family: ServerFamily
brand: Dell
mpn: PowerEdge R750
height_u: 2
tdp_w: 600
psu_count: 2
```

**Instance** 是一个已部署实体，可以覆盖 Model 的默认值。在 `samples/01-telecom-expansion/instances/devices/SRV-01.yaml` 中：

```yaml
id: SRV-01
model: dell-r750
family: ServerFamily
status: planned
```

在运行时，解析值按 `Model.defaults + Instance.overrides` 计算，然后针对 Family schema 进行校验。Instance 的 `id` 派生自文件名（`SRV-01.yaml` → `SRV-01`）。

一项关键设计决策是 **Instance 文件不包含布局信息**。位置、机架和 U 高在 PLL（`layouts/layout.yaml`）中单独声明。这种身份与空间的分离意味着同一设备可以放置在不同位置，而无需复制其定义，这对于基于分支的方案比较至关重要。

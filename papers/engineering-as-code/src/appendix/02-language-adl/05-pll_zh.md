<!-- markdownlint-disable MD041 -->
<!--
# 05 Pll
位置：第 5.4 节 PLL：部件布局语言
字数：约 200 词
目标：正文
-->

PLL 解析 PDL 声明 Part 且 PML 声明其耦合之后剩余的空间自由度（DoF）。它的作用不是执行任意几何约束求解，而是为设计的自由变量赋值。当前 PLL 模型由 ADR-013（`docs/adr/data-model/013-relative-coordinate-layout.md`）定义。

PLL 以两种模式运行。在**紧耦合装配**中，PLL 提供 PML 约束的参数补全。例如，`rack-mount-19inch` Mate 将 U 位留空；PLL 通过 `at.u_start` 或等价的 `LayoutEntry` 赋值：

```yaml
- instance: SRV-01
  rack_id: RACK-A02
  position_u: 10
```

在**松耦合或顶层装配**中，PLL 使用绝对或相对坐标系。绝对条目设置 `position_x_mm`、`position_y_mm`、`position_z_mm`；相对条目设置 `parent` 加上一个 `transform`，其中包含 `translation` 和 `rotation`（以度为单位的 Z-Y-X 欧拉角）。这两种模式在同一个 `LayoutEntry` 中互斥，并由 `adl/src/adl/validation/validator.py` 中的 `ADLValidator._validate_relative_layout()` 校验。

当前 PLL 实现存在已知边界。它支持离散坐标（机架 U 位、网格轴）和简单连续变换，但尚未解决复杂参数装配（例如连续 3D HVAC 布线或闭环机械连杆）或完整 3D 约束网络。这些留给未来扩展和外部 CAE 工具处理。

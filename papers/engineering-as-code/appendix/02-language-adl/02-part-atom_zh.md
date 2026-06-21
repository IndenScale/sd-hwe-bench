<!-- markdownlint-disable MD041 -->
<!--
# 02 Part Atom
位置：第 5.1 节 Part 作为工程原子
字数：约 246 词
目标：正文
-->

在 ADL 中，**Part** 是工程描述的原子单位。Part 不仅仅是一个几何实体；它是一个语义完整的实体，暴露类型化接口并参与显式关系。从形式上看，一个 Part 由类型定义（Family）、属性约束、一组 `Interface` 规范以及可选的内部几何包络组成。其含义既由自身字段决定，也由它与其他 Part 之间的 `Mate` 和 `Connection` 关系决定。

Part 抽象建立在四项属性之上：

1. **语义完整性。** Part 携带显式的功能身份。服务器 Part 被类型化为 `ServerFamily`，包含 `height_u`、`tdp_w`、`psu_count` 等字段；水泵 Part 则会携带 `flow_rate` 和 `head`。类型检查由插件注册的 pydantic schema 执行（`src/piki/extensions/telecom/plugin.py`）。
2. **封装性。** 内部几何被隐藏，除非需要进行高保真分析。只有标准化的 `Interface` 点对外可见，因此下游消费者通过狭窄、类型化的契约与 Part 交互。
3. **关系内在性。** Part 在装配中的角色通过关系表达。服务器是 `rack-mount-19inch` Mate 中的 `child`；收发器是 `sfp28-cage` Mate 中的 `child`；光纤是两个端口之间的 `Connection`。
4. **多视图投影。** 同一个 Part 可以投影到 CAD（USD/glTF）、CAE（热或结构模型）、ERP（BOM 条目）和 PM（生命周期目录），而无需修改其核心声明。

电信样本中的具体示例包括 `RACK-A01`（`RackFamily`）、`SRV-01`（`ServerFamily`）和 `XC-SRV01-ETH0`（`TransceiverFamily`）。它们都是 Part；其装配在 `mates/` 中单独定义。

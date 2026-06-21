<!-- markdownlint-disable MD041 -->
<!--
# 08 Adl Formal Syntax
位置：第 5.7 节或附录 A — ADL 核心语法摘要
字数：约 241 词
目标：附录（或紧凑正文框）
-->

以下语法总结了 ADL 在 piki 中的核心构造。它作为希望了解精确语法边界的读者参考；权威解析器是 `adl/src/adl/parsing/` 中的 YAML 加载链。

```text
Project       ::= piki.toml (ModelFile | InstanceFile | MateFile | LayoutFile | CatalogFile)*

ModelFile     ::= "model:" id
                  "family:" FamilyName
                  Field*
                  ("interfaces:" InterfaceSpec*)?

InstanceFile  ::= "id:" id
                  ("family:" FamilyName | "model:" ModelName)
                  Field*
                  ("interfaces:" InterfaceSpec*)?

InterfaceSpec ::= "- id:" id
                  "interface_type:" Type
                  ("direction:" "input" | "output" | "bidirectional")?
                  ("local_transform:" Transform)?

MateFile      ::= "type:" MateType
                  "parent:" Ref
                  "child:" Ref
                  ("at:" Map)?
                  ("constrains:" MateConstraint*)?
                  ("pairings:" InterfacePairing*)?

MateConstraint::= "- field:" Field
                  "operator:" "<=" | ">=" | "<" | ">" | "==" | "!="
                  "value_ref:" FieldOrConstant
                  ("message:" String)?

LayoutFile    ::= LayoutEntry*
LayoutEntry   ::= "- instance:" id
                  (AbsolutePose | RelativePose | GridPose)

AbsolutePose  ::= ("position_x_mm:" num)+
RelativePose  ::= "parent:" id
                  "transform:" Transform
GridPose      ::= "grid_id:" id
                  ("grid_position:" [String, String]
                  | "row_id:" String "bay_index:" Int)

Transform     ::= "translation:" [num, num, num]
                  ("rotation:" [num, num, num])?
                  ("scale:" [num, num, num])?

Ref           ::= id | id "/" interface_id
```

语法未捕获的关键语义约束：`InstanceFile` 不得包含布局字段；`LayoutEntry` 必须且只能使用绝对、相对或网格位姿中的一种；`Mate` 约束在加载时由 `ADLValidator._validate_mate_constraints()` 评估；`Ref` 中的接口引用必须解析为存在的 `Interface`（FK-001）。完整类型系统（包括六个内置插件中注册的 32 个 Family 和 33 个 Mate 类型）参见 `src/piki/extensions/` 和 `adl/src/adl/compiler/type_registry_builtins.py`。

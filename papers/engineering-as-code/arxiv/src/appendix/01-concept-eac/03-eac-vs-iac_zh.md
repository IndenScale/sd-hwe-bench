<!-- markdownlint-disable MD041 -->
<!--
# 03 Eac Vs Iac
位置：附录 I-C — EaC 与 Infrastructure as Code 的关系
字数：约 360 词
目标：附录
-->

# EaC 与 Infrastructure as Code 的关系

Infrastructure as Code（IaC）通过 Terraform、Ansible 等工具将基础设施配置从手工操作迁移到可版本化、可测试的代码层面 [@morris2022iac; @quattrocchi2023iacsurvey]。IaC 已经发展为一个成熟的研究领域，拥有关于测试、静态分析与幂等性验证的成体系实践 [@quattrocchi2023iacsurvey]。Chiari 等人对 IaC 静态分析工具的实证研究表明，tfsec、checkov 等工具可以在数秒内检测出数百项安全与合规违规，证明“X as Code”基础上的静态分析既可行又高效 [@chiari2024iacstatic]。

EaC 将 IaC 的逻辑推广到更广泛的物理工程系统设计，但两者之间存在一个关键差异：**IaC 描述的是已经数字化的基础设施状态，而 EaC 必须首先将物理世界抽象为可计算的设计描述**。云服务器、网络拓扑、容器镜像等基础设施对象天然存在于数字空间中；而机架、服务器、泵阀、结构构件等工程对象则首先存在于物理空间中，需要被人为地定义类型、接口、关系与布局，才能成为机器可消费的声明。

下表从七个维度对比两者：

| 维度 | Infrastructure as Code | Engineering as Code |
|---|---|---|
| 事实来源 | Terraform / Ansible 文件 | ADL 声明文件 |
| 校验方式 | `terraform plan`、CI 测试 | `piki check`、ESA |
| 协作单元 | Git PR、代码审查 | AssemblyHub PR、netlist 合并 |
| 资产复用 | npm / PyPI | EPM（Engineering Package Manager） |
| 原子单元 | 资源 / 服务实例 | Part（部件） |
| 空间维度 | 通常无关或次要 | 核心关切（布局、碰撞、自由度） |
| 目标 | 基础设施可重复、可审计 | 工程设计可校验、可复现、可自动化 |

基于上表，可以把 EaC 理解为 **IaC 的泛化**：IaC 处理的是“已经代码化的世界”，EaC 处理的是“尚未代码化、需要先被数字化的物理世界”。因此，EaC 不仅需要 VCS 和规则引擎，还需要一门专门的语言（ADL）来描述物理对象的类型、装配关系与空间布局；不仅需要包管理器分发代码，还需要分发带有工程语义的 Part 库和规则库。

这一泛化也解释了为什么 EaC 的挑战比 IaC 更大：基础设施的语义边界相对清晰（一台虚拟机要么存在要么不存在），而工程对象的语义边界需要领域专家共同约定（一个“服务器”应当暴露哪些接口、一个“机架”应当支持哪些 Mate 类型）。因此，EPM 与社区治理机制在 EaC 中的重要性，不低于语言与工具本身。

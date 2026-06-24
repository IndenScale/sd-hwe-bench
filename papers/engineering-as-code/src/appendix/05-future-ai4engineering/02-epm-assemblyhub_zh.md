<!-- markdownlint-disable MD041 -->
<!--
# 02 Epm Assemblyhub
位置：附录 V-B — EPM 与 AssemblyHub
字数：约 360 词
目标：附录
-->

# EPM 与 AssemblyHub：社会技术基础设施

ADL 与 ESA 构成 EaC 的技术核心，但其规模化部署需要社会技术基础设施。我们提出两个核心组件：EPM（Engineering Package Manager）与 AssemblyHub。

## EPM：工程包管理器

EPM 是面向 Part 库、Mate 类型库、规则库与生成器的包管理器，类比软件工程中的 npm 或 PyPI。其核心功能包括：

| 功能 | 说明 | 类比 |
|---|---|---|
| 发现 | 按领域、标准、版本搜索 Part 与规则包 | npm search |
| 安装 | 将依赖解析到项目本地 | npm install |
| 版本控制 | 语义化版本（SemVer）、依赖锁定 | package-lock.json |
| 签名与认证 | 权威机构对安全关键 Part 进行数字签名 | PyPI 签名 |
| 复用审计 | 追踪 Part 在项目间的使用历史 | SBOM |

EPM 中的“包”不仅是代码，还包含工程语义：一个 Part 包需要说明其适用的标准、接口规范、Mate 类型、测试覆盖率以及已知限制。例如，一个 `ServerFamily` 包可能需要附带温度降额曲线、重量分布数据和接口引脚定义。

## AssemblyHub：协作平台

AssemblyHub 是面向 EaC 的协作平台，以 ADL netlist 管理为核心，支持分支、合并、审查与自动化 ESA 检查。其关键特性包括：

- **语义差异**：由于 ADL 的正交性，`instances/`、`mates/`、`layouts/` 的 diff 分别对应身份、关系、空间三种变更，审查者可聚焦于相关工程维度；
- **netlist 合并**：与 CAD 文件合并不同，ADL 文件是文本，Git 的三向合并可直接应用，冲突通常局限于同一决策维度；
- **自动化 ESA 门禁**：PR 提交时自动运行 `piki check`，ERROR 级别诊断阻止合并；
- **自托管部署**：考虑到工程数据主权与安全要求，AssemblyHub 必须原生支持私有化部署。

## 治理模型

EPM 与 AssemblyHub 的治理可借鉴开源软件社区：

- **核心规则**：由行业协会或国家标准机构维护，确保权威性与稳定性；
- **领域规则**：由企业或专业社区贡献，通过 PR 与审查机制迭代；
- **Part 库**：由设备厂商、设计院或第三方维护，版本化发布；
- **生成器**：由工具厂商或领域专家贡献，支持多种下游格式（BOM、施工图、仿真输入）。

## 当前状态

EPM 与 AssemblyHub 目前仅处于概念设计阶段，尚未实现。它们是 EaC 从原型走向工业化的必要基础设施，但超出了本文的技术验证范围，因此作为未来工作简述。

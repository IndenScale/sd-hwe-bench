<!-- markdownlint-disable MD041 -->
<!--
# 03 Precommit Gate
位置：附录 IV-C — Pre-commit 门禁
字数：约 360 词
目标：附录
-->

# Pre-commit 门禁

Pre-commit 是在代码提交前本地执行的钩子集合，目的是在缺陷进入共享仓库之前拦截它们。在 EaC 中，pre-commit 同样适用于 ADL 声明：工程师在本地即可获得与 CI 一致的快速反馈，避免“提交 → 等待 CI → 修复 → 再提交”的长循环。

## Pre-commit 的组成

一个 EaC 项目的 pre-commit 配置通常包含三类钩子：

### 1. 通用文本钩子

- 尾随空白清理
- 文件末尾空行检查
- YAML/TOML 语法校验
- 行尾统一（LF / CRLF）

这些钩子不依赖领域知识，但能保证 ADL 文件在解析前具备一致的格式。

### 2. ADL 加载钩子

- **L0 解析检查**：确保所有 YAML 文件可被 ADL 解析器加载；
- **L1 Schema 检查**：验证字段类型、值域与必填项；
- **L2 引用完整性**：验证 Instance、Mate、Connection 之间的引用可解析。

这些检查通常在亚秒级完成，适合作为提交前快速反馈。

### 3. ESA 规则钩子

- **L3 业务规则**：功率预算、承重、容量、接口兼容性；
- **L4a 快速几何规则**：U 位冲突、AABB 碰撞、维护通道宽度。

由于完整规则检查可能需要数百毫秒到数秒，项目可以配置为：

- **默认启用**：对小型项目或关键路径规则始终运行；
- **按需启用**：通过 `--staged` 只对本次提交涉及的文件运行；
- **CI 延后**：将完整规则检查留给 CI，本地只运行最快的一层。

## 本地与 CI 的一致性

Pre-commit 与 CI 应共享同一套校验逻辑和配置文件（例如 `pyproject.toml` 或 `.eac.toml`）。这避免了“本地通过、CI 失败”的不一致问题。理想情况下，pre-commit 调用的命令与 CI 命令完全相同，只是作用范围更小（暂存文件 vs. 整个仓库）。

## 提交信息规范

为了支持设计变更的审计与豁免追踪，建议对 EaC 提交信息采用结构化格式：

```text
type(scope): short description

- rule-impact: TELECOM-POWER-001, TELECOM-RACK-001
- waiver: none
- downstream: none
```

其中 `rule-impact` 字段帮助审查者快速识别本次变更影响的规则；`waiver` 字段关联任何必要的豁免记录；`downstream` 字段记录是否需要触发 CAE/CFD 等后续验证。

## 价值

Pre-commit 的核心价值在于**缩短反馈循环**。在软件工程中，lint 与类型检查能在提交前拦截大量低价值错误，使代码审查聚焦于架构与逻辑 [@chiari2024iacstatic]。在 EaC 中，pre-commit 同样能让工程师在编写 ADL 声明时即时发现接口不匹配、U 位冲突等问题，而不是等到 PR 审查或夜间回归才暴露。

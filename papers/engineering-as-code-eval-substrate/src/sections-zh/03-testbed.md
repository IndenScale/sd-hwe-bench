# 3. EaC Substrate 的当前实现：SD-HWE-Bench

本文使用 SD-HWE-Bench 不是为了单独介绍一个 benchmark，而是为了给 Engineering as Code evaluation substrate 一个可运行的实现。它提供四个关键能力：可提交的工程状态、可执行的分层 critic、可复现的任务增量和可观察的 failure mode。

## 3.1 ADL：工程状态作为可提交对象

EaC 的第一层是 ADL，即一种面向系统级工程的声明式设计语言。ADL 用工程对象、属性、引用、连接、配合、布局、调度和交付物表达设计状态，使 agent 的输出不再是一段自然语言方案，而是一个可提交、可 diff、可评分的工程 patch。

这种提交对象与普通配置文件不同。它需要保留工程语义：设备和端口可以被引用，连接和配合可以被检查，位置和几何可以被约束，资源和活动可以进入排程，交付物可以被 critic 验证。ADL 无意覆盖所有工业软件能力；它在 agent evaluation 中承担的是稳定语义接口。

## 3.2 DTS：正确性作为分层可执行 critic

EaC 的第二层是 DTS 分层约束系统。DTS 将工程正确性拆分为多个可执行层：

- L0：语法和文件格式。
- L1：schema 与类型。
- L2：引用完整性。
- L3：静态工程约束，例如功率、接口、载荷和规则断言。
- L4：动态模型、调度仿真或多方案决策。
- L5：几何干涉、空间约束和施工可建性。
- L6：预留高精度 FEM/CFD 等仿真。

这种分层使错误不只是 pass/fail，而能被归因到约束类别、对象和文件位置。它为 repair loop、错误模式分析、诊断粒度实验和 RLVR 奖励设计提供统一信号。

## 3.3 Canonical Lineage：任务作为工程增量

SD-HWE-Bench 从 canonical 工程的 commit 历史中提取任务。每个任务可以理解为一个真实工程增量：给定某个设计状态和需求，agent 需要提交下一个状态的工程 patch。canonical lineage 保留了 scaffold、solution 和任务说明之间的一致性，避免手写任务在多阶段演进中产生内容漂移。

AIDC 60MW reference domain 采用 lineage 化 canonical，将概念设计、详细设计和 EPC 排程组织为同一工程仓的连续 tag。后一阶段物理包含前一阶段，使设计状态、施工状态和运营状态共享单一事实源。这一点对 evaluation substrate 很关键：如果任务之间的真相源漂移，agent 失败就无法被稳定归因。

## 3.4 Actor Isolation：评估作为可审计运行

工程 agent 评估还需要保证提交过程本身可信。SD-HWE-Bench 将 actor 工作区迁出仓库，并在 macOS 上使用 seatbelt 对参考解、canonical、runs 和 leaderboard 进行内核级读取隔离。agent 只能看到 scaffold 和任务说明，评分后产物再归档回 runs。

这样，pass/fail 取决于 agent 在隔离工作区内生成的工程提交，而不受“是否偶然读到参考答案”影响。对于 NeurIPS E&D 这类重视 artifact validity 的场景，隔离、归档和可复现运行属于 evaluation substrate 的组成部分，不能当作普通工程细节处理。

## 3.5 本文如何使用该平台

本文不把任务数量作为主要论据，而把 SD-HWE-Bench 用于受控对照：

1. 在同一工程意图上比较不同表征路径是否能形成可复现评估闭环。
2. 在同一任务池上比较自然语言规范、文档规范和可执行 DTS 的行为差异。
3. 在 AIDC 场景中比较静态合规、局部优化和设计-调度联合优化的上限差异。

这种用法使小规模但高耦合的任务集仍然具有解释力：我们关心的是 evaluation substrate 的因果结构，而非仅凭任务数量证明覆盖面。

## 3.6 Evaluative Claims 与 Artifact Contract

为了避免把 substrate 论文误读为普通 benchmark 排行榜，本文显式限定可支持的评估主张。主文应反复回到三条可验证 claim，而不是依赖“工程 agent 需要 substrate”这一不可直接检验的总判断。

**本文试图支持的三条主张**包括：

- **Representation claim**：提交对象和表征接口会改变 repair loop 的稳定性、反馈延迟、错误定位粒度和可复现性。
- **Constraint claim**：可执行约束和局部诊断会降低 pseudo-correctness、遗漏密度和 repair saturation，并改变 failure attribution。
- **Knowledge claim**：在 AIDC probe 中，可优化知识可以改变可行解之间的 TCO/PUE/SLA tradeoff；如果 frontier shift 不显著，也应报告为受任务可行域、设备库或优化器能力限制的 evaluation finding。

这些主张成立的前提是 artifact 真实可运行、可隔离、可归档、可诊断。换言之，artifact 不是事后补充材料，而是 E&D submission 的证据主体。

**本文不试图支持的主张**包括：

- ADL 已经替代 CAD/BIM/PLM/EDA 等工业工具链。
- 当前任务集已经覆盖全部系统级工程领域。
- 当前模型在真实工业 AIDC 设计中达到可部署水平。
- AIDC probe 的所有设备价格、供应链、故障率和施工风险已经等同于真实商业项目。

正式 artifact 应包含六类对象。第一，任务与数据：task.yaml、scaffold、solution、canonical lineage、AIDC 设备/气候/电价/成本参数，以及相应 task card、data card 和 license。第二，执行入口：顶层 README、安装命令、quickstart、smoke test 和 expected output。第三，执行环境：容器、依赖锁定、CLI、actor isolation 设置和复现实验矩阵。第四，评分与诊断：DTS critic、L0-L6 层输出、repair trajectory、pseudo-correctness 标注协议和 omission taxonomy。第五，结果归档：runs、manifest、actor_output、score artifacts、leaderboard 与生成论文表格的脚本。第六，E&D 元数据：匿名化托管说明、reviewer 30-minute reproduction path、full reproduction path，以及 dataset/benchmark 适用的 Croissant core 与 Responsible AI metadata [Akhtar et al., 2024; NeurIPS E&D, 2026]。

后文实验表格由 `src/data/eval-substrate.yaml` 通过 Jinja2 渲染。当前数据模式：**{{ data.eval_substrate.artifact.result_label }}**。{{ data.eval_substrate.artifact.result_note }}

正式投稿版只允许使用可由上述 artifact 重建的数字；趋势性分析也必须能回溯到具体 run、任务、模型、条件和评分层。若某个实验轴无法按时完成，应在正文中降级为 protocol 或 future work，而不是保留模拟数据。

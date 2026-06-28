# 术语表

| 缩写 | 全称 | 定义 | 所在章节 |
|------|------|------|---------|
| **EaC** | Engineering as Code | 将工程设计表达为文本原生的声明式语言，以自动规则引擎、版本控制与包管理作为质量门与协作基座的范式 | §1.4, §3.1 |
| **ADL** | Assembly Definition Language | EaC 的声明式领域特定语言，通过 PDL/PML/PLL 三层正交子语言统一描述多物理域设计 | §3.1.1 |
| **PDL** | Part Definition Language | ADL 子语言：定义部件类型——端口、属性、兼容性约束 | §3.1.1 |
| **PML** | Part Mating Language | ADL 子语言：定义部件间关系——电气连接、物理配合、层级包含 | §3.1.1 |
| **PLL** | Part Layout Language | ADL 子语言：定义部件空间布局——位置、方向、布局约束 | §3.1.1 |
| **Part** | — | EaC/ADL 的设计原子，对应物理工程中的一个可实例化部件（交换机、PDU、机架等） | §3.1.1 |
| **DTS** | Design Test Suite | EaC 的分层确定性评分引擎，从 L0 到 L5 逐层检查设计正确性，等价于工程领域的 QA 套件 | §3.1.2, §5.1 |
| **ASA** | Assembly Static Analysis | DTS 的 L3 层：对物理装配体做不施加激励的静态断言——功率预算、U 位冲突、端口兼容性、散热间距等 | §5.1.4 |
| **ADA** | Assembly Dynamic Analysis | DTS 的 L4 层：施加虚拟激励 → 观察系统响应 → 阈值判断——防火、承重、碰撞、软碰撞、电压降等 | §5.1.5 |
| **piki** | — | EaC 范式的开源参考实现，提供 ADL 解析、DTS 检查与交付物生成 | §3.1.3 |
| **Canonical 工程** | — | 由领域专家精心构建的完整 ADL 工程，其 commit 历史模拟真实设计迭代，作为任务提取的源 | §3.3.2, §4.2 |
| **ACC** | Automated Compliance Checking | 现有事后合规检查路径：从已完成的几何模型中逆向推断合规性，假阳性高、依赖命名约定 | §1.3, §3.1.2 |
| **Pass@k** | — | 每个任务独立执行 k 次，至少 1 次通过即视为 resolved 的评测指标，按无偏估计计算 | §5.3.2 |
| **Repair Loop** | — | Agent 首轮失败后获得 DTS 错误报告，迭代修复最多 R 轮的协议 | §5.5 |
| **RLVR** | Reinforcement Learning with Verifiable Rewards | 利用确定性可验证奖励信号进行强化学习的训练范式 | §1.2 |
| **HWE** | Hardware Engineering | 硬件工程：区别于软件工程的物理工程设计领域，涵盖电信、数据中心、机械等子领域 | §1.3 |
| **SWE** | Software Engineering | 软件工程：以文本源代码为核心工件的工程领域，其"可计算表示 + 执行评测"范式是 SD-HWE-Bench 的方法论来源 | §1.3 |

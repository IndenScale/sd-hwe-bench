# SD-HWE-Bench 评分规则

> 最后更新：基于 `src/sd_hwe_bench/scorer.py` 和 `settings.py` 的实际实现。

---

## 1. 评分层总览

SD-HWE-Bench 对每个 Agent 输出运行多层 Critic，从文本格式到物理行为逐层递进。所有带编号的层都是**确定性 QA 层**；性能优化分数、Rubric、交付物生成等不再占用层号。

| 层 | 名称 | 检查内容 | 权重 | 是否 Critical |
|----|------|---------|------|--------------|
| L0 | Syntax | YAML 语法、expected_files / expected_deliverables 存在性 | 0% | ✅ |
| L1 | Schema | 字段类型、值域、必填字段 | 10% | ✅ |
| L2 | Reference Integrity | ID 唯一、外键/端口/接口/配合/目录引用完整且类型兼容 | 15% | ✅ |
| L3 | Static Engineering Constraints | 功率预算、U 位冲突、静态工程约束 | 40% | ✅ |
| L4 | Reduced-Order Dynamic Model | 降阶动态仿真（AIDC 热/电仿真、硬约束断言） | 15% | ✅ |
| L5 | Geometry Interference & Error Analysis | 几何碰撞、rack 空间、误差分析 | 20% | ✅ |
| L6 | FEM/CFD High-Fidelity Simulation | 高保真仿真（预留，本次未实现） | 0% | — |
| — | Deliverable Generation | `piki generate` 产出期望交付物 | 0% | ✅ |
| — | Performance Score | 相对 baseline/reference 的优化改善分数 | 0% | ❌ |
| — | Rubric | LLM-as-judge 语义评估 | 0% | ❌ |

**关键变化（v6 重构）**：

- L2 不再拆分为 a/b/c，统一为引用完整性层。
- L4 接管原 `L7-Performance` 的 AIDC 仿真合规检查；优化分数变为独立诊断指标。
- L5 接管原 L4 的几何/碰撞规则。
- L6 预留给未来 FEM/CFD，权重为 0。
- 交付物检查是 L0 的延伸（预期输出必须存在），不再叫 L5/L6。

---

## 2. Critical Layers 与 Pass/Fail 判定

**Pass 条件**：所有 Critical Layer 必须通过，且所有 expected deliverables 必须产出。

Critical Layers 默认列表：`L0, L1, L2, L3, L4, L5`

交付物缺失视为生成/编译失败，导致任务 FAIL，但不贡献 overall_score。

---

## 3. Overall Score 计算公式

```text
overall_score = sum(LAYER_WEIGHTS[layer] × passed_for_layer)
```

其中 `passed_for_layer` 为 0 或 1（该层是否全部规则通过）。

**默认权重**：

| 层 | 权重 | 累计 |
|----|------|------|
| L0 | 0.00 | 门槛 |
| L1 | 0.10 | 10% |
| L2 | 0.15 | 25% |
| L3 | 0.40 | 65% |
| L4 | 0.15 | 80% |
| L5 | 0.20 | 100% |

若某任务未启用某层（如非 AIDC 任务不包含 L4），则该层权重不计入，overall_score 按实际启用层归一化理解即可。

---

## 4. AIDC 任务评分

AIDC 任务（`task_type = operation` 或 `co-design`）的 L4 由 `PerformanceCritic` 执行：

1. 从 workspace 读取 Agent 修改的 `rooms/*.yaml` 和 `strategy.yaml`。
2. 用 `AIDCSimulator` 按分时电价、湿球温度运行 48h 仿真。
3. **硬约束检查**（决定 L4 pass/fail）：
   - 室内温度 ≤ 32°C
   - PUE ≤ 任务给定目标（如 co-design 任务 PUE ≤ 1.22）
   - SOC 无过低违规
4. **性能诊断分数**（`performance_score`）：
   - 对比 `baseline`（scaffold 默认策略）和 `reference`（人工强参考）。
   - `score = clip((baseline - agent) / (baseline - reference), 0, 1)`
   - 仅用于排行榜区分度，**不计入 overall_score，也不决定 pass/fail**。

任务 `task.yaml` 的 `l7_config.constraints`（或未来 `l4_config.constraints`）显式定义硬约束。

---

## 5. 按任务类型的评分差异

### 5.1 声明型任务（instance / layout / connection / mating）

- `scoring_layers`: L0-L2 或 L0-L3
- 无 L4/L5
- 无 deliverable
- pass 条件：L0-L2（或 L0-L3）全部通过

### 5.2 综合型任务（comprehensive / rack / dc / site / cross / emergent）

- `scoring_layers`: L0, L1, L2, L3, L5
- 有 deliverable（BOM、power-budget、port-map、rack-panel、cable-list 等）
- 数值断言归入 L3
- pass 条件：L0-L3、L5 全过 + 交付物齐全

### 5.3 AIDC 任务（operation / co-design）

- `scoring_layers`: L0, L1, L2, L3, L4
- 无 deliverable
- L4 为仿真硬约束
- pass 条件：L0-L4 全过

---

## 6. Pass@k 计算

```text
Pass@k = 1/k × sum(pass_i for i in top-k attempts)

where pass_i = 1 if ALL critical layers pass AND deliverables齐全, else 0
```

Leaderboard 主指标为 pass@1。

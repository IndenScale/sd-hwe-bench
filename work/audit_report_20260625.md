# SD-HWE-Bench 轨迹审计报告

生成时间：2026-06-25
实验数据：
- Kimi: `runs/full-pass-20260625/` (19 tasks × 5 passes)
- DeepSeek v4 flash: `runs/deepseek-v4-flash-20260625-fixed/` (19 × 5)
- DeepSeek v4 pro: `runs/deepseek-v4-pro-20260625-fixed/` (19 × 5)

## 1. Leaderboard 汇总

| Model | Pass@1 | Avg Score |
|---|---|---|
| kimi | 100% | 87% |
| deepseek-v4-flash | 84% | 81% |
| deepseek-v4-pro | 81% | 79% |

## 2. 关键发现

### 2.1 任务设计缺陷：telecom-rack-002

**现象**：Kimi 100% 通过，Flash 0%，Pro 20%。

**根因**：任务 requirement 未明确指定 PDU 字段名和机柜关联字段。

- Solution 使用：`capacity_w: 2000` 和 `rack_id: RACK-A01`
- Flash/Pro 输出：`power_capacity_w: 2000`（无 `rack_id`）
- piki PduFamily schema 要求字段为 `capacity_w`
- 结果：L1 schema 校验失败

**结论**：这是任务 requirement 的歧义导致。模型选择 `power_capacity_w` 在语义上合理，但与 schema 不符。

**建议修复**：在 `telecom-rack-002/task.yaml` 的 requirement 中明确：
- 使用字段 `capacity_w: 2000`
- 包含 `rack_id: RACK-A01`

### 2.2 任务设计/模型能力交界：instance-declare-001

**现象**：Kimi 100%，Flash 20%，Pro 0%。

**根因**：任务要求声明多个设备并分配机柜 U 位，但 requirement 未明确说明 2U 设备需要占用连续 2U 且不能重叠。

- Solution layout：SRV-01@10, SRV-02@14, SW-01@20（间隔充足）
- Flash layout 示例：SRV-01@10, SRV-02@12, SW-01@14 → 2U 设备间产生空间冲突
- piki L4 检查报 `TELECOM-COLLISION-001`

**结论**：部分属于模型对机柜空间约束理解不足，部分属于任务 requirement 可以加强。建议明确 U 位分配规则。

### 2.3 模型能力差异

| 维度 | Flash | Pro | Kimi |
|---|---|---|---|
| 简单 canonical 任务 | 稳定 100% | 稳定 100% | 100% |
| connection-design | 60% | **100%** | 100% |
| comprehensive | 20% | 0% | 100% |
| 跨文件引用一致性 | 中等 | 中等 | 强 |
| 机柜 U 位空间规划 | 较弱 | 较弱 | 强 |

### 2.4 共同失败模式

Flash 失败模式：
- L2 引用错误：13 次
- L3 约束违规：8 次
- L1 schema 错误：5 次

Pro 失败模式：
- L2 引用错误：14 次
- L3 约束违规：12 次
- L1 schema 错误：5 次

两者在 L2/L3 上失败最多，说明跨文件引用和工程约束检查是主要难点。

## 3. 建议

1. **修复 telecom-rack-002 的 requirement**，消除字段名歧义。
2. **加强 instance-declare-001 的 requirement**，明确 U 位分配规则。
3. **检查其他 canonical 任务**是否有类似字段名歧义（如 `capacity_w` vs `power_capacity_w`）。
4. **考虑增加 repair 循环效果**：当前 self-check engagement 平均 < 0.5 轮，说明自动修复未充分参与。
5. **对 comprehensive-001 进行专项 audit**，分析多文件一致性失败的具体模式。

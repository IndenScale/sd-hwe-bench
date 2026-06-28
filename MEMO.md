# SD-HWE-Bench 开发备忘录

最后更新：2026-06-27（v2 改进完成）

## v2 改进记录（2026-06-27）

### 诊断结论

- **区分度不足三重根因**：① 约束太明确（涌现约束缺失）② Scaffold `power_capacity_w` 字段污染 ③ easy 任务依赖链太浅（1-2 层）
- **CLI Actor pass@1=100%**，区分度完全来自 Actor 类型差异
- **L2 单层过载**：16 条规则→1 层，一个字段错误导致 L1+L2+L3 连锁失败

### 改进措施

1. **Prompt 增强**（`prompts.py`）
   - 新增 PDU 实例 quick reference
   - 显式警告 `capacity_w` vs `power_capacity_w` 陷阱
   - 强调 `rack_id` 必填

2. **L2 拆分**（`rule_layers.yaml` + `settings.py` + `piki.py` + `scorer.py`）
   - L2a: REFS-*, FK-*, TELECOM-FK-*, TAGS-*（5 条，5%）
   - L2b: INTERFACE-*, TELECOM-PORT-*, TELECOM-CONN-*（7 条，5%）
   - L2c: MATE-*, CATALOG-*（4 条，5%）

3. **新增 12 个任务**（34→46）
   - 5 个复合 easy：递增依赖链，设备→端口→光模块/光纤→配合→电源
   - 4 个涌现约束：命名规范推断、必填字段推断、物理约束推断、U 位间隔推断
   - 3 个跨专业综合：地板载荷、散热约束、供电冗余

4. **难度重标定**
   - easy 50%→39%，medium 38%→46%，hard 12%→15%
   - 7 个原 easy 升级为 medium

### 待办

- [ ] 重跑 46-task 全量实验（含 L2a/L2b/L2c 分层评分）
- [ ] pass@5 + repair ablation
- [ ] 论文 B 英文版翻译
- [ ] 论文 A FSE 缩写版

## 历史记录

### 2026-06-27（34-task 实验完成）

- 34 个任务全量 piki check 通过；Kimi/DeepSeek Flash/Pro pass@1 leaderboard 生成
- Actor Gap 发现：CLI 系统性优于 API（+10-20pp）
- 论文 B 中文初稿更新至 34 任务

### 2026-06-14（M2 完成）

- 34 个任务提取完成，3 个 canonical 工程就绪
- 容器化就绪，4 种 Actor 全部实现

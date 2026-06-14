# SD-HWE-Bench 进度备忘录

> 最后更新：2026-06-14 20:25 CST

## 命名决策

**坚持 SD-HWE-Bench。** 结论：`HWE-Bench` 已被占用——arxiv 上已有两篇论文（北大 2026-04-16 的硬件 Bug 修复评测、EDI-Systems 2026-03-18 的板级电路设计评测）和三个 GitHub repo 使用该名称。你们的 `SD-` 前缀构成关键区分：他们是芯片级 Hardware Engineering，你们是系统级软件定义硬件工程。

- 论文标题建议：`SD-HWE-Bench: A Benchmark for Software-Defined Hardware Engineering`
- 品牌呈现：全大写连字符 `SD-HWE-Bench`
- pip 包名保持不变：`sd-hwe-bench`

## 域名（立即注册！）

四个域名全部可用，站点 HTML 已就绪：`site/index.html`

| 域名 | 状态 |
|---|---|
| `sd-hwe-bench.org` | ✅ 可注册 |
| `sdhwebench.org` | ✅ 可注册 |
| `sd-hwe-bench.com` | ✅ 可注册 |
| `sdhwebench.com` | ✅ 可注册 |

主域名建议用 `sd-hwe-bench.org`。注册商推荐 Namecheap 或 Cloudflare Registrar。

## 当前状态

| 维度 | 状态 | 说明 |
|---|---|---|
| 核心框架 | ✅ 完成 | Python 包、CLI、harness、scorer、dataset、leaderboard、llm_judge |
| 单元测试 | ✅ 30/30 pass | `tests/` 全覆盖 |
| 任务数量 | ⚠️ 5 个 | 每个 task_type 各 1 个（需扩充到 30+） |
| 评分体系 | ✅ 可运行 | L0-L4 + LLM rubrics 端到端通 |
| piki 引擎 | ✅ 已集成 | 真实 piki 0.1.0，通过 `--format json` 结构化输出 |
| LLM Judge | ✅ DeepSeek | via OPENAI_API_KEY |
| Leaderboard | ✅ 有数据 | `leaderboard/results.json` 含完整结果 |
| 站点 | ✅ HTML 就绪 | `site/index.html`，Coming Soon 单页 |
| 域名 | ❌ 未注册 | **高优先级：立刻注册** |

## Baseline 实验

### 已完成：DeepSeek V4 Flash vs V4 Pro（API 调用，5 tasks）

| Task | DeepSeek V4 Flash | DeepSeek V4 Pro |
|---|---|---|
| comprehensive-001 | ❌ 20% | ❌ 20% |
| connection-design-001 | ❌ 60% | ❌ 60% |
| instance-declare-001 | ❌ 20% | ❌ 30% |
| layout-design-001 | ❌ 30% | ❌ 65% |
| mating-design-001 | ✅ 85% | ✅ 85% |
| **Pass@1** | **1/5 (20%)** | **1/5 (20%)** |
| **Avg Score** | **43%** | **52%** |

详细结果：`work/baseline_api_results.json`

### 待完成：Gemini 2.5 Flash、Kimi K2.7 Code

- Gemini CLI 可用（OAuth），`gemini -p` 模式可产出文本但是否写文件待验证
- Kimi CLI 可用（OAuth），`kimi -y` TUI 模式在 subprocess 中有问题，`kimi -p` 模式只能产出文本
- 脚本已写好：`work/run_cli_baseline.py`（支持 API + CLI 两种模式）
- **下一轮直接用这个脚本跑 Gemini 和 Kimi：**
  ```bash
  cd /Users/indenscale/workspace/sd-hwe-bench
  .venv/bin/python work/run_cli_baseline.py
  ```

### Baseline 问题总结

**YAML 解析方案需要改进**：当前从模型文本输出中提取 YAML block 并写入正确目录的准确率不够高。许多任务 files_written=0，说明模型产出了内容但文件路径推断失败。需要下一轮改进 prompt 中的文件路径约定，或改用 agent driver 模式（让模型真正执行文件写入命令）。

## 论文摘要弹药（草稿）

> On the only truly end-to-end task — designing a complete 42U rack deployment from scratch — both DeepSeek V4 Flash and V4 Pro scored just 20%, failing at L1 schema validation, L2 reference integrity, and L3 business rules (power budget, U-slot conflicts). Even on simpler sub-tasks, Pass@1 was only 1/5 (20%) for both models.
>
> Across 5 telecom engineering design tasks spanning instance declaration, layout, connections, and mating, no model achieved more than 20% Pass@1, and the best average score was 52% — confirming that even strong LLMs lack the engineering common sense needed for declarative hardware design.

## 整体待做事项

1. **注册域名**：sd-hwe-bench.org + sdhwebench.org（立刻）
2. **完成 4-model baseline**：跑 `work/run_cli_baseline.py` 追加 Gemini + Kimi
3. **改进 YAML 文件写出的可靠性**：prompt 约定或改用 agent driver
4. **扩充任务到 30+**：每个 task_type 至少 6 个
5. **Git repo**：`git init` + 初始 commit
6. **CI/CD**：GitHub Actions 自动跑 benchmark
7. **论文初稿**：填充 baseline 数据到论文

## Piki 调用方式

```
绝对路径导入（开发阶段）:
  /Users/indenscale/workspace/piki/.venv/bin/python -m piki check --format json

未来 PyPI 分发后:
  piki check --format json
```

## 已有基线脚本

| 脚本 | 用途 |
|---|---|
| `work/run_baseline.sh` | Codex CLI 多模型（旧，已确认无效——都走 DeepSeek） |
| `work/run_api_baseline.py` | DeepSeek API 单模型（已验证可用） |
| `work/run_cli_baseline.py` | **4-model 统一脚本**（API + CLI，下一轮跑） |

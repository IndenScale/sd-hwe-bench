# SD-HWE-Bench 进度备忘录

> 最后更新：2026-06-15 CST

## 命名

- 项目名：`SD-HWE-Bench`
- 论文标题建议：`SD-HWE-Bench: A Benchmark for Software-Defined Hardware Engineering`
- pip 包名：`sd-hwe-bench`

## 域名

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
| 核心框架 | ✅ 完成 | Python 包、Typer CLI、Actor-Critic scorer、dataset、leaderboard、llm_judge |
| 单元测试 | ✅ 45/45 pass | `tests/` 覆盖 workspace、parser、actors、critics、scorer |
| 任务数量 | ⚠️ 5 个 | 每个 task_type 各 1 个（目标 30+） |
| 评分体系 | ✅ 可运行 | L0-L4 + Deliverables + LLM rubrics 端到端通 |
| piki 引擎 | ✅ 已集成 | 真实 piki 0.1.0，支持 `--sandbox docker` / `podman` / `none` |
| LLM Judge | ✅ DeepSeek | via OPENAI_API_KEY / `--rubrics-model` |
| Actor-Critic | ✅ 已落地 | Actor 生成 → Critics 分层评分 → 归档轨迹 |
| 沙盒 | ✅ 支持 | Workspace 隔离 + 可选 Docker/Podman piki 容器 |
| Leaderboard | ✅ 可生成 | `sd-hwe-bench leaderboard --update` |
| 站点 | ✅ HTML 就绪 | `site/index.html`，Coming Soon 单页 |
| 域名 | ❌ 未注册 | **高优先级：立刻注册** |

## CLI 用法

```bash
sd-hwe-bench list --dataset .
sd-hwe-bench run telecom/comprehensive-001 --actor kimi
sd-hwe-bench run telecom/comprehensive-001 --actor openai:deepseek-v4-pro --rubrics
sd-hwe-bench score telecom/comprehensive-001 runs/.../workspace
sd-hwe-bench archive
sd-hwe-bench leaderboard --update
```

Actor 规范：`kimi[:model]` / `codex[:model]` / `gemini[:model]` / `openai:MODEL` / `deepseek:MODEL`。

## 归档结构

每次 rollout 生成：

```text
runs/<timestamp>_<task>_<actor>/
├── manifest.json
├── prompt.md
├── trajectory.jsonl
├── workspace/          # Actor 最终输出
├── scores.json         # 各层、交付物、rubric 分数
└── reviews.json        # Critic comments
```

## 待做事项

1. 注册域名 `sd-hwe-bench.org`
2. 用 CLI 跑 baseline 并生成 leaderboard
3. 扩充任务到 30+，每个 task_type 至少 6 个
4. 验证并改进交付物产出（必要时在 Actor 中强制调用 `piki generate`）
5. `git init` + 初始 commit
6. GitHub Actions CI/CD
7. 论文初稿

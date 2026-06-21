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
| 核心框架 | ✅ 完成 | Python 包、Typer CLI、`commands/` 子命令、Actor-Critic scorer、dataset、leaderboard、llm_judge |
| 单元测试 | ✅ 49/49 pass | `tests/` 覆盖 workspace、parser、actors、critics、scorer |
| 任务数量 | ⚠️ 5 个 | 每个 task_type 各 1 个（目标 30+） |
| 评分体系 | ✅ 可运行 | L0-L4 + Deliverables + LLM rubrics 端到端通 |
| piki 引擎 | ✅ 已集成 | 真实 piki 0.1.0，支持 `--sandbox auto` / `docker` / `podman` / `none` |
| LLM Judge | ✅ DeepSeek | via OPENAI_API_KEY / `--rubrics-model`（可选依赖 `deepeval`） |
| Actor-Critic | ✅ 已落地 | Actor 生成 → Critics 分层评分 → 归档轨迹 |
| 沙盒 | ✅ 支持 | Workspace 隔离；`--sandbox auto` 自动探测 docker → podman → none |
| Leaderboard | ✅ 可生成 | `sd-hwe-bench leaderboard --update` |
| 站点 | ✅ HTML 就绪 | `site/index.html`，Coming Soon 单页 |
| 代码结构 | ✅ 已重构 | CLI 拆分为 `commands/`，删除 `agents/`、`leaderboard.py`、`* .bak` 等 legacy |
| 域名 | ❌ 未注册 | **高优先级：立刻注册** |

## 依赖与引擎

- `pyproject.toml` 已声明 `piki` / `adl` 依赖（git URL）。
- 在 monorepo 本地开发时，使用 editable 安装保持与 `~/workspace/piki` 同步：
  ```bash
  uv pip install -e ../piki/adl -e ../piki
  ```
- `SandboxRunner` 现在优先使用当前 Python 解释器执行 `python -m piki`；
  当当前环境没有 piki 时，依次回退到 `$PIPKIPATH` 和 PATH 上的 `piki` 可执行文件。

## 已知已修复的 ADL 问题

1. **model→family 推断丢失**：ADL MIR compiler 在 instance 只声明 `model:` 时未继承 model 的 family，导致 `MATE-002` 与碰撞检测误报。已在 `piki/adl/src/adl/compiler/passes/symbol_resolve.py` 修复。
2. **机柜 U 位坐标映射错误**：`GeometryProvider` 将 `position_u` 映射到深度轴（Z），使不同 U 位设备被判定为碰撞。已改为沿高度轴（Y）排布，并校正机柜内的 X/Z 居中/前对齐逻辑。

## CLI 用法

```bash
# 默认 `--sandbox auto`：优先 docker，其次 podman，最后回退到本地 none
sd-hwe-bench list --dataset .
sd-hwe-bench run telecom/comprehensive-001 --actor kimi
sd-hwe-bench run telecom/comprehensive-001 --actor openai:deepseek-v4-pro --rubrics
sd-hwe-bench score telecom/comprehensive-001 runs/.../workspace
sd-hwe-bench archive
sd-hwe-bench leaderboard --update

# 显式指定沙箱后端
sd-hwe-bench run telecom/comprehensive-001 --actor kimi --sandbox docker
sd-hwe-bench run telecom/comprehensive-001 --actor codex:deepseek --sandbox none
```

- Actor 规范：`kimi[:model]` / `codex[:model]` / `gemini[:model]` / `openai:MODEL` / `deepseek:MODEL`。
- 沙箱规范：`auto`（默认） / `docker` / `podman` / `none`。

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

## 感性认识（来自 2026-06-15 kimi pass@1 全任务 rollout）

1. **kimi code 能理解工程设计任务**：不只是模板填空，它会根据任务类型（instance/layout/mating/connection/comprehensive）选择正确的目录和文件类型，并主动调用 `piki check` / `piki generate`。
2. **具备自我修正能力**：`connection-design-001` 的 scaffold 把设备文件放在 `instances/` 根目录，kimi 从 piki 报错中推理出应移到 `instances/devices/`，并补上 `family: ServerFamily`。
3. **强依赖 prompt 准确性**：早期 prompt 中 layout/mate 的字段名、mate 格式、fiber family 等示例与实际 schema 不一致，kimi 能凭试错绕过去，但浪费 token 且可能失败。已根据成功 rollout 的轨迹重写了 `_PIKI_QUICKREF`。
4. **stdout 不是交付物**：kimi / codex / gemini 等 agent 模式直接修改工作目录，原 Actor 从 stdout 解析 YAML 回写是错误设计，已改为只统计新增文件。
5. **评分器也有 bug**：`score_task` 错误加载 task 元数据、PikiCritic fallback 无效、deliverable scorer 对 rack panel 文件名硬编码。均已修复。
6. **当前 benchmark 仍偏结构化**：5 个任务都有明确 scaffold 和 piki 强约束。真实工程设计更开放，后续需补充无 scaffold、需求模糊、多方案权衡类任务。

## 待做事项

1. 注册域名 `sd-hwe-bench.org`
2. 用 CLI 跑 baseline 并生成 leaderboard
3. 扩充任务到 30+，每个 task_type 至少 6 个
4. 验证并改进交付物产出（必要时在 Actor 中强制调用 `piki generate`）
5. `git init` + 初始 commit
6. GitHub Actions CI/CD
7. 论文初稿

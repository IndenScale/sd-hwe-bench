# 参数化 SD-HWE-Bench 中的 magic number 与硬编码固定值

## 状态

**已实现**，2026-06-25。提交：`480c4ce`。

实现概要：

- 新增 `src/sd_hwe_bench/settings.py`，集中管理所有默认值并支持 `SD_HWE_*` 环境变量覆盖。
- 新增 `src/sd_hwe_bench/config/rule_layers.yaml` 与 `deliverables.yaml`，外部化 piki 规则→层映射与交付物类型映射。
- `Containerfile` 增加 `PYTHON_BASE_IMAGE`、`WORKDIR_SRC`、`WORKDIR_RUN`、`PIKI_INSTALL_DIR` build args；`scripts/build-piki-image.sh` 支持 `CONTAINER_RUNTIME` 与 `--tag`。
- 删除 `runner.py` 与 `tools/extract_tasks.py` 中的绝对用户路径 fallback。
- `actors`、`scorer`、`critics`、`commands`、`prompts`、`llm_judge` 全部改为从 `settings` 读取默认值。
- 新增 `tests/test_settings.py`；全量测试 78/78 通过，`ruff check`/`ruff format` 通过。

## 动机

当前代码库中存在多处 magic number、硬编码路径、默认模型名、容器镜像名、超时时间等固定值。这些硬编码会导致：

1. **可移植性差**：绝对路径 `/Users/indenscale/workspace/piki/.venv/bin/python` 直接写死，换台机器或 CI 环境即失效。
2. **实验复现困难**：模型名、API endpoint、温度、max tokens、评分权重等实验参数散落在源码各处，无法通过环境变量或配置文件统一调整。
3. **维护成本高**：新增 piki 规则时需要同步修改 `PIKI_RULE_LAYERS` / `PIKI_RULE_PREFIXES`；新增交付物类型时需要同步修改 `DELIVERABLE_PATHS`。
4. **安全隐患**：虽然未发现明文密码/Token，但 API key 环境变量名、默认 API endpoint、容器 bypass 参数等假设固化在代码中，不利于凭证轮转和多后端切换。

本项目目前没有 `docker-compose.yml`；与容器相关的硬编码集中在 `Containerfile` 与 `scripts/build-piki-image.sh` 中，需要一起参数化。

## 范围

重点处理以下类别的硬编码：

- **容器/构建**：`Containerfile`、`scripts/build-piki-image.sh`
- **Actor 与模型**：默认模型名、API endpoint、生成参数、CLI 二进制名、CLI flags
- **沙箱与执行**：容器镜像名、挂载路径、超时时间、piki python 解析
- **评分与规则**：评分层权重、规则→层映射、交付物映射、默认阈值
- **Prompt 与模板**：大段硬编码 prompt、quickref、repair markers
- **CLI 默认值**：`--passes`、`--timeout`、`--jobs`、`--run-dir`、`--sandbox-image` 等
- **凭证/端点**：API key env 名、默认 base URL、CLI bypass flags

不在本次范围的：

- `canonical/telecom-rack/` 下的参考模型/实例数据（这些是 benchmark 的固定题库，不是运行配置）。
- 纯 UI 展示用的字符串截断（如 `rationale[:80]`），除非它们影响行为。

## 当前发现

### 1. 容器/构建相关

| 文件 | 位置 | 当前硬编码 | 建议 |
|------|------|------------|------|
| `Containerfile` | L6 | `FROM python:3.12-slim` | `ARG PYTHON_BASE_IMAGE=python:3.12-slim` |
| `Containerfile` | L8, L19 | `WORKDIR /src`、`WORKDIR /work` | `ARG WORKDIR_SRC=/src`、`ARG WORKDIR_RUN=/work` |
| `Containerfile` | L11 | `COPY . /src/piki` | `ARG PIKI_INSTALL_DIR=/src/piki` |
| `Containerfile` | L15–L16 | `pip install -e "/src/piki/adl"`、`"/src/piki"` | 使用上述 build arg |
| `scripts/build-piki-image.sh` | L9 | `IMAGE_TAG="${IMAGE_TAG:-sd-hwe-bench-piki:latest}"` | 已支持 env，可增加 `--tag` / `VERSION` 文件 |
| `scripts/build-piki-image.sh` | L18 | 直接调用 `docker build` | `CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"`（支持 podman） |

### 2. 绝对路径 / 用户环境相关

| 文件 | 位置 | 当前硬编码 | 建议 |
|------|------|------------|------|
| `src/sd_hwe_bench/sandbox/runner.py` | L19 | `_DEFAULT_PIKI_PYTHON = "/Users/indenscale/workspace/piki/.venv/bin/python"` | 删除或改为 `None`；优先使用 `PIPKIPATH` / `SD_HWE_PIKI_PYTHON` / PATH |
| `tools/extract_tasks.py` | L174 | `fallback = "/Users/indenscale/workspace/piki/.venv/bin/python"` | 同上 |

### 3. 容器镜像名

| 文件 | 位置 | 当前硬编码 | 建议 |
|------|------|------------|------|
| `src/sd_hwe_bench/sandbox/runner.py` | L77 | `image: str = "sd-hwe-bench-piki:latest"` | `settings.DEFAULT_SANDBOX_IMAGE` / `SD_HWE_SANDBOX_IMAGE` |
| `src/sd_hwe_bench/commands/run.py` | L360 | `--sandbox-image sd-hwe-bench-piki:latest` | 从 settings 读取默认值 |
| `src/sd_hwe_bench/commands/run_repair.py` | L78 | 同上 | 同上 |
| `src/sd_hwe_bench/commands/score.py` | L27 | 同上 | 同上 |
| `tests/test_run_parallel.py` | L109 等 | 测试直接写死镜像名 | 从 settings 导入 |

### 4. 超时时间

| 文件 | 位置 | 当前硬编码 | 建议 |
|------|------|------------|------|
| `src/sd_hwe_bench/actors/base.py` | L25 | `timeout: int = 600` | `settings.DEFAULT_ACTOR_TIMEOUT_S` / `SD_HWE_ACTOR_TIMEOUT_S` |
| `src/sd_hwe_bench/actors/factory.py` | L12 | `timeout: int = 600` | 同上 |
| `src/sd_hwe_bench/commands/run.py` | L369 | `--timeout 600` | 同上 |
| `src/sd_hwe_bench/commands/run_repair.py` | L83 | `--timeout 600` | 同上 |
| `src/sd_hwe_bench/sandbox/runner.py` | L161, L223 | `timeout=120`、`timeout=180` | `SD_HWE_PIKI_TIMEOUT_S` / `SD_HWE_CONTAINER_TIMEOUT_S` |
| `src/sd_hwe_bench/llm_judge.py` | L48, L116 | `timeout: int = 120` | `LLM_JUDGE_TIMEOUT_S` |
| `tools/extract_tasks.py` | L191 | `timeout=120` | 共享 piki timeout |
| `src/sd_hwe_bench/harness.py` | L77 | `timeout=300` | `Harness` 参数或 env |

### 5. Actor 默认模型 / 二进制 / API 端点

| 文件 | 位置 | 当前硬编码 | 建议 |
|------|------|------------|------|
| `src/sd_hwe_bench/actors/kimi.py` | L31 | `kimi_bin: str = "kimi"` | `KIMI_BIN` env |
| `src/sd_hwe_bench/actors/kimi.py` | L33 | `model=model or "kimi-code/kimi-for-coding"` | `DEFAULT_KIMI_MODEL` env / settings |
| `src/sd_hwe_bench/actors/.py` | L30 | `gemini_bin: str = ""` | `GEMINI_BIN` env |
| `src/sd_hwe_bench/actors/.py` | L32 | `model=model or "-2.5-flash"` | `DEFAULT_GEMINI_MODEL` env / settings |
| `src/sd_hwe_bench/actors/.py` | L52–L58 | git init/add/commit timeout = `10` | `GEMINI_GIT_INIT_TIMEOUT` env |
| `src/sd_hwe_bench/actors/codex.py` | L30 | `codex_bin: str = "codex"` | `CODEX_BIN` env |
| `src/sd_hwe_bench/actors/codex.py` | L32 | `model=model or "deepseek-chat"` | `DEFAULT_CODEX_MODEL` env / settings |
| `src/sd_hwe_bench/actors/codex.py` | L48–L54 | `--skip-git-repo-check`、`--dangerously-bypass-approvals-and-sandbox` 等 flags | `CODEX_EXTRA_ARGS` env 或 settings；补充安全说明 |
| `src/sd_hwe_bench/actors/openai_actor.py` | L36 | `model=model or "deepseek-chat"` | `DEFAULT_OPENAI_MODEL` env / settings |
| `src/sd_hwe_bench/actors/openai_actor.py` | L37 | `base_url or os.environ.get("OPENAI_BASE_URL", "https:/api.deepseek.com/v1")` | 默认 endpoint 放入 settings，env 优先 |
| `src/sd_hwe_bench/actors/openai_actor.py` | L67–L68 | `temperature=0.0`、`max_tokens=8192` | CLI `--temperature`、`--max-tokens` 或 settings |
| `src/sd_hwe_bench/llm_judge.py` | L17 | `_DEFAULT_MODEL = "deepseek-chat" if ... else "gpt-4.1-mini"` | `LLM_JUDGE_MODEL` env / `--rubrics-model` 统一 |

### 6. 评分 / 规则 / 交付物映射

| 文件 | 位置 | 当前硬编码 | 建议 |
|------|------|------------|------|
| `src/sd_hwe_bench/scorer.py` | L58–L66 | `LAYER_WEIGHTS` dict | `config/scoring.yaml` 或 `SD_HWE_LAYER_WEIGHT_L*` env |
| `src/sd_hwe_bench/scorer.py` | L68–L69 | `DELIVERABLE_WEIGHT = 0.15`、`RUBRIC_WEIGHT = 0.0` | 同上 |
| `src/sd_hwe_bench/critics/piki.py` | L15–L40 | `PIKI_RULE_LAYERS` dict | `config/rule_layers.yaml` |
| `src/sd_hwe_bench/critics/piki.py` | L45–L59 | `PIKI_RULE_PREFIXES` list | 同上 |
| `src/sd_hwe_bench/critics/piki.py` | L61–L66 | `LAYER_WEIGHTS`（与 scorer 重复） | 从 scorer / settings 导入 |
| `src/sd_hwe_bench/critics/deliverable.py` | L12–L18 | `DELIVERABLE_PATHS` dict | `config/deliverables.yaml` 或 `task.yaml` |
| `src/sd_hwe_bench/critics/syntax.py` | L54–L56 | 每个 parse error 扣 0.1 | `SYNTAX_PENALTY_PER_ERROR` settings |
| `src/sd_hwe_bench/task.py` | L53 | `threshold: float = Field(default=0.6, ...)` | `DEFAULT_RUBRIC_THRESHOLD` settings |
| `src/sd_hwe_bench/task.py` | L67 | `plugins: ... default=["telecom"]` | `DEFAULT_PLUGINS` settings |
| `src/sd_hwe_bench/task.py` | L69 | `scoring_layers: ... default=["L0","L1","L2","L3"]` | `DEFAULT_SCORING_LAYERS` settings |

### 7. Prompt / 模板

| 文件 | 位置 | 当前硬编码 | 建议 |
|------|------|------------|------|
| `src/sd_hwe_bench/prompts.py` | L9–L152 | `_PIKI_QUICKREF` 大段 prompt | 迁移到 `prompts/piki_quickref.md` 模板，支持 `--prompt-template-dir` |
| `src/sd_hwe_bench/prompts.py` | L155 | `REPAIR_MARKERS` dict | 可保留为常量，或暴露到 settings |
| `src/sd_hwe_bench/prompts.py` | L186 | `output_mode: Literal["cli", "api"] = "cli"` | CLI `--output-mode` |
| `src/sd_hwe_bench/prompts.py` | L233 | `f.stat().st_size < 4096` | `SCAFFOLD_INLINE_MAX_BYTES` settings |
| `src/sd_hwe_bench/prompts.py` | L365 | `diagnostics[:20]` | `REPAIR_PROMPT_MAX_DIAGNOSTICS` settings |
| `src/sd_hwe_bench/prompts.py` | L380, L382 | `ls.errors[:10]`、`len(ls.errors) > 10` | `REPAIR_PROMPT_MAX_ERRORS_PER_LAYER` settings |
| `src/sd_hwe_bench/llm_judge.py` | L198–L221 | rubric scoring scale 与默认 steps | 模板化 |
| `src/sd_hwe_bench/actors/openai_actor.py` | L19 | `_SYSTEM_PROMPT` | 支持 `--system-prompt` 文件或 `SD_HWE_SYSTEM_PROMPT` |

### 8. CLI 默认值

| 文件 | 当前硬编码 | 建议 |
|------|------------|------|
| `commands/run.py` | `--actor kimi` | `SD_HWE_DEFAULT_ACTOR` |
| `commands/run.py` | `--passes 1` | `SD_HWE_DEFAULT_PASSES` |
| `commands/run.py` | `--jobs -1`（自动上限 4） | `SD_HWE_MAX_AUTO_JOBS` |
| `commands/run.py` | `--run-dir runs` | `SD_HWE_RUN_DIR` |
| `commands/run.py` | `--sandbox auto` | `SD_HWE_SANDBOX_BACKEND` |
| `commands/run.py` | `--sandbox-image sd-hwe-bench-piki:latest` | `SD_HWE_SANDBOX_IMAGE` |
| `commands/run_repair.py` | `--max-repair 20` | `SD_HWE_DEFAULT_MAX_REPAIR` |
| `commands/archive.py` | `--run-dir runs` | `SD_HWE_RUN_DIR` |
| `commands/leaderboard.py` | `--run-dir runs`、`--output leaderboard` | `SD_HWE_RUN_DIR`、`SD_HWE_LEADERBOARD_DIR` |
| `commands/run.py` / `run_repair.py` | `raw_output_preview` 截断 2000 字符 | `SD_HWE_LOG_PREVIEW_CHARS` |

### 9. 其他 / 一致性

| 文件 | 问题 | 建议 |
|------|------|------|
| `src/sd_hwe_bench/actors/openai_actor.py` | 内部硬编码 `SandboxRunner(backend="none")`，与 `--sandbox` 参数不一致 | 接受 runner 注入或使用全局配置 |
| `src/sd_hwe_bench/sandbox/runner.py` | 容器内挂载路径 `/work` 与 `Containerfile` 中 `WORKDIR /work` 硬编码耦合 | 通过 build arg + settings 统一 |
| `pyproject.toml` | `adl` / `piki` 依赖使用固定 git URL 和默认分支 | 使用 tag/commit 或可选依赖组 |
| 多处源码 | `L0`–`L4` 层名重复出现 | 集中为 `LAYER_NAMES` 常量 |

## 建议方案

### 阶段 1：引入统一配置模块（高优先级）

1. 新建 `src/sd_hwe_bench/settings.py`（或使用 `pydantic-settings`），集中管理：
   - 默认 actor timeout、模型名、二进制名
   - 默认 sandbox image / backend / workdir
   - 默认 run dir、leaderboard dir、passes、jobs 上限
   - 评分权重、默认 rubric threshold、默认 scoring layers
   - piki python 解析顺序：`SD_HWE_PIKI_PYTHON` → `PIPKIPATH` → PATH
2. 所有 CLI `typer.Option` 默认值改为从 `settings` 读取。
3. 所有测试导入 `settings` 中的默认值，而不是再次硬编码。

### 阶段 2：外部化映射与模板（中优先级）

1. 将 `PIKI_RULE_LAYERS`、`PIKI_RULE_PREFIXES`、`DELIVERABLE_PATHS` 迁移到 `config/` YAML。
2. 将 `_PIKI_QUICKREF`、system prompt、rubric judge prompt 迁移到 `prompts/` Markdown/Jinja 模板。
3. `Containerfile` 增加 build args（`PYTHON_BASE_IMAGE`、`WORKDIR_SRC`、`WORKDIR_RUN`、`PIKI_INSTALL_DIR`），与 `settings` 保持一致。

### 阶段 3：凭证与后端解耦（高优先级）

1. OpenAI Actor 的默认 base URL 从 settings 读取，保留 `OPENAI_API_KEY` / `OPENAI_BASE_URL` env 优先。
2. 删除 `/Users/indenscale/workspace/piki/.venv/bin/python` 的硬编码 fallback。
3. 修复 `OpenAIActor` 内部 `backend="none"` 与全局沙箱配置不一致的问题。
4. `scripts/build-piki-image.sh` 支持 `CONTAINER_RUNTIME` 与 `--tag`。

## 验收标准

- [x] `settings.py` 存在且被 CLI、actors、sandbox runner 使用；没有新的 magic number 默认值继续散落在源码中。
- [x] 删除 `runner.py` 与 `tools/extract_tasks.py` 中的绝对用户路径 fallback。
- [x] `Containerfile` 支持通过 `--build-arg` 修改 base image 与安装路径；构建脚本支持 `podman`。
- [x] 默认模型名、API endpoint、超时、评分权重、rule-layer 映射、deliverable 映射均可通过 env var 或 config 文件覆盖。
- [x] `OpenAIActor` 遵守 `--sandbox` 全局配置，不再硬编码 `backend="none"`。
- [x] 所有现有测试通过；新增测试验证 settings 默认值可被 env var 覆盖。
- [x] 没有明文凭证/Token/密码写入源码（当前暂无，保持为 0）。

## 相关文件

- `Containerfile`
- `scripts/build-piki-image.sh`
- `src/sd_hwe_bench/settings.py`（待创建）
- `src/sd_hwe_bench/actors/{base,factory,kimi,codex,openai_actor}.py`
- `src/sd_hwe_bench/sandbox/{runner,workspace,parser}.py`
- `src/sd_hwe_bench/commands/{run,run_repair,score,archive,leaderboard}.py`
- `src/sd_hwe_bench/critics/{piki,deliverable,syntax,rubric}.py`
- `src/sd_hwe_bench/scorer.py`
- `src/sd_hwe_bench/task.py`
- `src/sd_hwe_bench/llm_judge.py`
- `src/sd_hwe_bench/prompts.py`
- `src/sd_hwe_bench/harness.py`
- `tools/extract_tasks.py`
- `pyproject.toml`
- `tests/test_actors.py`、`tests/test_scorer.py`、`tests/test_run_parallel.py`

## 优先级

**M2（任务集扩展与框架稳定）** —— 在扩展到 30+ 任务并跑多模型基线之前，需要统一配置入口，否则不同机器/CI 的实验参数会难以复现。

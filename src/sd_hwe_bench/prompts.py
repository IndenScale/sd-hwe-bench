"""Prompt building for Actor rollout."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from sd_hwe_bench.settings import settings

_PIKI_QUICKREF = """\
## Piki 快速参考

piki 是声明式系统建模框架。工程师用 YAML 声明设计意图，`piki check` 自动校验，`piki generate` 生成交付物。

### 目录约定（务必遵守）
- `instances/devices/` — 设备实例（**不能放在 `instances/` 根目录**）
- `instances/ports/` — 端口实例（独立文件）
- `instances/transceivers/` — 光模块实例
- `instances/fibers/` — 光纤实例
- `instances/port_connections/` — 端口连接实例
- `instances/pdus/` — PDU 实例
- `instances/racks/` — 机柜实例
- `layouts/` — 布局文件（`layouts/layout.yaml`）
- `mates/` — 配合文件（位于 workspace 根目录）
- `models/` — 型号默认值（已在 scaffold 中提供，**不要修改**）
- `piki.toml` — 项目配置（已在 scaffold 中提供，**不要修改**）
- `dist/` — `piki generate` 输出的交付物目录

如果 scaffold 中的设备文件被错误地放在 `instances/` 根目录，请将它们移动到 `instances/devices/`。

### 设备 Instance（`instances/devices/*.yaml`）
```yaml
id: SRV-01
family: ServerFamily
model: generic-server
name: "服务器-01"
status: installed
interfaces:
  - id: eth0
    interface_type: SFP28
    direction: bidirectional
```

### 端口 Instance（`instances/ports/*.yaml`）
```yaml
id: SRV-01-eth0
family: PortFamily
device_id: SRV-01
port_name: eth0
port_type: SFP28
status: installed
```

### 光模块 Instance（`instances/transceivers/*.yaml`）
```yaml
id: SFP28-SR-S01-ETH0
family: TransceiverFamily
model: sfp28-sr-25g
status: installed
```

### 光纤 Instance（`instances/fibers/*.yaml`）
```yaml
id: FIBER-S01-SW01
family: FiberPatchCordFamily
from_port: SRV-01/eth0
to_port: SW-01/Gi1/0/1
fiber_type: OM4-LC-LC
length_m: 2.0
status: installed
```

### 端口连接 Instance（`instances/port_connections/*.yaml`）
```yaml
id: CONN-S01-SW01
family: PortConnectionFamily
from_port: SRV-01/eth0
to_port: SW-01/Gi1/0/1
cable_type: OM4-LC-LC
length_m: 2.0
status: installed
```

### Layout（`layouts/layout.yaml`）
字段名必须是 `rack_id`、`position_u`、`pdu_id`：
```yaml
- instance: SRV-01
  rack_id: RACK-A01
  position_u: 10
  pdu_id: PDU-A
- instance: SW-01
  rack_id: RACK-A01
  position_u: 20
  pdu_id: PDU-B
```

**重要**：只要任务里出现机柜（rack）和设备/PDU，就必须为每个设备实例和每个 PDU 都创建一条 layout 记录。
没有 layout 时，所有设备会被认为挤在原点，导致 `TELECOM-COLLISION-001` 空间冲突检查失败。

### Mate（`mates/<mate-type>/*.yaml`）
统一使用 `type`、`parent`、`child`：

机柜安装：
```yaml
type: rack-mount-19inch
parent: RACK-A01
child: SRV-01
at:
  u_start: 10
  u_span: 2
constrains:
  - field: depth_mm
    operator: "<="
    value_ref: depth_mm
    message: "SRV-01 深度超过 RACK-A01 机柜深度，无法安装"
```

电源 IEC 配合：
```yaml
type: power-iec-c14-c13
parent: PDU-A/outlet-1
child: SRV-01/power-a
```

SFP28 笼式配合：
```yaml
type: sfp28-cage
parent: SRV-01/eth0
child: SFP28-SR-S01-ETH0/host
```

LC 光纤头配合：
```yaml
type: lc-connector
parent: SFP28-SR-S01-ETH0/line
child: FIBER-S01-SW01/end-a
```

### 推荐工作流
1. 阅读 scaffold 中的 `piki.toml` 和 `models/`，确认已有实例。
2. 按正确目录结构创建/补充 YAML 文件。
3. 运行 `piki check`。
4. 如果有错误，根据报错修复 YAML 或调整文件位置。
5. 运行 `piki generate` 生成交付物到 `dist/`。
6. 再次运行 `piki check` 确认最终无错误。

### 提交前检查清单（每次创建 `.sdhwe.done` 前必读）
- [ ] 所有要求的 instance YAML 已创建，且放在正确的子目录（`instances/devices/`、`instances/ports/`、`instances/pdus/`、`instances/racks/` 等），不在 `instances/` 根目录。
- [ ] 如果任务涉及机柜和设备/PDU，`layouts/layout.yaml` 已包含每条设备/PDU 的 `rack_id`、`position_u`、`pdu_id`。
- [ ] 所有 `mates/` 文件已创建（rack-mount、power、fiber、transceiver 等）。
- [ ] 已运行 `piki check` 且 0 错误。
- [ ] 如果任务要求交付物，已运行 `piki generate`，且 `dist/` 下出现对应的 `.csv` / `.svg` 文件。
"""


REPAIR_MARKERS = {
    "done": ".sdhwe.done",
    "give_up": ".sdhwe.give_up",
    "info_gap": ".sdhwe.info_gap",
    "no_solution": ".sdhwe.no_solution",
}

_REPAIR_MARKER_INSTRUCTIONS = """\
## 主动终止标记

本轮任务允许你在以下情况主动创建标记文件，系统会立即停止并记录原因：

- `.sdhwe.done` — 你认为任务已完成（系统仍会验证）。
- `.sdhwe.give_up` — 你确认当前能力不足以完成该任务。
- `.sdhwe.info_gap` — 任务描述或 scaffold 缺少关键信息，无法继续。
- `.sdhwe.no_solution` — 需求本身相互矛盾，不存在合法设计解（例如提供的构件无法同时满足强度和重量约束）。

你可以在标记文件里写一句简短说明。不要在没有充分尝试前随意放弃。
"""


class PromptBuilder:
    """Build prompts for Actor rollout."""

    def __init__(self, piki_ref_path: Path | None = None):
        self.piki_ref_path = piki_ref_path

    def build(
        self,
        task_metadata: dict[str, Any],
        scaffold_dir: Path,
        require_generator: bool = True,
        output_mode: Literal["cli", "api"] = "cli",
        repair_mode: bool = False,
        baseline_mode: bool = False,
    ) -> str:
        """Build the full prompt injected into the actor.

        Args:
            task_metadata: Parsed task.yaml as dict.
            scaffold_dir: Path to the task's scaffold/ directory.
            require_generator: Whether to emphasize deliverable generation.
            output_mode: "cli" for agents that mutate the working directory
                directly; "api" for agents that return YAML code blocks.
            repair_mode: Include repair-loop instructions and termination markers.
            baseline_mode: Baseline prompt with no ESA feedback / no markers.
        """
        parts: list[str] = []

        task_id = task_metadata.get("task_id", "unknown")
        task_name = task_metadata.get("name", "Unnamed")
        task_type = task_metadata.get("task_type", "comprehensive")
        difficulty = task_metadata.get("difficulty", "medium")
        plugins = task_metadata.get("plugins", [])

        parts.append(
            "You are a hardware engineering design agent. Your task is to "
            "complete a declarative engineering design using piki.\n\n"
            f"**Task**: {task_name} ({task_id})\n"
            f"**Type**: {task_type} | **Difficulty**: {difficulty}\n"
            f"**Plugins**: {', '.join(plugins)}"
        )

        parts.append(_PIKI_QUICKREF)

        # Optional full piki reference
        if self.piki_ref_path and self.piki_ref_path.exists():
            parts.append("## Piki 完整参考\n")
            parts.append(self.piki_ref_path.read_text(encoding="utf-8"))

        # Scaffold info
        parts.append("## Scaffold 中已有的文件（只读，请勿修改）\n")
        if scaffold_dir.exists():
            for f in sorted(scaffold_dir.rglob("*")):
                if f.is_file():
                    rel = f.relative_to(scaffold_dir)
                    parts.append(f"- `{rel}`")
                    # Include small scaffold files inline for context
                    if (
                        f.suffix in (".yaml", ".yml", ".toml")
                        and f.stat().st_size < settings.SCAFFOLD_INLINE_MAX_BYTES
                    ):
                        parts.append(f"\n`{rel}`:\n```yaml")
                        parts.append(f.read_text(encoding="utf-8"))
                        parts.append("```\n")
        else:
            parts.append("- (无 scaffold)")

        # Requirement
        requirement = task_metadata.get("requirement", "")
        parts.append(f"\n## 设计需求\n\n{requirement}")

        # Expected outputs
        expected = task_metadata.get("expected_files", [])
        deliverables = task_metadata.get("expected_deliverables", [])

        parts.append("\n## 需要产出的文件\n")
        if expected:
            parts.append("必须创建以下 YAML 文件：\n")
            for f in expected:
                parts.append(f"- `{f}`")
        if deliverables:
            parts.append("\n必须生成交付物（执行 `piki generate`）：\n")
            for d in deliverables:
                parts.append(f"- `{d}`")

        # Output instructions
        if output_mode == "api":
            parts.append(
                "\n## 输出要求\n\n"
                "1. 输出每个文件为一个独立的 ```yaml 代码块。\n"
                "2. 每个代码块的第一行必须是一个文件路径注释，例如 "
                "`# instances/devices/SRV-01.yaml`。\n"
                "3. 务必把设备实例放在 `instances/devices/`，不要放在 `instances/` 根目录。\n"
                "4. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
                "5. 只产出与任务相关的文件，不要额外发挥。\n"
                "\n请开始完成这个工程设计任务，输出所有需要的 YAML 文件。"
            )
        elif baseline_mode:
            parts.append(
                "\n## 输出要求\n\n"
                "1. 作为设计 agent，请直接在 workspace 目录中创建/修改 YAML 文件；"
                "不需要在 stdout 中输出完整 YAML。\n"
                "2. 务必把设备实例放在 `instances/devices/`，不要放在 `instances/` 根目录。\n"
                "3. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
                "4. 不要运行 `piki check`、`piki generate` 或任何外部验证命令；"
                "系统会在你提交后统一验证。\n"
                "5. 只产出与任务相关的文件，不要额外发挥。\n"
                "\n请开始完成这个工程设计任务。"
            )
        elif repair_mode:
            parts.append(
                "\n## 输出要求\n\n"
                "1. 作为设计 agent，请直接在 workspace 目录中创建/修改 YAML 文件；"
                "不需要在 stdout 中输出完整 YAML。\n"
                "2. 务必把设备实例放在 `instances/devices/`，不要放在 `instances/` 根目录。\n"
                "3. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
                "4. 系统会在你每次提交文件后运行 `piki check` 并返回诊断；"
                "你可以根据诊断继续修改，也可以主动报告完成或失败。\n"
                "5. 只产出与任务相关的文件，不要额外发挥。\n"
                "\n请开始完成这个工程设计任务。"
            )
            parts.append(_REPAIR_MARKER_INSTRUCTIONS)
        else:
            parts.append(
                "\n## 输出要求\n\n"
                "1. 作为设计 agent，请直接在 workspace 目录中创建/修改 YAML 文件；"
                "不需要在 stdout 中输出完整 YAML。\n"
                "2. 务必把设备实例放在 `instances/devices/`，不要放在 `instances/` 根目录。\n"
                "3. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
                "4. 完成后必须先执行 `piki check`，确认无错误后再执行 `piki generate`。\n"
                "5. 如果任务要求交付物，执行 `piki generate` 后检查 `dist/` 下是否出现对应的 `.csv` / `.svg` 文件；"
                "若未出现，先修复 `piki check` 报错再重新生成。\n"
                "6. 只产出与任务相关的文件，不要额外发挥。\n"
                "\n请开始完成这个工程设计任务。"
            )

        if require_generator and not repair_mode and not baseline_mode:
            parts.append(
                "\n**重要**：评分时会检查 `dist/` 下的交付物文件（如 bom.csv、"
                "power-budget.csv、port-map.csv、rack-panel-*.svg）是否已生成。"
                "如果 `piki check` 有错误，`piki generate` 可能失败，请务必先修复所有错误。"
            )

        return "\n".join(parts)

    def build_repair_turn(
        self,
        task_metadata: dict[str, Any],
        project_dir: Path,
        score: Any,
        turn: int,
        max_repair: int,
        diagnostics: list[dict] | None = None,
    ) -> str:
        """Build a self-contained repair prompt for turn N of a repair loop.

        The prompt includes the original requirement, the current workspace
        files, and the diagnostics from the last `piki check`. It is designed
        to be consumed by a stateless CLI actor (Kimi/Gemini) that can inspect
        the workspace directly.
        """
        task_id = task_metadata.get("task_id", "unknown")
        task_name = task_metadata.get("name", "Unnamed")
        requirement = task_metadata.get("requirement", "")

        parts: list[str] = []
        parts.append(
            "You are a hardware engineering design agent. You are continuing "
            "a declarative engineering design task in piki.\n\n"
            f"**Task**: {task_name} ({task_id})\n"
            "Review the requirement and the current workspace, then fix the errors."
        )

        parts.append("## 设计需求\n\n" + requirement)

        # List current files (excluding marker files and hidden/git internals)
        files = sorted(
            p.relative_to(project_dir)
            for p in project_dir.rglob("*")
            if p.is_file()
            and not p.name.startswith(".")
            and ".git" not in str(p.relative_to(project_dir)).split(os.sep)
        )
        parts.append("\n## 当前 workspace 中的文件\n")
        if files:
            for f in files:
                parts.append(f"- `{f}`")
        else:
            parts.append("- (无文件)")

        # Format diagnostics from the last score
        parts.append("\n## 上次 `piki check` 的诊断\n")
        has_errors = False
        if diagnostics:
            for d in diagnostics[: settings.REPAIR_PROMPT_MAX_DIAGNOSTICS]:
                has_errors = True
                rule = d.get("rule_id", "")
                name = d.get("name", "")
                msg = str(d.get("message", "")).splitlines()[0]
                file = d.get("file", "")
                parts.append(f"- `{rule}` {name}: {msg}" + (f" (文件: {file})" if file else ""))
        else:
            for layer in ("L0", "L1", "L2", "L3", "L4"):
                ls = score.layers.get(layer)
                if not ls:
                    continue
                if ls.errors:
                    has_errors = True
                    parts.append(f"\n**{layer}** ({'通过' if ls.passed else '未通过'}):")
                    max_errors = settings.REPAIR_PROMPT_MAX_ERRORS_PER_LAYER
                    for err in ls.errors[:max_errors]:
                        parts.append(f"- {err}")
                    if len(ls.errors) > max_errors:
                        parts.append(f"- ... 还有 {len(ls.errors) - max_errors} 条错误")
        if not has_errors:
            parts.append("所有检查已通过。如果交付物尚未生成，请运行 `piki generate`.")

        remaining = max_repair - turn + 1
        parts.append(f"\n## 剩余轮次\n\n当前是第 {turn} 轮修复，最多还有 {remaining} 轮。")

        parts.append(
            "\n## 操作要求\n\n"
            "1. 直接修改 workspace 中的 YAML 文件以修复上述错误。\n"
            "2. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
            "3. 如果你认为任务已经完成，创建 `.sdhwe.done`。\n"
            "4. 如果你确认无法完成，创建 `.sdhwe.give_up`、`.sdhwe.info_gap` 或 `.sdhwe.no_solution`。\n"
            "5. 只产出与任务相关的文件，不要额外发挥。"
        )
        parts.append(_REPAIR_MARKER_INSTRUCTIONS)

        return "\n".join(parts)

    def build_self_check_turn(
        self,
        task_metadata: dict[str, Any],
        project_dir: Path,
        diagnostics: list[dict],
        turn: int,
        max_rounds: int,
    ) -> str:
        """Build a self-check continuation prompt.

        Injected after the agent submits ``.sdhwe.done`` but ``piki check``
        still reports errors.  The prompt shows only the diagnostics (no full
        score object) and asks the agent to fix the remaining issues.
        """
        task_id = task_metadata.get("task_id", "unknown")
        task_name = task_metadata.get("name", "Unnamed")

        parts: list[str] = []
        parts.append(
            "You are a hardware engineering design agent. You marked the task "
            "as done, but `piki check` still found errors in your design.\n\n"
            f"**Task**: {task_name} ({task_id})\n"
            "Review the diagnostics below and fix the remaining issues in the "
            "workspace YAML files."
        )

        # Diagnostics only — concise, no file listing
        parts.append("\n## `piki check` 诊断\n")
        for d in diagnostics[: settings.REPAIR_PROMPT_MAX_DIAGNOSTICS]:
            rule = d.get("rule_id", "")
            name = d.get("name", "")
            msg = str(d.get("message", "")).splitlines()[0]
            file = d.get("file", "")
            parts.append(f"- `{rule}` {name}: {msg}" + (f" (文件: {file})" if file else ""))

        remaining = max_rounds - turn + 1
        parts.append(
            f"\n## 剩余自检轮次\n\n"
            f"这是第 {turn} 轮自检修复，最多还有 {remaining} 轮。"
        )

        parts.append(
            "\n## 操作要求\n\n"
            "1. 直接修改 workspace 中的 YAML 文件以修复上述错误。\n"
            "2. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
            "3. 修复完成后重新创建 `.sdhwe.done`。\n"
            "4. 如果你确认当前错误无法在当前轮次内解决，创建 `.sdhwe.give_up`。\n"
            "5. 只修复与诊断相关的文件，不要改动已通过检查的部分。"
        )

        return "\n".join(parts)

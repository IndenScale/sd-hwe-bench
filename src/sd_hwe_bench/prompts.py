"""Prompt building for Actor rollout."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

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
    ) -> str:
        """Build the full prompt injected into the actor.

        Args:
            task_metadata: Parsed task.yaml as dict.
            scaffold_dir: Path to the task's scaffold/ directory.
            require_generator: Whether to emphasize deliverable generation.
            output_mode: "cli" for agents that mutate the working directory
                directly; "api" for agents that return YAML code blocks.
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
                    if f.suffix in (".yaml", ".yml", ".toml") and f.stat().st_size < 4096:
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
        else:
            parts.append(
                "\n## 输出要求\n\n"
                "1. 作为设计 agent，请直接在 workspace 目录中创建/修改 YAML 文件；"
                "不需要在 stdout 中输出完整 YAML。\n"
                "2. 务必把设备实例放在 `instances/devices/`，不要放在 `instances/` 根目录。\n"
                "3. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
                "4. 完成后必须先执行 `piki check`，确认无错误后再执行 `piki generate`。\n"
                "5. 只产出与任务相关的文件，不要额外发挥。\n"
                "\n请开始完成这个工程设计任务。"
            )

        if require_generator:
            parts.append(
                "\n**重要**：评分时会检查 `dist/` 下的交付物文件（如 bom.csv、"
                "power-budget.csv、port-map.csv、rack-panel-*.svg）是否已生成。"
                "如果 `piki check` 有错误，`piki generate` 可能失败，请务必先修复所有错误。"
            )

        return "\n".join(parts)

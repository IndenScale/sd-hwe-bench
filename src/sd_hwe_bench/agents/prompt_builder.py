"""Build standardized prompts for agent-driven SD-HWE-Bench tasks.

The prompt includes:
1. System context: piki quick reference (from piki AGENTS.md)
2. Scaffold reference: model definitions available to the agent
3. Task requirement: from task.yaml
4. Output instruction: exact files to produce, piki check to verify
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ── Piki quick reference (compact subset of piki AGENTS.md) ──────────────
_PIKI_QUICKREF = """\
## Piki 快速参考

piki 是声明式系统建模框架。工程师用 YAML 声明设计意图，piki check 自动校验。

### 目录约定
- `instances/` — 实例声明（设备、机柜、PDU、端口、光模块、光纤、端口连接）
- `models/` — 型号默认值（已在 scaffold 中提供，**不要修改**）
- `layouts/` — 布局（设备→机柜 U 位映射）
- `mates/` — 配合声明（rack-mount, power-iec, sfp28-cage, lc-connector）
- `piki.toml` — 项目配置（已在 scaffold 中提供，**不要修改**）

### Instance 文件格式
```yaml
id: SRV-01           # 实例 ID = 文件名（不含 .yaml）
family: ServerFamily  # 或 model: generic-server（二选一）
model: generic-server
name: "服务器-01"     # 可选
status: installed
# 设备特有字段
height_u: 2
tdp_w: 300
# 接口列表（设备 Instance 内嵌）
interfaces:
  - id: eth0
    interface_type: SFP28
    direction: bidirectional
```

### 端口 Instance（独立文件）
```yaml
id: SRV-01-eth0
family: PortFamily
device_id: SRV-01
port_name: eth0
port_type: SFP28
status: installed
```

### 光模块 Instance
```yaml
id: SFP28-SR-S01-ETH0
family: TransceiverFamily
model: sfp28-sr-25g
status: installed
```

### 光纤 Instance
```yaml
id: FIBER-S01-SW01
family: FiberFamily
from_port: SRV-01/eth0
to_port: SW-01/Gi1/0/1
fiber_type: OM4-LC-LC
length_m: 2.0
status: installed
```

### 端口连接 Instance
```yaml
id: CONN-S01-SW01
family: PortConnectionFamily
from_port: SRV-01/eth0
to_port: SW-01/Gi1/0/1
cable_type: OM4-LC-LC
length_m: 2.0
status: installed
```

### Layout (layouts/layout.yaml) — 列表格式
```yaml
- instance: SRV-01
  rack: RACK-A01
  ru_position: 10
  pdu: PDU-A
- instance: SW-01
  rack: RACK-A01
  ru_position: 20
  pdu: PDU-B
```

### Mate (配合) 文件格式
```yaml
mate: rack-mount-19inch   # 配合类型
source: RACK-A01           # 机柜
target: SRV-01             # 设备
```
电源 IEC 配合：
```yaml
mate: power-iec
source: PDU-A
target: SRV-01
target_port: power-a
```
SFP28 cage 配合：
```yaml
mate: sfp28-cage
source: SRV-01
source_port: eth0
target: SFP28-SR-S01-ETH0
```
LC connector 光纤配合：
```yaml
mate: lc-connector
source: FIBER-S01-SW01
source_end: end-a
target: SFP28-SR-S01-ETH0
```

### 验证
完成所有文件后，运行 `piki check` 确认无错误。"""


def build_agent_prompt(
    task_metadata: dict[str, Any],
    scaffold_dir: Path,
    piki_ref_path: Path | None = None,
) -> str:
    """Build a structured prompt for the coding agent.

    Args:
        task_metadata: Parsed task.yaml as dict.
        scaffold_dir: Path to the task's scaffold/ directory.
        piki_ref_path: Optional path to piki AGENTS.md for full reference.

    Returns:
        Prompt string ready to pass to the agent CLI.
    """
    parts: list[str] = []

    # 1. Task header
    task_id = task_metadata.get("task_id", "unknown")
    task_name = task_metadata.get("name", "Unnamed")
    task_type = task_metadata.get("task_type", "comprehensive")
    difficulty = task_metadata.get("difficulty", "medium")

    parts.append(
        f"You are a hardware engineering design agent. Your task is to "
        f"complete a declarative engineering design using piki.\n\n"
        f"**Task**: {task_name} ({task_id})\n"
        f"**Type**: {task_type} | **Difficulty**: {difficulty}\n"
        f"**Plugins**: {', '.join(task_metadata.get('plugins', []))}"
    )

    # 2. Piki quick reference
    parts.append(_PIKI_QUICKREF)

    # 3. Scaffold info
    parts.append("## Scaffold 中已有的文件（只读，请勿修改）\n")
    if scaffold_dir.exists():
        for f in sorted(scaffold_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(scaffold_dir)
                parts.append(f"- `{rel}`")
    else:
        parts.append("- (无 scaffold)")

    # 4. Requirement
    requirement = task_metadata.get("requirement", "")
    parts.append(
        f"\n## 设计需求\n\n{requirement}"
    )

    # 5. Expected output files
    expected = task_metadata.get("expected_files", [])
    deliverables = task_metadata.get("expected_deliverables", [])

    parts.append("\n## 需要产出的文件\n")
    if expected:
        parts.append("必须创建以下文件：\n")
        for f in expected:
            parts.append(f"- `{f}`")
    if deliverables:
        parts.append(f"\n交付物类型: {', '.join(deliverables)}")

    # 6. Output instructions
    parts.append(
        "\n## 工作流程\n\n"
        "1. 阅读 scaffold 中的 `piki.toml` 和 `models/` 了解项目结构\n"
        "2. 按照设计需求，创建 `instances/`、`layouts/`、`mates/` 下的 YAML 文件\n"
        "3. 完成后运行 `piki check` 验证（命令：`piki check`）\n"
        "4. 如果 piki check 报错，根据错误信息修复，重新验证\n"
        "5. **只产出 YAML 文件，不要修改 scaffold 中的任何文件**\n"
        "\n"
        "请开始完成这个工程设计任务。"
    )

    return "\n".join(parts)

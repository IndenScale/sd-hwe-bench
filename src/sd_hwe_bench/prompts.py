"""Prompt building for Actor rollout."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
id: SRV-01
family: ServerFamily
model: generic-server
name: "服务器-01"
status: installed
height_u: 2
tdp_w: 300
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

### Mate（配合）文件格式
```yaml
mate: rack-mount-19inch
source: RACK-A01
target: SRV-01
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

### 验证与交付物
完成所有 YAML 文件后，必须执行：
1. `piki check` 确认无错误
2. `piki generate` 生成交付物（BOM、power-budget、port-map、面板图等）
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
    ) -> str:
        """Build the full prompt injected into the actor."""
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
        parts.append(
            "\n## 输出要求\n\n"
            "1. 直接在 workspace 中创建 YAML 文件，或按路径输出 ```yaml 代码块。\n"
            "2. 每个 YAML 块第一行请用 `# path/to/file.yaml` 标明文件路径。\n"
            "3. 不要修改 scaffold 中的 `models/` 和 `piki.toml`。\n"
            "4. 完成后必须执行 `piki check` 和 `piki generate`。\n"
            "5. 只产出与任务相关的文件，不要额外发挥。\n"
            "\n请开始完成这个工程设计任务。"
        )

        if require_generator:
            parts.append(
                "\n**重要**：评分时会检查交付物文件（如 bom.csv、power-budget.csv、"
                "port-map.csv、rack-panel.svg）是否已生成。请务必调用 `piki generate`。"
            )

        return "\n".join(parts)

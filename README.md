# SD-HWE-Bench

> **Software-Defined Hardware Engineering Benchmark**
>
> Can AI generate correct, compliant, and deliverable engineering designs from natural language requirements? SD-HWE-Bench makes this question measurable, competitive, and reproducible.

---

## What is SD-HWE-Bench?

SD-HWE-Bench evaluates AI agents on **declarative engineering design tasks**. Given a natural language engineering requirement, an agent must produce structured design declarations (YAML) that pass automated rule checks and generate valid engineering deliverables.

It is to hardware engineering what [SWE-Bench](https://www.swebench.com/) is to software engineering — a standardized, open, and automatically scored benchmark that drives AI capability forward.

### The Task

```
Input:  Natural language engineering requirement
Output: Structured design declarations (piki YAML)
Score:  Pass@1 rate across L0-L4 rule checks + deliverable generation
```

### Why HWE needs its own SWE-Bench

Software engineering RLVR (Reinforcement Learning from Verifiable Rewards) works because code has compilers, linters, and test suites — fast, deterministic, and interpretable verifiers. Hardware engineering has even richer verifiable constraints (physics doesn't negotiate), but lacks the infrastructure to expose them to AI agents.

SD-HWE-Bench provides that infrastructure:

| Gap in HWE | What SD-HWE-Bench provides |
|---|---|
| Design context scattered across email, IM, and memory | Self-contained task definitions with all required context |
| CAD/BIM data not operable by LLMs | Text-native YAML declarations that agents can read, write, and diff |
| Verification takes hours (FEA/CFD) | Millisecond-to-second rule engine checks (L0-L4) |
| No structured task definitions | Task instances with clear inputs, expected structure, and scoring rules |

---

## How It Works

```
┌─────────────────┐
│ Natural Language │  "Design a 42U rack deployment with 8 servers..."
│   Requirement    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI Agent       │  Generates piki YAML declarations:
│                  │  instances/, layouts/, mates/, connections/
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  piki check      │  L0: File format validity
│  (Rule Engine)   │  L1: Schema validation
│                  │  L2: Reference integrity
│                  │  L3: Business rules (power budget, U-slot conflicts)
│                  │  L4: Geometry checks (collision detection)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Scoring         │  Pass@1: all rules pass?
│                  │  Partial credit: which rule layers passed?
│                  │  Deliverable quality: BOM, port-map, rack panels?
└─────────────────┘
```

---

## Task Categories

| Category | Description | Example |
|---|---|---|
| **Instance Declaration** | Select correct family/model, declare instances with correct attributes | Declare 8 servers with proper TDP, interfaces |
| **Layout Design** | Place instances in correct physical positions | Rack U-slot assignment without conflicts |
| **Connection Design** | Create correct port-to-port connections with compatible interfaces | Server eth0 → Switch Gi1/0/1 via SFP28 |
| **Mating Design** | Define physical coupling constraints | Rack-mount, power-iec, lc-connector mates |
| **Comprehensive Design** | End-to-end: instances + layout + connections + mates | Full rack deployment from scratch |
| **Incremental Modification** | Modify existing design to meet new requirements | Add 2 more servers without breaking existing constraints |

---

## Scoring

SD-HWE-Bench uses a layered scoring system aligned with piki's L0-L6 check hierarchy:

| Layer | What it checks | Weight |
|---|---|---|
| L0 | File format validity | Required gate |
| L1 | Schema validation | 10% |
| L2 | Reference integrity | 15% |
| L3 | Business rules | 40% |
| L4 | Geometry checks | 20% |
| Deliverables | Generator output validity | 15% |

**Pass@k**: Fraction of tasks where the agent's best-of-k attempts passes all L0-L4 checks.

---

## Getting Started

### Prerequisites

- Python >= 3.11
- [piki](https://github.com/indenscale/piki) >= 0.1.0 (for the rule engine)

### Installation

```bash
git clone https://github.com/indenscale/sd-hwe-bench.git
cd sd-hwe-bench
pip install -e ".[dev]"
```

### Running a Task

```bash
# List available tasks
sd-hwe-bench list

# Run a single task (requires piki project at task path)
sd-hwe-bench run tasks/telecom/rack-deploy-001

# Run full benchmark
sd-hwe-bench run --dataset telecom
```

### Task Structure

```
tasks/telecom/rack-deploy-001/
├── task.yaml          # Task metadata and requirement
├── scaffold/          # Pre-existing project files (models, existing instances)
│   ├── piki.toml
│   ├── models/
│   └── instances/
├── solution/          # Reference solution (hidden from agent)
│   ├── instances/
│   ├── layouts/
│   └── mates/
└── expected/          # Expected deliverables for scoring
    └── bom.csv
```

---

## Domains

| Domain | Status | Task Count |
|---|---|---|
| **Telecom** | Alpha | In progress |
| **Datacenter** | Planned | — |
| **Mechanical (Keyboard)** | Planned | — |
| **HVAC/Fluid** | Planned | — |

---

## Relationship to piki

SD-HWE-Bench is an independent community initiative. It uses [piki](https://github.com/indenscale/piki) as the default declarative modeling language and rule engine, but the benchmark's task definitions, scoring methodology, and governance are separate.

- piki provides: YAML DSL, rule engine (L0-L4 checks), generator pipeline
- SD-HWE-Bench provides: Task datasets, scoring harness, leaderboard, community governance

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the task contribution workflow. We welcome:

- **Task proposals**: New engineering design scenarios with requirements and solutions
- **Domain plugins**: New engineering domains (HVAC, structural, electrical)
- **Scoring improvements**: Better partial credit, deliverable quality metrics
- **Leaderboard submissions**: Run your agent and submit results

---

## Governance

SD-HWE-Bench is community-governed. Initial maintenance by piki core team, transitioning to a technical committee + domain maintainers model when task count exceeds 200.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Citation

```bibtex
@misc{sd-hwe-bench,
  title = {SD-HWE-Bench: A Benchmark for Software-Defined Hardware Engineering},
  author = {SD-HWE-Bench Contributors},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/indenscale/sd-hwe-bench}
}
```

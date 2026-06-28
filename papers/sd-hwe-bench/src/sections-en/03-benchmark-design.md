# 3. Benchmark Design

This chapter describes the overall design philosophy, core components, and task lifecycle of SD-HWE-Bench. Section 3.1 reviews key concepts of the Engineering as Code paradigm; Section 3.2 introduces the three-layer benchmark architecture; Section 3.3 describes task definition, sourcing, and quality assurance; Section 3.4 presents the Actor abstraction and evaluation pipeline.

## 3.1 Engineering as Code Core Concepts

SD-HWE-Bench is built on the **Engineering as Code (EaC)** paradigm [@song2025eac]. EaC's core claim is that the bottleneck in AI for physical engineering is not model capability but the lack of a code-like, computable design representation. The paradigm comprises three mutually coupled components:

### 3.1.1 ADL: Assembly Definition Language

**ADL** is a declarative domain-specific language for uniformly describing physical engineering designs. It models "what parts exist, how they relate, and where they sit" in plain text. ADL contains three orthogonal sub-languages:

- **PDL (Part Definition Language)**: defines part types. Each Part is a typed entity with ports (electrical/fluid/mechanical/signal), attributes (power, weight, dimensions, materials), and compatibility constraints (interface types, compatible pin families).
- **PML (Part Mating Language)**: defines relationships between parts—electrical connections (power/signal/data), physical mating (bolt/snap-fit/rail-mount), and hierarchical containment (sub-assembly → parent assembly).
- **PLL (Part Layout Language)**: defines spatial arrangement—positions, orientations, and layout constraints (rack U-range, spacing, collision avoidance).

The three sub-languages are orthogonal: changing a Part's power attribute does not affect its layout declaration; changing wiring does not require redefining Part types. This orthogonality is the architectural basis for DTS layered checking.

### 3.1.2 DTS: Design Test Suite

**DTS (Design Test Suite)** is EaC's quality gate engine—it shifts design rule checking upstream to the design generation phase, providing agents with layered deterministic feedback. Unlike traditional Automated Compliance Checking (ACC), DTS checks design *declarations* (ADL text) rather than geometrically instantiated products, naturally avoiding false collisions and naming dependencies.

DTS layers, detailed in §5, are:

- **L0 (Syntax)**: YAML validity, required field presence, expected file existence.
- **L1 (Semantic)**: Schema validation, type system consistency, legal attribute ranges.
- **L2a (Identity & Foreign Key Integrity)**: Part/Port reference resolvability, foreign key existence, tag uniqueness (5 rules).
- **L2b (Interface & Port Compatibility)**: Interface type compatibility, port device existence, connection endpoint existence and type matching (7 rules).
- **L2c (Mate & Catalog Constraints)**: Physical mate type matching, catalog reference validity, EOL device prohibition (4 rules).
- **L3 (Engineering Constraints & Cross-Entity Coupling)**: PDU power budget, phase balance, cable matching—plus v3 cross-entity coupling rules (Spine-Leaf full-mesh topology integrity, multi-site frequency reuse distance), extending constraints from single entities to multi-entity graphs (7 rules).
- **L-Numeric (Numerical Assertions)**: Tolerance-based comparison of key numerical values in report files (EIRP, coverage radius, safety factors), capturing LLM computation fidelity errors. Driven by `numeric_assertions` in task.yaml (weight 0.10).
- **L4 (Geometric & Spatial)**: 3D collision detection, U-slot conflict, rack capacity, device dimension fit, maintenance clearance (5 rules).
- **L5/L6 (Deliverable)**: Successful `piki generate` execution with all expected deliverables present.

DTS serves dual roles in SD-HWE-Bench: (1) as a scorer (Critic), providing deterministic scores for agent outputs; (2) as a repair feedback signal, enabling agents to iteratively fix designs based on DTS error reports.

### 3.1.3 piki: EaC's Open-Source Runtime

**piki** is the open-source reference implementation of the EaC paradigm, providing ADL parsing, DTS checking, and deliverable generation (BOM tables, 3D previews, wiring diagrams). SD-HWE-Bench uses piki as both the scoring engine and the containerized execution environment (see §3.4).

## 3.2 Three-Layer Benchmark Architecture

SD-HWE-Bench's overall architecture has three layers:

```text
┌─────────────────────────────────────────────────┐
│                 Task Layer                       │
│  tasks/<domain>/<task>/                          │
│  ├── task.yaml     (metadata, requirement,       │
│  │                  scoring definition)          │
│  ├── scaffold/     (agent initial context)       │
│  └── solution/     (reference, hidden from agent)│
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│              Evaluation Layer                    │
│  SyntaxCritic(L0) → PikiCritic(L1-L4)           │
│  → NumericCritic → DeliverableCritic(L5/L6)      │
│  → RubricCritic(LLM)                             │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│            Execution Layer                       │
│  SandboxRunner (docker/podman/none)              │
│  Container image: sd-hwe-bench-piki:latest       │
└─────────────────────────────────────────────────┘
```

**Figure 1**: SD-HWE-Bench three-layer architecture.

The evaluation layer consists of five Critics executed in sequence:

1. **SyntaxCritic (L0)**: validates YAML syntax and expected file presence.
2. **PikiCritic (L1-L4)**: invokes `piki check --format json`, mapping rule failures to DTS layers (L1/L2a/L2b/L2c/L3/L4). L3 layer in v3 is extended to cover cross-entity coupling rules (Spine-Leaf topology integrity, multi-site frequency reuse distance).
3. **NumericCritic (L-Numeric)**: performs tolerance-based comparison of key numerical values in report files (EIRP, coverage radius, wind-load safety factors), capturing LLM computation fidelity errors. Driven by `numeric_assertions` in task.yaml (weight 0.10).
4. **DeliverableCritic (L5/L6)**: invokes `piki generate` and checks for expected deliverable files.
5. **RubricCritic (LLM-as-Judge)**: qualitative evaluation against task-defined rubrics (diagnostic only, not counted in overall_score).

The unified scoring entry point `score_task()` aggregates results from all Critics.

## 3.3 Task Definition and Quality Assurance

### 3.3.1 Task Types

SD-HWE-Bench defines six task types:

- **instance-declaration**: create Part instances with specified attributes.
- **layout-design**: allocate Part positions in 3D space satisfying U-slot, spacing, and thermal constraints.
- **connection-design**: declare electrical/fluid/signal connections between Parts.
- **mating-design**: declare physical mating relationships (bolt, snap-fit, rail).
- **comprehensive**: simultaneous coverage of multiple capability dimensions.
- **incremental**: localized modifications to an existing design.

Each task is annotated with `difficulty` (easy/medium/hard), determined by the number of files modified, DTS layers covered, and degree of cross-domain coupling.

### 3.3.2 Task Sourcing: Canonical Projects + Commit Extraction

Following SWE-bench's task generation paradigm, SD-HWE-Bench tasks are sourced from the commit history of **canonical ADL projects**—complete ADL projects carefully authored by domain experts, whose commit history simulates real design iterations (each commit is a meaningful, complete increment).

The task extraction pipeline (`tools/extract_tasks.py`) automatically generates tasks from adjacent commit pairs:

- **Requirement**: derived from commit message and diff content.
- **Scaffold**: checkout to commit k state.
- **Solution**: commit k+1 complete state.
- **DTS validation**: `piki check` on solution, ensuring all DTS layers pass.

Each auto-extracted task undergoes manual review: requirement accuracy, scaffold completeness, solution correctness, difficulty annotation, and rubric supplementation. Non-conforming tasks are discarded.

## 3.4 Actor Abstraction and Evaluation Pipeline

### 3.4.1 Actor Interface

All Actors implement a unified Python interface:

```python
class Actor(ABC):
    @abstractmethod
    def run(self, prompt: str, workspace_root: Path) -> ActorResult:
        """Execute design task in workspace_root.
        Agent may directly modify files in workspace.
        Returns ActorResult with output path, logs, and interaction trace."""
        ...
```

New Actors are plug-and-play: only `run()` needs to be implemented.

### 3.4.2 Evaluation Pipeline

Each rollout's evaluation follows six phases: Prepare → Scaffold → Prompt → Run → Score → Archive.

Agent generation runs locally; DTS scoring runs in Docker containers (`sd-hwe-bench-piki:latest`) to ensure cross-environment reproducibility. SD-HWE-Bench uses a **thin sandbox** pattern: the agent does not directly control the sandbox but requests `piki check` and `piki generate` through the fixed CLI interface. The rule engine, test cases, and scoring logic inside the sandbox are entirely non-writable by the agent—preventing reward hacking and ensuring all Actors are evaluated against the same immutable scoring standard.

# 4. Dataset

This chapter describes SD-HWE-Bench's dataset construction process: pipeline overview (4.1), canonical projects (4.2), task extraction and quality control (4.3), statistical characteristics (4.4), train/val/test split (4.5), and comparison with related benchmarks (4.6).

## 4.0 Specification-Driven Task Construction

A core design principle of SD-HWE-Bench is **specification-driven design**: agents must actively consult project design specifications (rather than relying solely on prompt content) to complete tasks. This is the key mechanism distinguishing "instruction-following capability" from "engineering design capability."

Implementation: each canonical project's `docs/` contains design specification documents defining field names, directory structures, constraint rules, and design workflows. `tools/extract_tasks.py` copies these docs into every task's `scaffold/` and `solution/`. PromptBuilder adjusts output format by Actor type—CLI Actors receive guidance to read spec files actively; API Actors receive inlined spec content.

## 4.1 Construction Pipeline Overview

SD-HWE-Bench follows a four-phase dataset construction pipeline:

```text
Canonical Project Authoring → Commit Serialization → Task Extraction → Validation + Review
```

Final dataset: 33 tasks across 3 sub-domains.

### 4.1.1 v2 Expansion (2026-06-27)

Based on diagnostic analysis of the initial 34-task experiment (CLI Actor saturation, L2 single-layer overload, excessive easy tasks), v2 introduced:

1. **5 compound easy tasks** (telecom-easy-compound-001~005): incremental dependency chains with 3-4 layers.
2. **4 emergent constraint tasks** (telecom-emergent-001~004): constraints not explicitly stated in requirements; agents must infer from scaffold.
3. **3 cross-disciplinary tasks** (telecom-cross-001~003): multi-domain constraints (electrical + structural + fire safety).
4. **L2 sub-layer split**: 16 rules split into L2a (5 rules, identity/FK), L2b (7 rules, interface/port), L2c (4 rules, mate/catalog), each 5% weight.
5. **Incremental chain merge (v2.1)**: 29 commit-by-commit tasks merged into 11 stage tasks. Easy: 39%→25%, hard: 15%→29%.

### 4.1.2 v3 Deep Expansion (2026-06-28)

Building on v2, v3 further extends canonical project depth and constraint complexity:

1. **3 site deep tasks** (site-stage5~7): tower wind-load verification (structural engineering, lattice tower solidity ratio and overturning safety factor), BBU thermal redundancy (thermal management, cabinet surface area temperature rise and throttling risk), three-sector spectrum interference coordination (EMC, ACIR computation and coverage overlap ΔRSSI).
2. **1 dc Spine-Leaf networking task** (dc-stage5): 2 Spine × 2 Leaf full-mesh topology, convergence ratio ≤ 3:1, validated by the new TELECOM-TOPOLOGY-001 cross-entity coupling rule.
3. **L-Numeric scoring layer**: NumericCritic performs tolerance-based comparison of key numerical values (EIRP, coverage radius, safety factor, surface area, ΔRSSI), capturing LLM computation fidelity errors.
4. **Cross-entity coupling rules**: piki rules extended from single-entity constraints (intra-rack/cabinet) to multi-entity graph constraints (Spine-Leaf full-mesh, multi-site frequency reuse distance). Two new rules (TELECOM-TOPOLOGY-001, TELECOM-SPECTRUM-001), total rules: 30→32.

## 4.2 Canonical Projects

SD-HWE-Bench builds tasks from three canonical ADL projects:

### 4.2.1 Telecom Rack Expansion

**Domain**: telecom infrastructure. Simulates complete deployment of a 42U standard telecom rack from empty to fully loaded. 15 commits progressively add PDUs, devices, ports, transceivers, fibers, and cross-rack connections. Includes a comprehensive design specification (`rack-design-spec.md`).

### 4.2.2 Data Center Deployment

**Domain**: data center facilities. Covers server room layout (12m×8m), two rack rows (4 racks each), dual-PDU power distribution, compute node deployment, in-row cooling, and Spine-Leaf network topology. 9 commits. Design specification: `dc-design-spec.md`.

### 4.2.3 Outdoor Base-Station Site

**Domain**: outdoor telecom sites. Covers IP65 outdoor cabinet, DC power system, BBU, RRU/antenna installation, feeder cables, lightning protection grounding, RF parameter configuration, link budget calculation, sector planning, tower wind-load verification, thermal redundancy analysis, and spectrum interference coordination. 13 commits. Design specification: `site-design-spec.md`.

## 4.3 Task Extraction and Quality Control

The extraction tool processes adjacent commit pairs from each canonical project's `task_manifest.yaml`. Quality control includes requirement accuracy verification, scaffold completeness checks, solution `piki check` validation, difficulty annotation, and rubric supplementation. All 33 reference solutions pass the full regression test suite (33/33 pass).

## 4.4 Dataset Statistics

| Dimension | Value |
|-----------|-------|
| Total tasks | 33 |
| Domains | 1 (telecom), 3 sub-domains |
| Canonical projects | 3 |
| POC manual tasks | 5 |
| Task type distribution | instance-declaration: 5, mating-design: 2, connection-design: 2, layout-design: 2, comprehensive: 22 |
| Difficulty distribution | easy: 7, medium: 13, hard: 13 |
| Avg scaffold YAML lines | 238 |
| Avg scaffold YAML files | 24 |
| Avg DTS rules/task | 32 (L1 schema, L2a/L2b/L2c identity/interface/mate, L3 engineering + cross-entity, L4 geometric, L-Numeric, L5/L6 deliverable) |
| Avg requirement length | 31 words (incremental), 60 words (comprehensive) |

Table: SD-HWE-Bench dataset statistics. {#tbl:dataset-stats}

### 4.4.1 Key Task Characteristics

1. **Real engineering tasks**: sourced from canonical ADL project commit histories, not synthetic toy problems.
2. **Multi-physics coupling**: single tasks may involve electrical, structural, thermal, and EMC constraints simultaneously.
3. **Long context**: scaffolds contain 800-3000+ lines of ADL declarations.
4. **Executable digital models**: each task binds to 32 DTS rule assertions with millisecond-to-second evaluation latency.
5. **Cross-abstraction editing**: modifications may span PDL, PML, and PLL layers.
6. **Sustainable updates**: any new canonical project commit can be auto-extracted into a new task.

## 4.5 Dataset Splits

Tasks are split by canonical project: certain commit ranges for training/validation, complete retained projects for testing—ensuring no Part type or engineering scenario is shared across splits.

## 4.6 Comparison with Related Benchmarks

| Dimension | SWE-bench | SWE-bench M | HumanEval | SD-HWE-Bench |
|-----------|-----------|-------------|-----------|-------------|
| Task source | Open-source repos | Open-source repos | Hand-written | Canonical ADL projects |
| Domain | Python code | JS/TS + vision | Algorithms | Physical engineering design |
| Context scale | Hundreds–tens of thousands of lines | Same | Few-line signatures | 800-3000+ lines ADL |
| Feedback type | pytest pass/fail | pytest + vision | Input/output pairs | DTS L0-L4 layered (32 rules/task) |
| Multi-domain coupling | None | Limited | None | Electrical/thermal/structural/EMC |
| Geometric constraints | None | Limited | None | Collision/U-slot/spacing |
| Task expansion | Depends on new issues | Same | Hand-write | Auto-extract from commits |

Table: Dataset construction paradigm comparison. {#tbl:dataset-comparison}

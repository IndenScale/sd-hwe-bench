# ESA: Engineering Static Analysis

Engineering Static Analysis (ESA) is the mechanism that makes EaC's shift-left quality strategy executable. It consumes ADL declarations and checks deterministic rules before design submission, moving compliance review from downstream inspection to upstream gating.

## From ACC to ESA

Traditional Automated Compliance Checking (ACC) operates on completed CAD/BIM models or IFC files [@eastman2009acc; @zhang2019acc]. This creates three structural problems: design logic is frozen into geometry (information loss); violations are discovered only after multi-discipline coupling (high feedback cost); and agents receive no reward signal during generation (no RLVR support).

Model-based ACC also suffers from two semantic deficiencies (§2.2.1). Geometric clash detection produces massive false positives because the model has no representation of **intended** relationships; rule engines rely on standardized naming conventions, forcing costly pre-check remodeling. Even in ACC's most mature subdomain (building fire code), graph-reasoning methods reach only 84.3% accuracy [@xiao2025bimgraph]—not an algorithmic ceiling, but a representational one.

ESA addresses these problems at the root by checking ADL **declarations** rather than geometry. It operates on Part identity and Family schema, explicit Mate relationships, and a layered L0–L4 rule hierarchy. The result is a checker that consumes design **intent**, analogous to a compiler type checker consuming source code rather than a post-hoc binary analyzer inferring types.

### Concrete Example: Rack Power Budget

The following comparison checks whether the total power of devices in a rack exceeds its PDU capacity.

**Model-based ACC approach**. The checker must parse the BIM model, identify rack and server objects, determine containment via geometry or naming conventions, extract power ratings from property sets, and compare. Every step depends on model quality and naming standards; a server named `DELL-R740-SRV01` instead of `SERVER-R740-01` may be missed, and project-specific shared parameters require per-project rule customization.

**ESA approach**. The rule iterates over `PDUFamily` instances, traverses their `outputs`, accumulates connected loads' `rated_power_w`, and compares against each output's rating. The rule is 12 lines of Python, independent of naming conventions, and valid for any project using the same Part Family. Diagnostics pinpoint the specific PDU output and over-limit loads.

This is not a comparison of speed, but of whether the rule can be **authored** without per-project customization.

## Why "Static Analysis"

ESA borrows the term "static analysis" from software engineering because it shares three characteristics:

1. **No physical simulation is executed**. What is reasoned about is declarations and constraints, not simulated physics.
2. **Deterministic results**. The same ADL declarations always produce the same pass/fail verdict.
3. **Low cost**. Millisecond to sub-hundred-millisecond completion, suitable for pre-commit hooks and CI gating.

Just as lint and type checking cannot replace unit tests, ESA cannot replace CAE/CFD or human review. It intercepts a large volume of low-level, deterministic errors at the front end, allowing expensive validation to focus on issues that truly require expert judgment.

## Four Operational Principles

ESA follows four principles designed to make it usable in real engineering practice.

**Principle I: Rules are waivable**. Physical boundary conditions cannot be exhausted by a finite rule set. Authorized engineers may waive rules, but each waiver is recorded in design history and triggers downstream reinforced verification, turning informal exceptions into auditable risk management.

**Principle II: Focus on baseline rules**. Initial deployment targets mechanical, deterministic clauses—fire separation, egress width, power budget, U-position conflicts—with binary verdicts and minimal dispute space. The rule library supports modular composition of national codes, local standards, and enterprise controls.

**Principle III: Shift-left and signal-to-noise optimization**. Like compiler warnings, ESA intercepts low-value errors at design time, preventing propagation into downstream artifacts. Severity tiers and suppression directives (`# noqa`) let teams tune the signal-to-noise ratio.

**Principle IV: Declarative rule authoring**. Rules use structured decorators so domain experts can compose and extend them without understanding the checker engine internals.

## Rule Hierarchy: L0–L6

ESA partitions all checkable rules into a six-layer hierarchy, with clear ownership boundaries at each layer:

| Layer | Name | Scope | Responsible | Example |
|-------|------|-------|-------------|---------|
| L0 | Lexical | Single ADL file | ADL Loader | YAML syntax validity |
| L1 | Schema | Single ADL file | ADL Loader | Required fields, type constraints |
| L2 | Semantic Reference | Cross-file | ESA Core | Part references exist, Mate types compatible |
| L3 | Business Rule | Cross-file | ESA Core | Power budget, U-position conflict, fire separation |
| L4a | Lightweight Geometry (AABB) | Cross-file | ESA Extension | AABB-based spatial conflicts, clearance checks |
| L4b | Precise Geometry | Cross-file | Downstream CAD | Precise clash detection (requires CAD kernel) |
| L5 | Physical Simulation | Cross-file | Downstream CAE/CFD | Structural, thermal, fluid analysis |
| L6 | Human/Expert Sign-off | Project-level | Downstream Process | Professional engineer stamp, compliance sign-off |

Table: ESA rule hierarchy (L0–L6) and ownership boundaries {#tbl:esa-hierarchy}

ESA's core scope covers L2–L4a. L0–L1 are handled by the ADL loader (see §4). L4b–L6 belong to downstream verification (see §5.8).

The following table shows the L2–L4a rules implemented in the piki prototype for telecom rack scenarios:

| Rule ID | Name | Layer | Description |
|---------|------|-------|-------------|
| `INTERFACE-COMPAT-001` | Interface type compatibility | L2 | Mate interface types must match |
| `POWER-001` | Rack PDU power budget | L3 | PDU load must not exceed capacity threshold |
| `TELECOM-RACK-001` | U-position conflict | L3 | Device U-positions within the same rack must not overlap |
| `TELECOM-RACK-002` | Rack capacity | L3 | Total device height must not exceed rack available U-positions |
| `TELECOM-COLLISION-001` | Intra-rack 3D collision | L4a | AABB-based spatial conflict detection |
| `TELECOM-WEIGHT-001` | Rack load bearing | L3 | Total weight must not exceed rack load capacity |
| `TELECOM-FLOOR-002` | Maintenance aisle width | L4a | Same-row rack spacing must meet maintenance aisle requirements |

Table: L2–L4a rules implemented in the piki prototype for telecom rack scenarios {#tbl:telecom-rules}

Rules are registered via the `@rule(rule_id, name, priority, severity)` decorator. Layered registration allows projects to enable only L2 during logical design, and add L3–L4a during detailed layout phase.

## Waiver Mechanism

The current piki prototype supports `--skip <rule_id>` and `warning_only` configuration; the target design records each waiver as a YAML file with fields for `rule_id`, `target`, `scope`, `rationale`, `author`, `approver`, `expires_at`, `downstream_tasks`, and audit trail. Waivers are committed alongside ADL files and reviewed in PRs. A waiver is not a bypass—it is a transfer of responsibility from the deterministic rule engine to higher-cost verification activities.

## Diagnostic Output

ESA produces a unified diagnostic structure consumable by terminals, CI dashboards, IDEs, and PR bots. On the telecom rack sample, `piki check` completes in under 200ms, returning structured pass/warn/fail results with file-level locations. The JSON format is LSP-compatible and can drive terminal summaries, JUnit XML dashboards, IDE overlays, and GitHub Checks API annotations.

## CI/CD and Pre-commit Integration

ESA runs in standard CI/CD workflows. A typical EaC pipeline stages checks by cost: lint and parse (L0) per commit; schema (L1), link (L2), and rule checks (L3–L4a) per PR; artifact build post-merge; and nightly regression including geometry and CAE/CFD. Pre-commit hooks mirror the cheaper checks locally, giving engineers sub-second feedback before commit.

## Downstream Verification Protocol: ESA's Boundary

ESA's scope is intentionally limited to checks deterministic from declarations alone: L2–L3 (core) and L4a (lightweight geometry). L0–L1 are handled by the ADL loader; L4b (precise clash detection), L5 (physical simulation), and L6 (expert sign-off) belong to **downstream verification**. The EaC workflow architecture proposes a clean interface: after `piki check` passes, CI actions export ADL declarations to STEP/USD or mesh formats and invoke CAD/CAE tools; downstream findings flow back as ESA-compatible Diagnostics referencing specific ADL identifiers, without being merged into the ESA rule library.

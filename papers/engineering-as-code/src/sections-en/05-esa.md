# ESA: Engineering Static Analysis

Engineering Static Analysis (ESA) is the mechanism that makes EaC's shift-left quality strategy executable. It consumes ADL declarations and checks deterministic rules before design submission, moving compliance review from downstream inspection to upstream gating.

## From ACC to ESA

Traditional Automated Compliance Checking (ACC) operates on completed CAD/BIM models or IFC files [@eastman2009acc; @zhang2019acc]. This creates three structural problems:

1. **Information loss**. Design logic is frozen into geometry; reverse-extracting functional relationships is lossy.
2. **High feedback cost**. Violations are discovered only after the design has been coupled into a multi-discipline model.
3. **No RLVR signal**. ACC can only judge completed designs; it cannot reward Agents during generation.

Beyond these timing issues, model-based ACC suffers from two deeper semantic deficiencies (see §2.2.1). First, pure geometric clash detection produces massive false positives—pipes passing through walls, tray crossings—because the model has no representation of **intended** relationships. Second, rule-based ACC relies on standardized naming conventions, forcing costly pre-check model rework that erodes the very efficiency ACC was supposed to provide.

ESA addresses these problems at the root. It checks ADL declarations—not geometry—and therefore has access to:

- **Part identity and type** (Family schema), allowing rules to operate on semantic categories (e.g., "any `PDUFamily` instance") rather than naming patterns (e.g., "any object named `PDU-*`");
- **Explicit Mate relationships** (PML), allowing the checker to know which pairs of objects are **intended** to interact—and to exclude them from clash detection (a pipe passing through a wall is a declared Mate, not a clash to suppress);
- **Layered checking** (L0–L4), allowing syntax errors, reference errors, and business rule violations to be caught at distinct stages, each with targeted diagnostics.

The result is not a faster ACC. It is a checker that operates on a fundamentally different input: design **intent** rather than design **instantiation**. This distinction—checking declarations vs. checking models—is identical to the distinction that makes a compiler type checker fundamentally different from a post-hoc binary analysis tool. The compiler has access to the type system; the binary analysis tool must infer types. Even in ACC's most mature subdomain (building fire code), state-of-the-art graph reasoning methods achieve only 84.3% accuracy [@xiao2025bimgraph] and frequently fail on rules involving multi-step spatial reasoning chains—this is not the ceiling of algorithms, but the ceiling of the semantic bandwidth of geometric representation.

### Concrete Example: Rack Power Budget

The following comparison checks whether the total power of devices in a rack exceeds its PDU capacity.

**Model-based ACC approach**. The checker must: (a) parse the BIM model to identify rack objects, (b) identify server objects, (c) determine which servers belong in which rack via geometric containment or naming conventions, (d) extract power ratings from property sets (if populated), (e) extract PDU ratings (if populated), (f) compare. Steps (a)–(e) depend on model quality and naming standards. If a server is named `DELL-R740-SRV01` instead of `SERVER-R740-01`, the rule engine may miss it. If power ratings are stored in project-specific shared parameters, rules must be customized per project.

**ESA approach**. The rule iterates over all `PDUFamily` instances, traverses their `outputs`, accumulates the `rated_power_w` of connected loads, and compares against each output's `rated_power_w`. The rule is 12 lines of Python, independent of naming conventions, and valid for any project using the same Part Family. Diagnostics pinpoint the specific PDU output and over-limit loads.

This is not a comparison of speed. This is a comparison of whether the rule can be **authored** without per-project customization.

## Why "Static Analysis"

ESA borrows the term "static analysis" from software engineering because it shares three characteristics:

1. **No physical simulation is executed**. What is reasoned about is declarations and constraints, not simulated physics.
2. **Deterministic results**. The same ADL declarations always produce the same pass/fail verdict.
3. **Low cost**. Millisecond to sub-hundred-millisecond completion, suitable for pre-commit hooks and CI gating.

Just as lint and type checking cannot replace unit tests, ESA cannot replace CAE/CFD or human review. It intercepts a large volume of low-level, deterministic errors at the front end, allowing expensive validation to focus on issues that truly require expert judgment.

## Four Operational Principles

ESA follows four principles designed to make it usable in real engineering practice.

**Principle I: Rules are waivable**. Physical boundary conditions cannot be exhausted by a finite rule set. ESA allows authorized engineers to waive specific rules, but every waiver must be recorded as part of the design history and trigger downstream reinforced verification (e.g., higher-fidelity CAE simulation or physical testing). The goal is to transform "beyond-spec" behavior from informal decisions into auditable risk management.

**Principle II: Focus on baseline rules**. Initial deployment should focus on mechanical, deterministic clauses: fire separation distances, egress clear width, minimum clear height, power budget, U-position conflicts. These rules have binary verdicts, minimal dispute space, and high automation returns. The rule library should support modular configuration, allowing projects to compose national codes, local standards, and enterprise internal controls.

**Principle III: Shift-left and signal-to-noise optimization**. Software engineering, through CI/CD practices, has validated that lint and type checking intercept low-value errors before commit, freeing code review to focus on architecture and logic. ESA applies this same principle: catching rule violations at design time prevents them from propagating into downstream artifacts, reducing costly rework cycles. Rule severity tiers (error, warning, info) and suppression directives (`# noqa`) allow teams to tune the signal-to-noise ratio, just as engineering teams tune compiler warning levels.

**Principle IV: Declarative rule authoring**. Rules should use structured decorators and modular organization so that domain experts can compose and extend rules without understanding the checker engine internals. See Appendix A for the full rules directory structure.

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

The structured waiver system is part of ESA's design; the current piki prototype only supports `--skip <rule_id>` and `warning_only` configuration. The target design records each waiver as a YAML file containing the following fields:

| Field | Meaning | Example |
|-------|---------|---------|
| `rule_id` | The waived rule | `TELECOM-FLOOR-002` |
| `target` | Affected objects | `RACK-A01`, `RACK-A02` |
| `scope` | Scope (single file, branch, global) | `branch:feature/legacy-room` |
| `rationale` | Technical and business justification | "Constrained by existing building column grid" |
| `author` | Requester | Engineer ID |
| `approver` | Authorizer | Senior engineer / compliance lead |
| `expires_at` | Expiration (optional) | `2027-06-20` |
| `downstream_tasks` | Downstream reinforced verification tasks | `["CFD-thermal-sim", "site-survey"]` |
| `created_at` / `commit` | Audit trail | Timestamp and Git hash |

Table: Structured waiver file fields {#tbl:waiver-fields}

Waivers are committed alongside ADL files and reviewed in PRs. A waiver is not a bypass of the rule—it is a transfer of responsibility from the deterministic rule engine to higher-cost verification activities. If downstream tasks fail, the waiver is reconsidered.

## Diagnostic Output

ESA produces a unified diagnostic structure consumable by terminals, CI dashboards, IDEs, and PR bots. On the telecom rack sample, `piki check` completes in under 200ms on a laptop, returning 1 warning and 29 passes:

```text
[PASS] INTERFACE-COMPAT-001: Interface type compatibility check
...
[FAIL] TELECOM-FLOOR-002: Rack maintenance aisle width check
       Racks RACK-A01 and RACK-A02 same-row spacing -600.0mm is less than required 600.0mm
============================================================
Total: 0 errors, 1 warning, 29 passed
============================================================
```

The JSON format exposes the same data, is LSP-compatible, and can drive terminal summaries, JUnit XML dashboards, IDE overlays, and GitHub Checks API annotations.

## CI/CD and Pre-commit Integration

ESA is designed to run within workflows that software engineers already use. A typical EaC CI/CD pipeline consists of the following stages:

| Stage | Trigger | Content | Failure Policy |
|-------|---------|---------|----------------|
| Lint | Per commit | YAML/TOML formatting, trailing whitespace, naming conventions | Block commit |
| Parse | Per commit | ADL syntax (L0) | Block merge |
| Schema Check | Per commit | pydantic / JSON Schema (L1) | Block merge |
| Link Check | Per PR | Reference integrity, Mate consistency (L2) | Block merge |
| Rule Check | Per PR | Business and lightweight geometry rules (L3–L4a) | Block merge |
| Artifact Build | Post-merge | BOM, drawings, port maps | Report warning |
| Nightly Regression | Scheduled | Full sample suite, geometry, CAE/CFD | Report and notify |

Table: EaC CI/CD pipeline stages and failure policies {#tbl:cicd-stages}

Pre-commit hooks mirror the cheaper checks locally, giving engineers sub-second feedback before commit. The same configuration file drives both pre-commit and CI, preventing "passes locally, fails CI" inconsistencies.

## Downstream Verification Protocol: ESA's Boundary

ESA's scope is intentionally limited to checks that can be performed deterministically from declarations alone. It covers L2–L3 (core) and L4a (lightweight geometry extension). L0–L1 are handled by the ADL loader. L4b (precise geometric clash detection, requiring a CAD kernel), L5 (physical simulation, requiring CAE/CFD solvers), and L6 (human/expert sign-off) belong to **downstream verification**—critical to engineering correctness, but not part of ESA.

The integration of these downstream stages follows a protocol that is an architectural proposition of the EaC workflow architecture, not a feature of the current piki prototype:

1. **Trigger**. After `piki check` passes, CI Pipeline Actions invoke downstream tools—exporting ADL declarations as STEP/USD and running precise clash detection (L4b) with a CAD kernel, or generating mesh files and invoking CFD/FEA solvers (L5).
2. **Feedback loop**. Downstream findings flow back into the ADL project in a Diagnostic format compatible with ESA, referencing specific Instance, LayoutEntry, or Mate identifiers. This means downstream tools only need to produce structured diagnostic output; they do not need to understand ADL internals.
3. **Separation of concerns**. Downstream findings do not feed back into the ESA rule library. They form independent L4b/L5 diagnostic collections, just as SPICE simulation results and DRC reports are independent, complementary verification channels in chip design. Waivers based on downstream findings reference downstream diagnostics, not ESA rule IDs.

This protocol defines the **interface** between EaC's design-time verification and the broader physical verification ecosystem. It does not require piki to be a CAD or CAE platform; it requires piki to produce consumable outputs and a standardized diagnostic envelope.

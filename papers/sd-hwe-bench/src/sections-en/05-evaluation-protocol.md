# 5. Evaluation Protocol

This chapter defines SD-HWE-Bench's evaluation protocol: DTS layered scoring (5.1), rubric evaluation (5.2), score aggregation and pass@k (5.3), evaluation context settings (5.4), repair loop protocol (5.5), and auxiliary metrics (5.6).

## 5.1 DTS Layered Scoring System

SD-HWE-Bench's core scoring engine is **DTS (Design Test Suite)**, which decomposes design correctness into eight layers, progressing from text format to physical behavior.

### 5.1.1 L0: Syntax

Validates YAML legality and expected file existence. Latency: <10ms.

### 5.1.2 L1: Semantic (Schema & Type System)

ADL Schema validation, type system consistency, legal attribute ranges. Latency: <50ms.

### 5.1.3 L2a: Identity & Foreign Key Integrity

Part/Port reference resolvability, foreign key existence, tag uniqueness. 5 rules. Latency: <100ms.

### 5.1.4 L2b: Interface & Port Compatibility

Interface type compatibility, port device existence, connection endpoint existence and type matching. 7 rules.

### 5.1.5 L2c: Mate & Catalog Constraints

Physical mate type matching, catalog reference validity, EOL device prohibition. 4 rules.

### 5.1.6 L3: Engineering Constraints & Cross-Entity Coupling

PDU power budget (≤80% threshold), phase balance, cable matching—plus v3 cross-entity coupling rules: Spine-Leaf full-mesh topology integrity (TELECOM-TOPOLOGY-001), multi-site frequency reuse distance (TELECOM-SPECTRUM-001). 7 rules. Latency: <500ms.

### 5.1.7 L-Numeric: Numerical Assertions

Tolerance-based comparison of key numerical values in report files. Driven by `numeric_assertions` in task.yaml. Weight: 0.10 (taken from L3=0.35, L4=0.15 redistribution). Captures LLM computation fidelity errors (surface area formulas, ΔRSSI direction, safety factors).

### 5.1.8 L4: Geometric & Spatial

3D collision detection, U-slot conflict, rack capacity, device dimension fit, maintenance clearance. 5 rules. Latency: 1-5s.

### 5.1.9 L5/L6: Deliverable

Successful `piki generate` with all expected deliverable files present. Weight: 0.15.

### 5.1.10 Layer Weights

| Layer | Weight | Rule Count |
|-------|--------|------------|
| L1 Schema | 0.10 | 5 |
| L2a Identity/FK | 0.05 | 5 |
| L2b Interface/Port | 0.05 | 7 |
| L2c Mate/Catalog | 0.05 | 4 |
| L3 Engineering + Cross-Entity | 0.35 | 7 (incl. TELECOM-TOPOLOGY-001, TELECOM-SPECTRUM-001) |
| L-Numeric | 0.10 | task-defined |
| L4 Geometric/Spatial | 0.15 | 5 |
| L5/L6 Deliverable | 0.15 | task-defined |
| **Total (piki + numeric + deliverable)** | **1.00** | — |

Table: DTS scoring layer weights. {#tbl:layer-weights}

## 5.2 Rubric Evaluation (LLM-as-Judge)

Optional qualitative evaluation for dimensions requiring human-like judgment. Rubric scores are diagnostic only—not counted in pass/fail or overall_score—due to LLM-as-Judge scoring uncertainty.

## 5.3 Score Aggregation and Pass@k

A task's overall_score is the weighted sum of all layer scores. A task is considered **resolved** if overall_score ≥ 75% (the piki layer sum). Pass@k follows the standard unbiased estimator [@chen2021evaluating]. SD-HWE-Bench reports pass@1 and pass@5 by default.

## 5.4 Evaluation Context Settings

| Setting | Agent receives | Test target |
|---------|---------------|-------------|
| Full Context | Complete scaffold ADL project | End-to-end real capability |
| Oracle Context | Only modified modules + direct dependencies | Upper bound (identification bottleneck removed) |
| Collapsed Context | Modified lines ±N lines | Lower bound / local reasoning |

Table: Three evaluation context settings. {#tbl:context-settings}

## 5.5 Repair Loop Protocol

When initial generation fails, the agent receives the complete DTS error report and may iteratively fix failures for up to R rounds (default R=5). Pass rate with repair is reported as `pass@k (repair)` and compared against no-repair `pass@k` to quantify the causal value of deterministic feedback.

## 5.6 Auxiliary Metrics

Beyond pass@k: %Apply, DTS layer pass rates, average API cost, average wall-clock time, repair round count, and File F1 (agent-modified files vs. gold patch files).

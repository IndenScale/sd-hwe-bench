# 1. Introduction

## 1.1 The Importance of AI for Engineering

Physical engineering design—spanning telecommunications infrastructure, data centers, automotive harnesses, and medical devices—remains one of the last frontiers where AI assistance lags significantly behind software engineering. While LLM-based coding agents routinely resolve real-world GitHub issues (SWE-bench) and generate complex algorithms (HumanEval), their ability to produce *physically manufacturable engineering designs* has not been systematically evaluated.

The gap is not primarily about model capability. It is about **representation**: software engineering benefits from decades of infrastructure investments—programming languages with formal grammars, compilers with deterministic error messages, test frameworks with binary pass/fail signals, and version control systems that make incremental change tractable. Physical engineering lacks equivalent infrastructure. Designs are captured in proprietary CAD formats, validated through manual review, and tested through physical prototyping—none of which lends itself to automated, scalable AI evaluation.

## 1.2 The Engineering as Code Vision

**Engineering as Code (EaC)** [@song2025eac] proposes to close this gap by giving physical engineering the same computational infrastructure that software engineering enjoys. Its three pillars are:

1. **ADL (Assembly Definition Language)**: a declarative DSL that models "what parts exist, how they connect, and where they sit" in plain text.
2. **DTS (Design Test Suite)**: a layered validation engine that checks designs from syntax (L0) through physical behavior (L4), providing deterministic pass/fail signals analogous to compiler errors and test results.
3. **piki**: an open-source runtime that implements ADL parsing, DTS checking, and deliverable generation.

If EaC succeeds, AI agents should be able to read engineering specifications, produce ADL declarations, run DTS checks, and iterate—just as they do with code today.

## 1.3 SD-HWE-Bench

This paper introduces **SD-HWE-Bench**, a benchmark for evaluating AI agents on declarative hardware engineering tasks. Built atop the EaC stack, SD-HWE-Bench contributes:

1. **A layered evaluation protocol**: 8 scoring layers (L0 syntax through L-Numeric and L5/L6 deliverables) that decompose design correctness into independently measurable dimensions.
2. **A cross-entity coupling extension**: two new DTS rules (TELECOM-TOPOLOGY-001 for Spine-Leaf full-mesh integrity, TELECOM-SPECTRUM-001 for multi-site frequency reuse distance) that evaluate whether agents can reason about *global* constraints spanning multiple physical entities—a capability absent from all existing benchmarks.
3. **33 tasks across 3 telecom sub-domains**: rack expansion, data center deployment, and outdoor base-station site engineering, with difficulty ranging from single-instance declarations to multi-disciplinary comprehensive design.
4. **L-Numeric scoring layer**: a tolerance-based numerical assertion mechanism that captures LLM computation fidelity errors in engineering calculations (surface area, link budget, safety factors).
5. **An open-source release**: task set, scoring pipeline, containerized evaluation environment, and leaderboard.

## 1.4 Key Findings

Our experiments with DeepSeek-v4-Flash (Codex CLI) on 33 tasks reveal:

- **94% pass@1** (31/33): CLI-native agents can reliably produce syntactically valid, schema-compliant, constraint-passing ADL declarations in a single attempt.
- **Average Overall Score of 84.7%**: the newly introduced L-Numeric layer exposes numerical computation deviations (surface area formulas, ΔRSSI direction errors) that reduce weighted scores even when tasks technically pass.
- **Three distinct failure dimensions**: (1) deliverable completeness—missing SVG output for non-rack facilities; (2) numerical fidelity—arithmetic errors in multi-step engineering calculations; (3) cross-entity coupling—not yet triggered at current topology scale but mechanically verified.
- **The deterministic design space ceiling**: the benchmark's grounding in canonical project commits ensures reproducibility but inherently limits differentiation when tasks reduce to formula substitution. True engineering judgment—multi-objective optimization, constraint conflict resolution, incomplete-information reasoning—remains beyond the benchmark's current scope.

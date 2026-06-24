# Evaluation

This chapter reports evaluation results. All sample inspections and the violation-injection experiment are complete; SD-HWE-Bench is in the design phase.

## Research Questions and Methodology

We answer three research questions:

- **RQ1.** Can ADL express real engineering designs in a text-native, machine-checkable form?
- **RQ2.** Can ESA detect common design violations at design time, satisfying CI/CD gating requirements with a higher signal-to-noise ratio than geometry-based ACC?
- **RQ3.** Does the representation provide the verifiable reward signal required for RLVR-style agent training?

The evaluation uses sample projects from the piki repository and a controlled violation-injection experiment. Metrics include:

1. **Expressiveness**: Whether each sample can be fully declared in ADL;
2. **Check latency**: Time for `piki check` to complete L0–L4a verification;
3. **Rule coverage**: Number and type of applicable rules;
4. **Detection accuracy**: Whether ESA identifies deliberately injected violations in semantically plausible configurations without false positives;
5. **Deliverable generation**: Whether downstream artifacts (BOM, panel view, port mapping, cable manifest) can be produced.

All measurements are taken on a laptop-class machine with a hot cache; latency reported as the median of five runs.

## Sample Projects

[@tbl:sample-status] summarizes the status of the three samples in the piki repository.

| Sample | Domain | ADL files | Applicable rules | Status | Expected by submission |
|--------|--------|-----------|------------------|--------|------------------------|
| 01-telecom-expansion | Telecom rack expansion | 42 | 30 | **Pass** (1 warning) | Complete |
| 02-modular-datacenter | Modular containerized datacenter | 38 | 34 | **Pass** (0 errors) | Complete |
| 03-mechanical-keyboard | Mechanical keyboard assembly | 29 | 28 | **Pass** (0 errors) | Complete |

Table: Status of piki sample projects {#tbl:sample-status}

**Sample 01: Telecom Rack Expansion**. The most mature sample, declaring two cabinets, servers, PDUs, switches, and fiber connections. `piki check` passes all L2–L4a rules with one warning: aisle width between `RACK-A01` and `RACK-A02` is below 600mm. It demonstrates full ADL expressiveness, sub-200ms latency, and generation of ten downstream artifacts.

**Sample 02: Modular Datacenter**. Tests container-level power and cooling. Passes all L2–L4a checks (13 passes, 0 errors) after fixing a layout empty-string defect, a missing relative-coordinate transform parse, and a cooler half-height collision. The pass demonstrates sufficiency of PLL relative-skeleton modeling for containerized infrastructure.

**Sample 03: Mechanical Keyboard**. Demonstrates skeleton-based assembly modeling across consumer electronics: `CASE-01` as root, with PCB, plate, battery, switches, keycaps, and stabilizers via parent-transform chains. Passes all L2–L4a checks (27 passes, 0 errors), providing evidence that Part/Mate/Layout abstractions generalize beyond telecom.

## Violation-Injection Experiment

To test ESA's detection accuracy and conduct a structural comparative analysis against model-based ACC, we performed a controlled violation-injection experiment on the telecom sample.

**Experimental design**. Fifteen known violations were injected into correct ADL declarations, covering four categories:

| Category | Count | Example |
|----------|-------|---------|
| L2: Interface mismatch | 4 | SFP28 optical module paired with SFP+ port |
| L2: Reference integrity | 3 | Mate referencing a non-existent Instance |
| L3: Power budget | 4 | PDU output overload exceeding rated capacity |
| L3: Spatial conflict | 2 | Two servers assigned to overlapping U slots |
| L4a: Aisle clearance | 2 | Cabinet spacing below maintenance-aisle minimum |

Table: Categories of injected violations in the telecom sample {#tbl:violation-categories}

`piki check` was then run for ESA inspection.

**Results**:

1. **ESA detection rate**: 15/15 violations detected (100%), with zero false positives — because ESA checks semantic categories (Family types, Mate relations) rather than geometry.
2. **Check latency**: `piki check` completes L0–L4a verification across all 30 rules within 200ms (laptop, hot cache, median of five runs).

### Structural Comparison with ACC

We did not run a quantitative ACC comparison because the comparison is structurally asymmetric. Seven of the fifteen violations are L2 semantic errors—interface mismatches and reference-integrity failures—that depend on the Part Family type system and Mate relations, information simply absent from IFC geometry models. Spatial checks are also qualitatively different: Mate relations distinguish intended compatibility from genuine conflicts, whereas ACC must reverse-engineer intent from geometry. Finally, after fifteen years of ACC research the community still lacks a standardized benchmark comparable to SWE-bench or VerilogEval, because heterogeneous IFC/BIM inputs require per-project remodeling and rule adaptation. This reproducibility barrier is itself a symptom of the representation-layer problem.

ESA's violation-injection experiment requires no such customization: violations are injected via YAML edits, and `piki check` provides a unified scoring function. Rules are indexed by Family types rather than project-specific naming patterns, making the methodology portable across domains.

## SD-HWE-Bench: Agent Evaluation Benchmark [Design Phase]

The pilot experiments validate feasibility and detection accuracy, but do not test whether agents can **generate** ADL from natural-language requirements. We are designing **SD-HWE-Bench** to fill this gap; it will be reported in a companion paper.

**Task paradigm**: Input natural-language engineering requirements; output structured ADL declarations (piki YAML); score by L0–L4 pass rate, deliverable quality, and L6 sign-off. Unlike SWE-bench, which tests patch generation on existing codebases [@jimenez2024swebench], SD-HWE-Bench tests creation from scratch because declarative engineering design is not yet an established practice.

**Initial domain: Telecom rack deployment**. Chosen because the space is discrete (rack U slots), constraints are algebraic (power, weight, U-slot conflicts), interface types are enumerable (SFP28, RJ45, IEC-C13/C14), and `piki check` completes in ~200ms—satisfying RLVR's fast-reward requirement.

**Connection to RQ3**. SD-HWE-Bench tests the RLVR causal chain: if ADL + ESA provides a structured, deterministic reward signal, agents trained with it should outperform those without it (prediction P1 of §3.2.2).

## Cross-Domain Validation

Samples 02 and 03 validate that ADL and ESA are not telecom special cases. [@tbl:cross-domain] lists the features exercised.

| Sample | Domain | Key cross-domain property tested |
|--------|--------|----------------------------------|
| 02-modular-datacenter | Containerized infrastructure | Container-relative layout, multi-subsystem power/cooling |
| 03-mechanical-keyboard | Consumer electronics | Skeletal assembly hierarchy, parent-transform-chain-based Mate |

Table: Cross-domain validation samples and the ADL features they exercise {#tbl:cross-domain}

Both samples pass their L2–L4a checks (13 and 27 passes respectively).

## Evaluation Summary

[@tbl:eval-summary] summarizes the current status and expected status at submission time.

| Component | Current status | Expected by submission |
|-----------|---------------|------------------------|
| Sample 01 (Telecom) | Complete | Complete |
| Sample 02 (Datacenter) | Complete (0 errors, 13 passes) | Complete |
| Sample 03 (Keyboard) | Complete (0 errors, 27 passes) | Complete |
| Violation-injection experiment | Complete | 15/15 violations detected (100%), 0 false positives |
| SD-HWE-Bench | Design complete, task authoring in progress | Task suite specification complete; agent experiments deferred to companion paper |

Table: Evaluation status and submission expectations {#tbl:eval-summary}

All three samples passing L2–L4a checks validates ADL expressiveness and ESA detection capability across domains. The violation-injection experiment verified 100% detection with zero false positives, and the structural analysis in §6.3.1 demonstrates ESA's semantic advantages over ACC. SD-HWE-Bench design is in place; agent experiments are deferred to the companion paper.

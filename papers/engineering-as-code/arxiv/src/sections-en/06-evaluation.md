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

**Sample 01: Telecom Rack Expansion**. This is the most mature sample. It declares two cabinets, multiple servers, PDUs, switches, optical modules, and fiber connections. `piki check` passes all L2–L4a rules, producing 1 warning: the aisle width between `RACK-A01` and `RACK-A02` is below the required 600mm. This sample demonstrates full ADL expressiveness, sub-200ms feedback latency, and the generation of 10 downstream artifacts (BOM, cabinet panel views, port mapping, cable manifest, etc.).

**Sample 02: Modular Datacenter**. This sample tests container-level power and cooling. The sample passes all L2–L4a checks (13 passes, 0 errors). Three root causes were fixed: (1) a `LAYOUT-001` empty-string falsy-check defect — `absolute_fields` mistook `""` for a valid value; (2) the lowering pass lacked `transform` field parsing — relative coordinates declared in YAML were dropped in the compilation pipeline; (3) a cooler position data issue — an incorrect half-height calculation caused a collision with a GPU. The sample's pass demonstrates the sufficiency of PLL relative-skeleton modeling and container-level coordinate chains, as well as the successful extension of ADL expressiveness from the telecom domain to containerized infrastructure.

**Sample 03: Mechanical Keyboard**. This sample demonstrates skeleton-based assembly modeling across the consumer electronics domain: `CASE-01` serves as the assembly root, with PCB, plate, battery, switches, keycaps, and stabilizers declared through parent-transform chains. The sample passes all L2–L4a checks (27 passes, 0 errors). After fixing the `LAYOUT-001` empty-string falsy-check defect, all entries in the continuous 2D grid layout parsed correctly. The sample's pass provides evidence for the cross-domain generalizability of the three-layer ADL architecture, extending from telecom through datacenter infrastructure to consumer electronics.

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

We did not conduct a quantitative comparison experiment against ACC tools, because such a comparison is of limited significance under current technical conditions and is difficult to execute. There are three reasons.

**L2 semantic violations are structurally unreachable for ACC.** Seven of the fifteen violations belong to the L2 category — interface type mismatches and reference-integrity violations. Detecting these violations depends on the Part Family type system and Mate relation declarations, information that simply does not exist in IFC geometry models. Regardless of how mature an ACC tool (Solibri Model Checker, Navisworks, or an academic prototype) may be, it cannot inspect attributes that are not encoded in the input representation. This is not a matter of precision — it is a matter of representational boundaries.

**The signal-to-noise ratio difference in spatial violation detection is qualitative.** ESA has access to the design intent behind spatial relations. Mate relations distinguish expected device compatibility (a server inserted into a cabinet) from genuine spatial conflicts (two devices occupying overlapping U slots). ESA's advantage lies not in running faster, but in the fact that its input representation captures semantics that ACC must reverse-engineer from geometry models.

**The lack of a standardized evaluation benchmark in the ACC community is itself a symptom of the representation-layer problem.** After fifteen years of ACC research, the field still lacks a standardized evaluation benchmark comparable to SWE-bench or VerilogEval. ACC's inputs — IFC/BIM models — are highly heterogeneous: naming conventions, modeling habits, and LOD vary by project, and regulatory frameworks vary by region. Every evaluation requires customized remodeling and rule adaptation. This precisely validates the central thesis of this paper: when design intent is trapped in geometry, not only do agents lack training signal, but even basic human evaluation reproducibility becomes difficult.

ESA's violation-injection experiment requires no such customization. The fifteen violations were injected via semantically clear YAML edits in ADL declarations, and `piki check` provided a unified, reproducible scoring function. The same violation-injection methodology can be applied to any sample that follows the three-layer ADL architecture — as already demonstrated by the cross-domain portability of samples 02 and 03 — because rules are indexed by Family types rather than project-specific naming patterns.

This comparison directly validates the core claims in §2.2.1 and §5.1: ESA's advantage stems from the fact that it inspects design declarations rather than geometric instantiation artifacts. The reliance on remodeling and the false positives from pure geometry collision detection are not implementation defects of ACC — they are fundamental limitations of its input representation.

## SD-HWE-Bench: Agent Evaluation Benchmark [Design Phase]

The pilot and violation-injection experiments validate feasibility and detection accuracy, but do not test whether agents can **generate** ADL from natural-language requirements. We have built **SD-HWE-Bench**, a benchmark for AI agent evaluation on declarative hardware engineering tasks. It is detailed in a companion paper; we summarize the key results here to establish the RQ3 evidence chain. SD-HWE-Bench currently comprises 19 telecom-domain tasks: 5 manually authored POC tasks covering all 6 task types, and 14 canonical incremental tasks automatically extracted from the canonical telecom-rack project's Git history via tools/extract_tasks.py.

**Baseline results (pass@1, no-repair, 19 tasks)**:

| Model | Pass@1 | Avg Score |
|-------|--------|----------|
| Kimi (k2.7) | 100% | 87% |
| DeepSeek-v4-Flash | 84% | 81% |
| DeepSeek-v4-Pro | 81% | 79% |

Table: SD-HWE-Bench pass@1 baseline results (telecom domain only). {#tbl:sd-hwe-bench-baseline}

Kimi achieves perfect pass@1 across all 19 tasks, demonstrating that the task set is solvable by a capable agent. DeepSeek models exhibit systematic failures concentrated in L2 (reference integrity) and L3 (engineering constraints), with common error modes including field-name ambiguity (power_capacity_w vs. capacity_w), cross-file reference errors, and U-slot spatial conflicts. These failures are not due to lack of design knowledge but to inability to consistently satisfy all constraints in a multi-file, long-context design space—precisely the gap that deterministic feedback is designed to close.

The benchmark is containerized (Docker image sd-hwe-bench-piki:latest, 1.58GB), ensuring reproducible scoring. All experiments use the unified score_task() pipeline: SyntaxCritic(L0) → PikiCritic(L1-L4) → piki generate → DeliverableCritic(L5/L6) → RubricCritic (optional).

**Task paradigm**:

```text
Input:  Natural-language engineering requirements
Output: Structured ADL declarations (piki YAML)
Scoring:  L0–L4 rule-check pass rate + deliverable quality + L6 sign-off assessment
```

Unlike SWE-bench — which tests patch generation on existing codebases [@jimenez2024swebench] — SD-HWE-Bench tests creation from scratch, because declarative engineering design does not yet exist at scale as a practice.

**Initial domain: Telecom rack deployment**. This domain was chosen because:

- The space is discrete (rack U slots), avoiding continuous 3D constraint solving;
- Constraints are primarily algebraic (power budget, weight, U-slot conflicts);
- Interface types are enumerable (SFP28, RJ45, IEC-C13/C14);
- `piki check` completes in approximately 200ms, satisfying RLVR's need for fast reward signals.

**Planned metrics**:

| Metric | Definition |
|--------|------------|
| `Pass@1` | Percentage where the first ADL output passes all enabled rules |
| `Pass@k` | Percentage with at least one pass over k samples |
| `Latency` | Median `piki check` time per output |
| `Coverage` | Coverage of task requirements in the generated ADL |
| `Human sign-off` | Percentage deemed acceptable by domain experts (L6 agent) |

Table: Planned SD-HWE-Bench evaluation metrics {#tbl:metrics}

**Connection to RQ3**. SD-HWE-Bench directly tests the RLVR causal chain: if ADL + ESA provides a structured, deterministic reward signal, then agents trained with this signal should outperform those without it. This is prediction P1 of the information representation hypothesis (§3.2.2). Benchmark design is complete; task authoring and baseline agent experiments are in progress.

## Cross-Domain Validation

Samples 02 and 03 serve a dual purpose: they are both current capability boundary records and cross-domain validation targets. Their passage before the submission deadline will demonstrate that the three-layer ADL architecture and ESA rule engine are not telecom-domain special cases.

| Sample | Domain | Key cross-domain property tested |
|--------|--------|----------------------------------|
| 02-modular-datacenter | Containerized infrastructure | Container-relative layout, multi-subsystem power/cooling |
| 03-mechanical-keyboard | Consumer electronics | Skeletal assembly hierarchy, parent-transform-chain-based Mate |

Table: Cross-domain validation samples and the ADL features they exercise {#tbl:cross-domain}

Both samples have passed their respective L2–L4a checks (Sample 02: 13 passes; Sample 03: 27 passes), providing evidence that ADL's Part/Mate/Layout abstractions transcend the telecom domain.

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

The evaluation framework is in place. All three samples passing L2–L4a checks marks the completion of cross-domain validation for ADL expressiveness and ESA detection capability. The violation-injection experiment verified ESA's design-time detection accuracy with 100% detection rate and zero false positives, and the structural analysis in §6.3.1 demonstrates ESA's semantic advantages over model-based ACC. The SD-HWE-Bench design is in place; agent experiments are deferred to the companion paper. We commit to delivering the full evaluation before the October 2, 2026 submission deadline.

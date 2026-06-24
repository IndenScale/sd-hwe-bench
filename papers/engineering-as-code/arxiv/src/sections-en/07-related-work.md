# Related Work

This chapter situates EaC within five research threads: RLVR training methodology, engineering domain benchmarks, declarative modeling and formal methods, AI4E implementation paths, and Infrastructure as Code.

## RLVR Methodology

EaC's information representation hypothesis is directly anchored in the RLVR literature. DeepSeek-R1 demonstrated that Group Relative Policy Optimization (GRPO) with deterministic verification signals yields powerful reasoning improvements [@deepseek2025r1]. SWE-RL showed that test suite feedback alone is sufficient to train effective code-repair agents [@sweagent2025swerl]. Multi-SWE-bench extended this paradigm to multi-language settings, validating its cross-linguistic generality [@multiswebench2025]. These works establish the latter half of the RLVR causal chain; EaC addresses the former half — RLVR cannot boot without structured representations.

## Engineering AI Benchmarks and Automated Compliance Checking

Existing engineering AI benchmarks occupy different positions in the matrix.

**AEC-Bench** evaluates AI reviewing human-created drawings — sitting at the intersection of ACC philosophy and AI capability assessment, but does not test design generation capabilities [@galanos2026aecbench]. **EngDesign** spans multiple design disciplines, but evaluates models on tasks defined within existing CAD/BIM workflows, without requiring a "Design as Code" intermediate representation [@engdesign2025].

**EDA benchmarks** (VerilogEval [@liu2023verilogeval], ChipBench [@chipbench2025], AMS-IO-Bench [@liu2025amsio]) have already benefited from a "Circuit as Code" foundation, exhibiting high RLVR compatibility; their performance levels provide an upper-bound reference for the targets SD-HWE-Bench aims to reach once "Design as Code" foundations are established in traditional engineering domains. Rule2DRC further validates the "executable verification" philosophy — rules as executable checks rather than passive constraints — aligning with SD-HWE-Bench's L0–L4 design [@kim2025rule2drc].

The **Automated Compliance Checking (ACC)** community has continuously advanced compliance automation through ACC tools [@eastman2009acc; @zhang2019acc], and recent efforts leveraging LLMs for regulation-to-rule translation [@fuchs2024llmregs; @yang2024llmacc; @nakhaee2024kgllm]. However, these methods still operate downstream — after design completion rather than at design time. As argued in §2.2.1, model-based ACC also suffers from two structural deficiencies — geometric collision false positives and name-dependent copy mapping — whose root cause lies in the semantic limitations of geometric representations themselves.

## Declarative Modeling and Formal Methods

**SysML v2** provides a rich systems engineering modeling framework with `part`/`occurrence` separation, `connection`/`interaction` relationships, and repository-based version control [@omg2024sysml]. Yet the methodological divergence from ADL is fundamental: SysML v2 targets human GUI modeling, with the source of truth in a model repository and verification via model checking; ADL targets agent-human textual collaboration, with the source of truth in YAML files and verification via a layered ESA rule engine enforced before commit. This is isomorphic to the division of labor between Verilog netlists and circuit schematics.

**BIM/IFC** uses the IFC exchange format and geometry-centric models as an interoperability layer [@buildingsmart2023ifc]. However, IFC couples identity, geometry, and relationships in a graph that allows multiple equivalent serializations, making line-level version control difficult [@liu2023ifcversion]. ADL inverts this relationship: text is the source of truth, and CAD/BIM are downstream consumers.

**IaC** provides the closest conceptual analogy from the software domain, but operates on infrastructure states that are already digital-native [@morris2022iac; @quattrocchi2023iacsurvey]. Chiari et al.'s empirical study of IaC static analysis [@chiari2024iacstatic] directly supports EaC's feasibility argument of "X as Code + static analysis."

## AI4E Implementation Paths

Current AI4E efforts follow two main implementation paths:

- **CUA (Computer-Using Agent)**: Having AI operate CAD software through GUIs. This path faces limitations in interface interaction fragility, absence of verification signals, and difficulty in large-scale trial-and-error.
- **CAD-MCP**: Wrapping structured tool interfaces on top of CAD software. While more stable than CUA, it remains bound to proprietary CAD kernels and does not address the design source-of-truth problem.

EaC takes a methodologically opposite approach to both paths: placing computable engineering descriptions at the center, and making CAD/CAE tools downstream consumers and renderers of that description. CUA and CAD-MCP are patches to existing toolchains; EaC rebuilds from the representation layer, enabling agents to directly operate on a computable design source of truth.

## Systematic Comparison of Related Work

The following table systematically compares EaC with major related works across dimensions including source-of-truth modality, version control granularity, verification timing, and agent-friendliness:

| Dimension | ACC | CUA | CAD-MCP | BIM/IFC | SysML v2 | **EaC (This Work)** |
|------|-----|-----|---------|---------|----------|----------------|
| Source of Truth | CAD/BIM model | CAD GUI | CAD kernel | Central model file | Model repository | **Text file (YAML)** |
| Verification Timing | Post-design | None | Tool-level | Post-design | Model-level | **Design-time (ESA)** |
| Verification Speed | Seconds to minutes | N/A | Tool-dependent | Minutes | Model-checking level | **Milliseconds** |
| Version Control | File-level | File-level | File-level | Model version | Model version | **Git line-level** |
| Agent Friendliness | No | Indirect | Partial | No | Partial | **Yes (first-class)** |
| Quality Shift-Left | No (endpoint) | No | No | No (endpoint) | Partial | **Yes (full spectrum)** |
| Part Reuse | Ad hoc | No | No | Limited | Partial | Future Work |
| RLVR Compatibility | No | No | No | No | Partial | **Yes (L0–L4a, second-level)** |
| Check Semantic Layer | Naming convention | N/A | Tool API | Property sets | Model elements | **Family type system** |
| False Positive Suppression | None (pure geometry) | N/A | N/A | None (pure geometry) | Partial | **Mate relationship exclusion** |

Table: Systematic comparison of EaC with related work {#tbl:related-work}

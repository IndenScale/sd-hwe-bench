# Introduction

Software engineering as a discipline builds reasoning infrastructure around correctness. Source code exists so that programs can be read, inspected, diffed, branched, merged, and versioned. Static analyzers catch defects before execution. Test suites provide fast, deterministic pass/fail signals. CI pipelines gate every commit. These are not AI innovations—they are software engineering innovations that AI subsequently exploits because they supply the structured, verifiable feedback that reinforcement learning with verifiable rewards (RLVR) requires [@lightman2023letsverify; @deepseek2025r1]. When code has a test suite, an agent can propose patches and receive millisecond-level correctness feedback, and its policy improves accordingly [@sweagent2025swerl]. When a chip netlist has design rule checks (DRC), a placement agent can learn under DRC supervision [@mirhoseini2020rlchip]. The pattern is consistent across code [@anthropic2025claude], mathematics [@shao2024deepseekmath], and hardware: structured, checkable representations enable AI.

Now consider physical engineering. A telecom rack designer specifies equipment, connectors, power budgets, and spatial constraints. A structural engineer defines beams, nodes, and load paths. An HVAC engineer plans ductwork and selects fans. The artifacts these engineers produce—3D CAD models, BIM databases, IFC exchange files—are geometry-centric and deeply coupled to tools [@buildingsmart2023ifc]. They capture what the design "looks like" and "how it fits together," but do not separate design **intent** from geometric **instantiation**.

The consequences of this coupling extend beyond feedback latency. The dominant inspection method today—automated compliance checking (ACC)—operates directly on geometric models. Yet geometric models have no representation of **intended** relationships: a pipe passing through a wall is flagged as a clash simply because the wall model lacks an opening, not because the design is actually wrong. A server plugged into a PDU is invisible to the checker unless both follow specific project naming conventions that the rule engine has been pre-configured to parse. The result is that ACC produces massive false positives at semantically valid geometric intersections, while also requiring costly per-project remodeling—renaming, restructuring, rebuilding—before rules can even execute. These are not algorithmic flaws but **representational** flaws: geometry cannot encode the answer to "is this pipe **supposed** to pass through this wall?"

The consequences for AI are severe. An agent that generates a building model or rack layout receives no fast, deterministic feedback on whether its output is correct. The loop is broken. Physical engineering has no `cargo check`.

The central thesis of this paper is: the bottleneck is **representation infrastructure**, not algorithmic capability. Physical engineering lacks an equivalent of source code—a structured, text-native, machine-checkable representation of design intent. And the software engineering community, not the AI community, is best positioned to design such a representation. Specifically, the community that invented programmable lint, pre-commit hooks, static single assignment, and package-level dependency resolution also possesses the vocabulary and design patterns to define:

- What an **engineering design unit** looks like (*Part*, analogous to a function or module)
- How to declare **compatibility constraints** (*Mate specifications*, analogous to interfaces or type signatures)
- How to separate **spatial layout** from part identity (*layout language*, analogous to separation of presentation and logic)
- How to stratify **correctness rules** by cost and precision (*L0–L4 rule hierarchy*, analogous to syntax → type → semantic → performance checks)
- How to **version, branch, and review** entire artifacts (*Git workflow*, battle-tested in the code domain)

We call the resulting framework **Engineering as Code (EaC)**. EaC is not "AI for engineering"—it is a **software engineering methodology for designing and implementing source code representations and toolchains for the engineering domain**.

## The Source Code Gap

[@tbl:se-gap] characterizes the gap between software engineering and physical engineering along the dimensions required for verifiable feedback.

| Dimension | Software Engineering | Physical Engineering (Current) |
|-----------|---------------------|-------------------------------|
| Primary artifact | Text (`.rs`, `.py`, `.ts`) | Geometry (`.stp`, `.rvt`, `.ifc`) |
| Atomic unit | Function / module / class | CAD body / assembly node |
| Type system | Static types, interfaces, generics | Implicit (connector families) |
| Correctness checking | Compiler / lint / test suite | Downstream review / manual review |
| Check latency | Milliseconds to minutes | Hours to weeks |
| Version control | Git (line-level diff, merge) | PDM / PLM (check-out/lock, binary diff) |
| CI pipeline | `git push → lint → test → deploy` | Manual review gates |
| Package manager | npm / cargo / pip | Part libraries (vendor-specific, unversioned) |
| Relationship encoding | Explicit (import, type signatures, dependency injection) | Implicit in geometry or naming conventions |
| Check signal-to-noise ratio | Rules target semantic categories | Rules rely on naming conventions; pure geometric clashes produce massive false positives |

Table: Gap between software engineering and physical engineering along verifiable-feedback dimensions {#tbl:se-gap}

Physical engineering does not lack rules—building codes, telecom standards, and interface specifications are rich and precise. What is missing is a representation that makes these rules **executable at design time**—just as a compiler makes type-safety rules executable at compile time.

## Contributions

This paper makes three contributions to software engineering:

1. **ADL: Assembly Definition Language** (§4). A three-layer design-intent language for physical engineering, composed of a **Part Definition Language (PDL)** for the Part type system (Family, Model, Instance), a **Part Mating Language (PML)** for explicit relationships (Mate and Connection), and a **Part Layout Language (PLL)** for spatial placement. Drawing on SE design patterns—separation of concerns, explicit type signatures, contract-based design—ADL provides a text-native, version-controllable, machine-checkable engineering representation that is distinct from and complementary to existing CAD and BIM formats.

2. **ESA: Engineering Static Analysis** (§5). An L0–L4 layered rule checker that operates on ADL artifacts, from syntax → reference integrity → business rules → geometric constraints. Unlike ACC—which operates on geometric models and suffers from false-positive noise and naming-dependency overhead—ESA checks design **declarations** over semantic categories (Part Family, Mate type, interface signatures). This paper defines ESA's operational charter (waivers, baselines, signal-to-noise ratio, AI assistance) and provides a structured diagnostic format that serves simultaneously as human-readable error reports and machine-consumable reward signals.

3. **The Information Representation Hypothesis** (§3). A testable claim, anchored in the RLVR literature: the bottleneck for AI in physical engineering is the lack of a computable design representation, not insufficient model capability. This paper derives predictions from this hypothesis and describes **SD-HWE-Bench**, a benchmark designed to evaluate generative agent performance on ADL authoring tasks.

We validate ADL and ESA through **piki**, an open-source EaC runtime. On a representative telecom rack deployment, piki checks 64 engineering rules—interface compatibility, power budget, U-slot conflicts, load-bearing—in under 200ms. The prototype integrates with Git, supports `--skip` and `warning_only` rule waivers, and produces structured diagnostics suitable for CI pipeline consumption. We report the prototype's current scope and explicit limitations in §6.

## Designing Source Code for New Domains Is a Core SE Problem

Designing source code representations for new domains is a core SE activity. The DSL literature treats language design as an SE contribution in its own right—encompassing syntax, semantics, type systems, and verification trade-offs [@hudak1996dsl; @fowler2010dsl; @volter2013dsl]. ADL continues this lineage, but targets physical engineering design, requiring a balance between human readability and machine verifiability for a dual audience of engineers and AI agents.

Static analysis provides the direct foundation for ESA. Compiler analysis evolved from syntax checking through type systems and data-flow analysis to inter-procedural verification; Cousot's abstract interpretation supplied its mathematical footing [@cousot1977abstract]. ESA replicates this layered pattern, mapping "syntax → reference integrity → type constraints → spatial constraints" onto engineering rules. The missing prerequisite was a representation layer that makes such stratification possible—ADL.

IaC static analysis offers proximal empirical evidence. Chiari et al.~demonstrated that "X as Code + static analysis" is viable and efficient for Terraform and Ansible [@chiari2024iacstatic]. EaC extrapolates this pattern from cloud infrastructure to physical infrastructure, showing that the DSL+static-analysis pattern is domain-independent and that physical engineering is its most demanding testbed.

## Paper Structure

Section 2 surveys current representations used in physical engineering, analyzing the structural deficiencies of model-based ACC—geometric clash false positives and naming-dependency-induced remodeling overhead—and why they constitute an AI bottleneck. Section 3 articulates the Information Representation Hypothesis and its RLVR foundation. Section 4 introduces ADL: its three-layer architecture, design rationale, and integration with SE toolchains. Section 5 introduces ESA: the layered rule hierarchy, semantic advantages over ACC, operational charter, structured diagnostic output, and downstream verification protocol. Section 6 reports evaluation results from the piki prototype—all three samples pass, and violation injection experiments validate ESA's detection accuracy at 100% recall. Section 7 discusses differentiation from related work—ACC, SysML v2, BIM/IFC, IaC static analysis, and existing benchmarks. Section 8 concludes, acknowledges limitations, and outlines future work including SD-HWE-Bench and RLVR training.

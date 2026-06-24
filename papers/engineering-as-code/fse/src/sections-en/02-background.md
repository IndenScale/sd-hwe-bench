# Background and Motivation

This chapter traces a causal chain that has already driven transformation in three adjacent domains, establishes the motivation for Engineering as Code, and explains why engineering design has so far been unable to participate in this chain.

## The RLVR Causal Chain

Across three domains — code, mathematics, and chip design — a striking pattern recurs: a structured representation of correctness enables automatic, deterministic checking; that checking provides a fast reward signal; and that signal makes Reinforcement Learning with Verifiable Rewards (RLVR) effective.

- **Mathematics**. DeepSeekMath trains on problems whose final answers are automatically verifiable. Using Group Relative Policy Optimization (GRPO), it improves reasoning without requiring a separate reward model [@shao2024deepseekmath]. Lightman et al. demonstrate that Process Reward Models (PRMs) — scoring intermediate reasoning steps — outperform Outcome Reward Models (ORMs), underscoring the value of step-level checkability [@lightman2023letsverify].
- **Code**. SWE-RL uses test suite pass/fail as a reward signal to train agents for fixing GitHub issues, achieving substantial gains over supervised fine-tuning [@sweagent2025swerl]. Claude Code and similar agents operate in repositories where compilation and tests provide immediate feedback [@anthropic2025claude].
- **Chips**. Deep-reinforcement-learning-based chip placement treats design rule checking as a fast, differentiable signal during macro placement [@mirhoseini2020rlchip]; AMS-IO-Bench evaluates LLM-generated I/O ring designs under DRC/LVS [@liu2025amsio].

The pattern can be summarized as:

```text
Structured, checkable representation → Sub-second deterministic feedback → RLVR effective → Agent capability leap
```

We call this the **RLVR Causal Chain**.

## Why Engineering Design Is Blocked

Physical engineering design — buildings, mechanical assemblies, telecommunications infrastructure — has so far failed to participate in this chain. The obstacle lies not in insufficient model scale or excessive physical complexity, but in the fact that **the design representation itself cannot be checked by machines in the required way**.

Today's dominant representations are CAD and BIM. They couple three things within the same artifact:

1. **Functional identity** (what a component is and does)
2. **Geometric realization** (where it is located and how it looks)
3. **Tool-specific state** (vendor-format-internal constraints, history, parameters)

This coupling creates three problems for AI agents.

**Information loss**. Once design intent is frozen into geometry, recovering the original functional relationships — which port connects to which, which cabinet hosts which server, which rooms form a fire compartment — requires reverse extraction. Eastman et al. and Zhang et al. document that ACC must parse IFC or drawing models and infer intent, a lossy and error-prone step [@eastman2009acc; @zhang2019acc].

**Feedback delay**. ACC runs after the design artifact is complete. When a violation is found, the design is already a tightly coupled multi-discipline model; remediation is costly and slow.

**No training signal**. Because checking is downstream and expensive, an agent cannot use it as a reward during generation. It cannot try a layout, receive a pass/fail reward in milliseconds, and update its policy. The RLVR loop breaks at the very first arrow.

Recent work has attempted to apply LLMs directly to building code interpretation [@fuchs2024llmregs; @yang2024llmacc; @nakhaee2024kgllm], but these approaches still operate downstream of the design artifact. They improve the reviewer side, not the generator side.

### Two Structural Deficiencies of Model-Based ACC

Even within its operating scope — checking completed designs — model-based ACC suffers from two structural, rather than algorithmic, deficiencies. These deficiencies explain why merely accelerating ACC cannot bridge the gap.

**False positives from pure geometric clash detection**. BIM clash detection treats every volumetric intersection as a violation. A pipe passing through a wall triggers a clash because the wall model lacks an opening. A cable tray crossing a beam is reported as a clash even when the two have physical clearance by design. These are not detection errors — the algorithm correctly identifies geometric overlap. The problem is that the model contains **no semantic information** describing the **intended** relationship between two objects. In EaC terms, the model lacks a Mate declaration stating "this pipe passes through this wall" or "this cable tray sits above this beam at a specified offset." Without such a declaration, the checker cannot distinguish an intentional penetration from a genuine layout error. The result is a flood of false positives that designers learn to ignore, drowning genuine violations in noise.

**Naming dependency and remodeling overhead**. Rule-based ACC tools — whether operating on IFC, Revit, or proprietary formats — rely on standardized naming conventions to identify objects. A rule such as "all ducts named `DUCT-SUPPLY-*` must maintain 50 mm clearance from structural elements" works only if every duct in every project obeys that naming convention. In practice, naming conventions vary across firms, projects, and even disciplines. Before ACC can run, the model must be **remodeled** — objects renamed, reorganized, and sometimes reconstructed — to match the naming patterns the rule engine expects. This remodeling step is manual, expensive, and itself introduces errors. Worse, it erodes the efficiency ACC is supposed to provide: if you must remodel the design before checking it, you have not automated checking — you have merely shifted manual labor upstream. One consequence of this structural problem is that the ACC community, after 15 years of development, still lacks a standardized evaluation benchmark: heterogeneous IFC models with different naming conventions, LODs, and modeling practices cannot form a unified test set, and every evaluation requires bespoke remodeling and rule adaptation.

These three deficiencies — false-positive noise, naming-dependent remodeling, and non-reproducible evaluation due to representation-layer issues — share a common root: the model is the design's **sole** structured description, but it is structured for geometric representation rather than semantic query. A rule engine that must check geometry to infer intent will forever be limited by the semantic poverty of geometry.

## Lessons from Software Engineering and Chip Design

Two mature domains offer a different model.

**Infrastructure as Code (IaC)**. Tools such as Terraform and Ansible express infrastructure as versionable, diffable, and statically analyzable textual declarations. Chiari et al. empirically demonstrate that IaC static analysis tools can detect hundreds of security and compliance violations in seconds [@chiari2024iacstatic]. IaC proves that "X as Code" plus static analysis is a practical, scalable combination [@morris2022iac; @quattrocchi2023iacsurvey].

**Chip design**. A Verilog netlist is the source of truth for logical design; physical layout is a downstream view. Design rule checking runs during place-and-route, not only after tape-out. The representation is deliberately designed to be textual, hierarchical, and checkable before visualization [@ieee1364].

Engineering design has no equivalent of a Verilog netlist or a Terraform file. EaC's goal is precisely to provide one.

## The Research Gap

The gap can be stated precisely. Existing work provides:

- Rich **geometric** representations (CAD/BIM/IFC);
- Downstream **compliance checking** (ACC), hampered by false-positive noise and naming-dependency overhead;
- Isolated **AI benchmarks** for engineering tasks [@engdesign2025; @galanos2026aecbench; @maatouk2023teleqna].

What is missing is an **upstream, text-native, machine-checkable design representation** — one that can serve as both a training objective for generative agents and a source of truth for human engineers. EaC fills this gap.

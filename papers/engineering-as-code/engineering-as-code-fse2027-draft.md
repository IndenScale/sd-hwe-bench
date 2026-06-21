# Abstract

Generative AI has made rapid progress in domains that possess a machine-readable, verifiable representation of correctness: source code, formal mathematics, and chip netlists. In each case, a structured artifact can be checked automatically, and that deterministic feedback enables reinforcement learning with verifiable rewards (RLVR). Engineering design---spanning mechanical, electrical, civil, and telecom-physical systems---has not seen comparable advances, not because the models are weaker, but because the domain lacks an equivalent "design as code" representation.

We introduce **Engineering as Code (EaC)**, a paradigm that treats structured, textual design declarations as the source of truth for physical engineering systems. EaC has three pillars. First, the **Information Representation Hypothesis**: the bottleneck for AI engineering is the absence of a computable design representation, not model capability. Second, **Assembly Definition Language (ADL)**, a three-layer language that separates part identity (PDL), part mating (PML), and part layout (PLL), making design intent machine-readable, diffable, and agent-writable. Third, **Engineering Static Analysis (ESA)**, a deterministic rule engine that moves compliance checking from downstream audit to upstream design-time gating, analogous to static analysis in software engineering.

We validate the approach through **piki**, an open-source EaC runtime. On a representative telecom rack deployment, piki checks 64 engineering rules spanning interface compatibility, power budgets, load capacity, and fast geometry in under 200 ms. We also report the current limitations of the prototype and outline **SD-HWE-Bench**, a benchmark that will evaluate agents on generating ADL declarations from natural-language requirements.

EaC reframes engineering AI as a representation problem: before agents can reliably design physical systems, the systems must first be describable in a language that machines can read, check, and version.

# 1. Introduction

In the last three years, generative agents have learned to prove mathematical theorems [@shao2024deepseekmath; @deepseek2025r1], fix real GitHub issues [@sweagent2025swerl; @anthropic2025claude], and place chip macros under design-rule constraints [@mirhoseini2020rlchip; @liu2025amsio]. The common ingredient is not merely a large model; it is a **machine-readable, automatically checkable representation of correctness**. A theorem has a verifiable proof; a code patch has a test suite; a chip netlist has design-rule checking. Where such a representation exists, reinforcement learning with verifiable rewards (RLVR) can close the loop: the agent proposes, the checker judges, and the policy improves [@lightman2024letsverify; @shao2024deepseekmath].

Engineering design---the specification of racks, pumps, structural frames, HVAC ducts, and datacenter layouts---has not crossed the same threshold. The dominant representation is still geometry-centric: CAD bodies, BIM models, and neutral exchange files such as IFC [@buildingsmart2023ifc]. These formats excel at visualization and manufacturing, but they couple function, geometry, and tool state into a single artifact. As a result, an agent that writes a building or a telecom rack cannot receive millisecond-level feedback on whether its design is correct. It can only be audited after the fact, often by expensive downstream processes: collision detection, manual drawing review, or physical testing.

This paper argues that the bottleneck is **representational**, not algorithmic. We call this claim the **Information Representation Hypothesis**:

> The lag of AI in physical engineering is caused primarily by the lack of a structured, text-native, machine-checkable design representation, rather than by insufficient model capability or by the intrinsic complexity of physics.

To make the hypothesis actionable, we propose **Engineering as Code (EaC)**, a paradigm that places declarative, textual design declarations at the center of the engineering workflow. In EaC, CAD and BIM tools remain important, but they become **consumers** of the design source of truth, much as physical layout tools consume Verilog netlists in chip design [@ieee1364].

## Contributions

This paper makes three contributions:

1. **The Information Representation Hypothesis and its testable predictions.** We articulate the hypothesis, connect it to the RLVR causal chain observed in code, math, and chips, and derive predictions that can be evaluated empirically (\S 3).

2. **ADL, an Assembly Definition Language for physical engineering.** ADL separates design intent into three orthogonal layers---Part Definition Language (PDL), Part Mating Language (PML), and Part Layout Language (PLL)---so that identity, relationships, and geometry can be written, checked, and versioned independently (\S 4).

3. **ESA, Engineering Static Analysis.** ESA moves rule checking from downstream Automated Compliance Checking (ACC) [@eastman2009acc; @zhang2019acc] to upstream design-time gates. We define a seven-level validation stack, position ESA at levels L2--L3 with a lightweight geometric extension at L4a, and present four operational principles: waivers, baseline rules, shift-left signal-to-noise optimization, and AI-assisted rule authoring (\S 5).

We evaluate the approach through **piki**, an open-source prototype. On a telecom rack sample, piki loads the ADL declaration and checks 64 rules in under 200 ms. We report what works, what fails, and where the boundary between ESA and downstream verification lies (\S 6). We also outline **SD-HWE-Bench**, a planned benchmark that will test whether agents can generate ADL from natural-language requirements.

## Research Questions

The paper is organized around three research questions:

- **RQ1.** Can ADL express real engineering designs in a text-native, machine-checkable form?
- **RQ2.** Can ESA detect common design violations at design time, with latency suitable for CI/CD pre-commit gates?
- **RQ3.** Does the resulting representation provide the verifiable reward signal needed for RLVR-based design agents?

## Paper Organization

\S 2 reviews the background: why existing CAD/BIM and ACC workflows cannot support RLVR, and what software engineering and chip design teach us about checkable representations. \S 3 presents the EaC approach. \S 4 and \S 5 detail ADL and ESA. \S 6 describes the prototype evaluation and threats to validity. \S 7 situates the work against related research. \S 8 concludes with limitations and future work.

# 2. Background and Motivation

This section motivates Engineering as Code by tracing a causal chain that has already transformed three adjacent fields, then showing why engineering design currently lacks the necessary representation to participate in that chain.

## 2.1 The RLVR Causal Chain

A striking pattern has emerged in code, mathematics, and chip design. In each domain, a structured representation of correctness enables automatic, deterministic checking; that checking provides fast reward signals; and those signals make reinforcement learning with verifiable rewards (RLVR) effective.

- **Mathematics.** DeepSeekMath trains on problems whose final answers are automatically verifiable. Using Group Relative Policy Optimization (GRPO), it improves reasoning without a separate reward model [@shao2024deepseekmath]. Lightman et al. show that process reward models, which score intermediate reasoning steps, outperform outcome reward models, underscoring the value of step-level checkability [@lightman2024letsverify].
- **Code.** SWE-RL trains agents to fix GitHub issues using test-suite pass/fail as the reward signal, achieving substantial gains over supervised fine-tuning [@sweagent2025swerl]. Claude Code and similar agents operate in repositories where compilation and tests give immediate feedback [@anthropic2025claude].
- **Chips.** Chip placement with deep reinforcement learning treats design-rule checking as a fast, differentiable signal during macro placement [@mirhoseini2020rlchip]; AMS-IO-Bench evaluates LLM-generated I/O ring designs against DRC/LVS checks [@liu2025amsio].

The pattern can be summarized as:

```text
structured, checkable representation → sub-second deterministic feedback → RLVR works → agent capability jump
```

We call this the **RLVR causal chain**.

## 2.2 Why Engineering Design Is Stuck

Physical engineering design---buildings, mechanical assemblies, telecom infrastructures---does not yet participate in this chain. The obstacle is not that the models are too small or that physics is too hard; it is that the **design representation itself is not machine-checkable in the required way**.

The dominant representations are CAD and BIM. They couple three things into one artifact:

1. **Functional identity** (what a component is and what it does);
2. **Geometric realization** (where it sits and what it looks like);
3. **Tool-specific state** (constraints, history, parameters internal to a vendor format).

This coupling creates three problems for AI agents.

**Information loss.** Once design intent is frozen into geometry, recovering the original functional relationships---which port connects to which, which rack holds which server, which rooms form a fire compartment---requires reverse extraction. Eastman et al. and Zhang et al. document how Automated Compliance Checking (ACC) must parse IFC or drawing models and infer intent, a lossy and error-prone step [@eastman2009acc; @zhang2019acc].

**Late feedback.** ACC runs after the design artifact is complete. By the time a violation is found, the design is already a tightly coupled cross-disciplinary model; fixing it is expensive and slow.

**No training signal.** Because checking is downstream and costly, an agent cannot use it as a reward during generation. It cannot try a layout, receive a pass/fail reward in milliseconds, and update its policy. The RLVR loop is broken at the first arrow.

Recent work attempts to apply LLMs directly to building-code interpretation [@fuchs2024llmregs; @yang2024llmacc; @nakhaee2024kgllm], but these approaches still operate downstream of the design artifact. They improve the auditor, not the generator.

## 2.3 What Software Engineering and Chip Design Teach Us

Two mature fields offer a different model.

**Infrastructure as Code (IaC).** Tools such as Terraform and Ansible express infrastructure as textual declarations that can be versioned, diffed, and statically analyzed. Chiari et al. empirically show that IaC static-analysis tools can detect hundreds of security and compliance violations in seconds [@chiari2024iacstatic]. IaC proves that "X as Code" plus static analysis is a practical, scalable combination [@morris2022iac; @quattrocchi2023iacsurvey].

**Chip design.** A Verilog netlist is the source of truth for logical design; physical layout is a downstream view. Design-rule checking runs during placement and routing, not only after tape-out. The representation is deliberately textual, hierarchical, and checkable before visualization [@ieee1364].

Engineering design has no equivalent of a Verilog netlist or a Terraform file. EaC aims to provide it.

## 2.4 Research Gap

The gap can be stated precisely. Existing work provides:

- rich **geometric** representations (CAD/BIM/IFC);
- downstream **compliance checking** (ACC);
- isolated **AI benchmarks** for engineering tasks [@engdesign2025; @galanos2026aecbench; @maatouk2023teleqna].

What is missing is an **upstream, text-native, machine-checkable design representation** that can serve as a training target for generative agents and as a source of truth for human engineers. EaC fills this gap.

# 3. The Engineering as Code Approach

This section defines Engineering as Code as a socio-technical configuration, states the Information Representation Hypothesis in testable form, and maps the seven-level validation stack that separates design-time static analysis from downstream verification.

## 3.1 A Formal Definition

Engineering as Code (EaC) is a design paradigm in which design intent is expressed as structured, textual declarations; validated by an automated rule engine; versioned in a version-control system; and distributed through a package manager. Formally, an EaC system is a quadruple:

```text
EaC = <ADL, ESA, VCS, PM>
```

- **ADL (Assembly Definition Language)** is the declarative design notation. It describes parts, their interfaces, their mating relationships, and their spatial layout in machine-readable text.
- **ESA (Engineering Static Analysis)** is the deterministic rule engine that checks declarations before they are committed or persisted.
- **VCS (Version Control System)**, typically Git, provides line-level history, branching, and pull-request review of design intent.
- **PM (Package Manager)**, such as the proposed Engineering Package Manager (EPM), distributes reusable part libraries, rule sets, and generators.

The quadruple emphasizes that EaC is not only a language or a tool; it is a socio-technical configuration. Each component serves a distinct function: ADL supplies expressiveness, ESA supplies feedback, VCS supplies collaboration granularity, and PM supplies reuse economics. Removing any one of them prevents the paradigm from scaling.

## 3.2 The Information Representation Hypothesis

The central claim of this paper is the **Information Representation Hypothesis**:

> The lag of AI in physical engineering is caused primarily by the absence of a machine-readable, generatable, checkable, and versionable design representation---a "Design as Code" computable substrate---rather than by insufficient model capability or by the intrinsic complexity of physics.

The hypothesis is derived from three observations:

1. **Code, math, and chips share a common enabler.** In each domain, success came after a structured, automatically checkable representation was in place (tests, proof checkers, DRC/LVS).
2. **Step-level checkability matters.** Process reward models outperform outcome reward models when intermediate steps can be verified [@lightman2024letsverify]; the same logic applies to design decisions.
3. **Engineering lacks the starting node.** CAD/BIM couple intent, geometry, and tool state, so agents cannot read or write design intent directly, and they cannot receive millisecond feedback.

**Testable prediction.** If the hypothesis is correct, then holding the underlying model constant, providing an agent with a text-native, machine-checkable, structurally decoupled "Design as Code" representation should produce a measurable improvement in design-generation ability. We report a small pilot experiment in \S 6.1 and outline a larger benchmark, SD-HWE-Bench, in \S 6.3.

## 3.3 The Seven-Level Validation Stack

EaC partitions engineering validation into seven levels, ordered by computational cost and determinism. Table 1 summarizes the stack.

| Level | Scope                                                          | Execution     | ESA?    | Latency target |
| ----- | -------------------------------------------------------------- | ------------- | ------- | -------------- |
| L0    | File parseability                                              | Load          | No      | < 1 ms         |
| L1    | Schema validation                                              | Load          | No      | < 10 ms        |
| L2    | Reference integrity, mate consistency, interface compatibility | Load / check  | **Yes** | < 10 ms        |
| L3    | Cross-record business rules                                    | `piki check`  | **Yes** | 10--100 ms     |
| L4a   | Fast geometry (AABB, U-space conflict, aisle width)            | `piki check`  | Partial | 100 ms--1 s    |
| L4b   | Exact geometry (CAD-kernel interference, clearance)            | `verify geom` | No      | 1 s--1 min     |
| L5    | Physics simulation (CFD/FEA)                                   | `verify phys` | No      | 1 min--1 h     |
| L6    | AI / human approval                                            | `signoff`     | No      | seconds--hours |

**Why ESA is mainly L2--L3 (with L4a as a lightweight extension).** ESA is deliberately scoped to checks that are deterministic, repeatable, and cheap enough to run on every commit. L2 and L3 satisfy all three criteria: they reason about declarations and constraints without physical simulation. L4a is a boundary case: it uses axis-aligned bounding boxes, discrete rack units, and algebraic inequalities rather than CAD kernels, so it can still run in milliseconds. Once exact interference, clearance, or continuous constraint solving is required (L4b), the cost jumps by one to three orders of magnitude and the activity becomes downstream verification.

This scoping is conservative but strategic. If a model cannot satisfy deterministic rules, there is little value in exposing it to fuzzier geometric or physical constraints; the signal would be noisy and the RLVR loop unstable.

## 3.4 EaC and Its Downstream Tools

EaC does not replace CAD, BIM, CAE, or manufacturing systems. It repositions them. ADL declarations become the **design source of truth**; CAD and BIM become **consumers** that render, refine, and manufacture from that truth. The relationship is analogous to Verilog and physical layout in chip design: the netlist is the logical source of truth, and the layout is an implementation view [@ieee1364; @mirhoseini2020rlchip].

The benefits of this separation are threefold:

1. **Agents can read and write the source of truth.** A generative model outputs ADL text; it does not need to manipulate a proprietary CAD file.
2. **Humans can review design intent line by line.** A pull request shows exactly which parts, mates, or layout entries changed, independent of geometry.
3. **Downstream tools become interchangeable.** Any tool that can consume ADL can participate in the workflow; the project is not locked to one vendor's format.

## 3.5 EaC and Infrastructure as Code

EaC generalizes Infrastructure as Code (IaC) from the cloud to physical engineering [@morris2022iac; @quattrocchi2023iacsurvey]. The two share textual declarations, version control, static analysis, and package management. The critical difference is that **IaC describes an already-digitized world** (servers, networks, containers), while **EaC must first digitize the physical world** (racks, pumps, structural members) by defining types, interfaces, relationships, and layouts.

| Dimension          | Infrastructure as Code               | Engineering as Code                                     |
| ------------------ | ------------------------------------ | ------------------------------------------------------- |
| Source of truth    | Terraform / Ansible files            | ADL declarations                                        |
| Check command      | `terraform plan`, CI tests           | `piki check`, ESA                                       |
| Collaboration unit | Git PR                               | AssemblyHub PR                                          |
| Asset reuse        | npm / PyPI                           | EPM                                                     |
| Atomic unit        | Resource / service instance          | Part                                                    |
| Spatial dimension  | Usually absent                       | Core concern                                            |
| Goal               | Repeatable, auditable infrastructure | Checkable, reproducible, automatable engineering design |

Because physical objects have semantic boundaries that must be agreed upon by domain experts, EaC needs not only a language and a rule engine, but also a community-governed package ecosystem. EPM and AssemblyHub are discussed as future infrastructure in \S 8.

# 4. ADL: Assembly Definition Language

ADL is the declarative design notation of Engineering as Code. It is deliberately text-native: design intent is authored as YAML and validated as code, rather than captured as geometric operations inside a CAD or BIM GUI. ADL is organized around three orthogonal sub-languages that separate what exists, how parts couple, and where they are placed.

## 4.1 Design Goals

ADL pursues three goals:

1. **Text-native representation.** Agents and humans can read and write design intent in plain text, enabling version control, diffing, and programmatic generation.
2. **Agent-oriented syntax.** Files have explicit identities, references, and deterministic validation. There is no hidden state that depends on a GUI session.
3. **Orthogonality of identity, relation, and space.** A change to one dimension should not force a rewrite of files in another dimension.

The reference runtime is **piki**, an open-source engine that loads ADL declarations, runs the layered rule engine, and generates downstream deliverables. However, ADL is defined independently of any single tool.

## 4.2 Part as the Engineering Atom

In ADL, a **Part** is the atomic unit of engineering description. A Part is not merely a geometric body; it is a semantically complete entity that exposes typed interfaces and participates in explicit relationships. A Part is defined by:

- a **Family** (its schema and value constraints);
- a **Model** (a concrete realization with defaults);
- an **Instance** (a deployed entity that may override defaults);
- a set of typed **Interfaces**;
- optional internal geometry, kept hidden unless high-fidelity analysis is needed.

The Part abstraction rests on four properties:

1. **Semantic completeness.** A server Part is typed as `ServerFamily` and carries fields such as `height_u`, `tdp_w`, and `psu_count`. A pump Part carries `flow_rate` and `head`. Type checking is performed by pydantic schemas registered by plugins.
2. **Encapsulation.** Internal geometry is hidden; only standardized interfaces are visible to downstream consumers.
3. **Relational intentionality.** A server's role in an assembly is expressed through relationships: it is the `child` in a `rack-mount-19inch` Mate; a transceiver is the `child` in an `sfp28-cage` Mate.
4. **Multi-view projection.** The same Part can be projected to CAD (USD/glTF), CAE (thermal or structural models), ERP (BOM entries), and lifecycle catalogs without changing its core declaration.

## 4.3 PDL: Part Definition Language

PDL defines the Part type system across three layers: **Family**, **Model**, and **Instance**.

**Family.** A Family is a pydantic `BaseModel` class that declares the schema and value constraints for a category of parts. For example, a `ServerFamily` might require `id`, `height_u` (1--48), `tdp_w` (> 0), and a list of interface specifications. Families are code, not configuration; they are registered by plugins.

**Model.** A Model supplies concrete defaults for a Family. An example model file is:

```yaml
model: dell-r750
family: ServerFamily
brand: Dell
mpn: PowerEdge R750
height_u: 2
tdp_w: 600
psu_count: 2
```

**Instance.** An Instance is a deployed entity that may override Model defaults:

```yaml
id: SRV-01
model: dell-r750
family: ServerFamily
status: planned
```

At runtime, the resolved value is computed as `Model.defaults + Instance.overrides`, then validated against the Family schema. The Instance's identity is derived from its file name (`SRV-01.yaml` → `SRV-01`). A key design decision is that **Instance files do not contain layout information**; layout is declared separately in PLL. This separation means the same device can be placed in different locations without duplicating its definition.

## 4.4 PML: Part Mating Language

PML describes relationships between Parts and distinguishes two kinds: **Mate** and **Connection**.

**Mate** expresses design coupling: it constrains how two Parts fit or work together. Mates are stored as independent YAML files under `mates/<mate_type>/`. For example:

```yaml
type: rack-mount-19inch
parent: RACK-A02
child: SRV-01
at:
  u_start: 10
  u_span: 2
constrains:
  - field: depth_mm
    operator: "<="
    value_ref: depth_mm
```

The engine validates these constraints at load time. Registered Mate types include `sfp28-cage`, `power-iec-c14-c13`, and `lc-connector`.

**Connection** expresses signal, power, or material flow between two Interfaces. A Connection is itself a first-class Instance:

```yaml
id: CONN-ACCESS-SRV01
family: PortConnectionFamily
from_port: ACCESS-SW-01/10GE1/0/1
to_port: SRV-01/eth0
cable_type: OM4-LC-LC
```

The Mate/Connection split maps to two distinct design phases: mechanical or electrical feasibility (Mate) and functional topology correctness (Connection). CAD/BIM systems often merge these into a single object, making it impossible to validate one phase without involving the other.

## 4.5 PLL: Part Layout Language

PLL assigns values to the remaining spatial degrees of freedom after PDL declares Parts and PML declares their couplings. Its purpose is not to solve arbitrary geometric constraint networks, but to assign values to the free variables of a design.

PLL operates in two modes. In **tightly coupled assemblies**, PLL provides parameter completion for PML constraints. For example, a `rack-mount-19inch` Mate leaves the rack unit open; PLL assigns it through `at.u_start` or an equivalent `LayoutEntry`:

```yaml
- instance: SRV-01
  rack_id: RACK-A02
  position_u: 10
```

In **loosely coupled or top-level assemblies**, PLL uses absolute or relative coordinate systems. Absolute entries set `position_x_mm`, `position_y_mm`, and `position_z_mm`; relative entries set a `parent` plus a `transform` containing `translation` and `rotation` (Z-Y-X Euler angles in degrees). The two modes are mutually exclusive within a single `LayoutEntry`.

Current PLL has known boundaries. It supports discrete coordinates (rack units, grid axes) and simple continuous transforms, but not complex parametric assemblies such as continuous 3D HVAC routing or closed-loop mechanical linkages. These are left to future extensions and external CAE tools.

## 4.6 Orthogonality

The orthogonality of PDL, PML, and PLL is the design principle that enables incremental validation, parallel editing, and semantic diffs. Each sub-language lives in its own directory: `instances/` and `models/` for PDL, `mates/` for PML, and `layouts/` for PLL. Because namespaces are separated, a change in one dimension does not rewrite files in another.

**Incremental validation.** An agent can generate PDL declarations and pass L0--L2 checks before it attempts PML constraints and PLL spatial rules. This mirrors the staged error feedback of a compiler.

**Parallel editing.** A device engineer can edit `instances/SRV-01.yaml`, a layout engineer can edit `layouts/layout.yaml`, and a mechanical engineer can edit `mates/rack-mount/RACK-A02-SRV-01.yaml` simultaneously. Git merge conflicts occur only when the same decision dimension changes.

**Semantic diffs.** A diff in `instances/` means "some device identities or attributes changed"; a diff in `mates/` means "some couplings changed"; a diff in `layouts/` means "some positions changed." For example:

```diff
- position_u: 10
+ position_u: 12
```

is unambiguously a layout change, while a change to `tdp_w` in `instances/SRV-01.yaml` is an electrical change. This interpretability supports both human code review and automated reward attribution in RLVR training.

## 4.7 Comparison with SysML v2 and BIM/IFC

ADL, SysML v2, and BIM/IFC all aim to formalize engineering systems, but they differ in assumptions about source of truth, collaboration unit, and target user. Table 2 summarizes the comparison.

| Dimension            | SysML v2 [@omg2024sysml]     | BIM / IFC [@buildingsmart2023ifc] | ADL (piki)                                                 |
| -------------------- | ---------------------------- | --------------------------------- | ---------------------------------------------------------- |
| Source of truth      | Model repository             | Central model file / IFC exchange | Text files (YAML + TOML)                                   |
| Version-control unit | Model version                | File version                      | Git line-level history                                     |
| Core operation unit  | Model element                | Geometry object / IFC entity      | File (Instance, Mate, Layout)                              |
| Identity and space   | Mixed in part/occurrence     | Geometry is identity              | Instance and Layout separated at file level                |
| Inter-part relations | `connection` / `interaction` | Implicit in geometric constraints | `Mate` + `Connection` dual separation                      |
| Validation           | Model checking               | Collision detection (post-hoc)    | ESA L2--L4a + load-time checks L0--L1, millisecond latency |
| Target user          | Human systems engineer (GUI) | Human designer (GUI)              | AI agent + human engineer (text)                           |

SysML v2 and BIM are primarily human-facing modeling environments. Their source of truth lives in repositories or large central files that are difficult to diff, branch, and validate automatically. IFC in particular couples identity, geometry, and relations in a graph that admits many equivalent serializations, making line-level version control difficult [@liu2023ifcversion].

ADL inverts these priorities. It targets agent-human collaboration, treats text as the only source of truth, and makes validation a first-class concern. CAD and BIM are not eliminated; they become downstream consumers for visualization, collision detection, and manufacturing.

## 4.8 Core Syntax Summary

Figure 3 gives a compact grammar of ADL. The authoritative parser is the YAML loading chain in the piki implementation; the grammar is provided for readers who need precise boundaries.

```text
Project       ::= piki.toml (ModelFile | InstanceFile | MateFile | LayoutFile | CatalogFile)*

ModelFile     ::= "model:" id
                  "family:" FamilyName
                  Field*
                  ("interfaces:" InterfaceSpec*)?

InstanceFile  ::= "id:" id
                  ("family:" FamilyName | "model:" ModelName)
                  Field*
                  ("interfaces:" InterfaceSpec*)?

InterfaceSpec ::= "- id:" id
                  "interface_type:" Type
                  ("direction:" "input" | "output" | "bidirectional")?
                  ("local_transform:" Transform)?

MateFile      ::= "type:" MateType
                  "parent:" Ref
                  "child:" Ref
                  ("at:" Map)?
                  ("constrains:" MateConstraint*)?
                  ("pairings:" InterfacePairing*)?

MateConstraint::= "- field:" Field
                  "operator:" "<=" | ">=" | "<" | ">" | "==" | "!="
                  "value_ref:" FieldOrConstant
                  ("message:" String)?

LayoutFile    ::= LayoutEntry*
LayoutEntry   ::= "- instance:" id
                  (AbsolutePose | RelativePose | GridPose)

AbsolutePose  ::= ("position_x_mm:" num)+
RelativePose  ::= "parent:" id
                  "transform:" Transform
GridPose      ::= "grid_id:" id
                  ("grid_position:" [String, String]
                  | "row_id:" String "bay_index:" Int)

Transform     ::= "translation:" [num, num, num]
                  ("rotation:" [num, num, num])?
                  ("scale:" [num, num, num])?

Ref           ::= id | id "/" interface_id
```

Key semantic constraints not captured by the grammar include: `InstanceFile` must not contain layout fields; a `LayoutEntry` must use exactly one of absolute, relative, or grid pose; and interface references in `Ref` must resolve to existing interfaces.

# 5. ESA: Engineering Static Analysis

Engineering Static Analysis (ESA) is the mechanism that makes EaC's shift-left quality strategy executable. It consumes ADL declarations and checks deterministic rules before the design is committed, moving compliance checking from downstream audit to upstream gating.

## 5.1 From ACC to ESA

Traditional Automated Compliance Checking (ACC) operates on completed design artifacts: drawings, BIM models, or IFC files [@eastman2009acc; @zhang2019acc]. This creates three structural problems:

1. **Information loss.** Design logic is frozen into geometry; reverse-extracting functional relationships is lossy.
2. **High feedback cost.** Violations are found after the design has become a tightly coupled cross-disciplinary model.
3. **No RLVR signal.** ACC can only judge finished designs; it cannot reward an agent during generation.

ESA addresses these problems by checking declarations directly. It is analogous to static analysis in software engineering and to Design Rule Checking (DRC) in chip design: rules are embedded in the generation workflow and reject non-compliant configurations as soon as they appear [@ieee1364].

ESA's scope is deliberately limited. It covers L2--L3 (core) and L4a (lightweight geometric extension). L0--L1 are handled by the ADL loader; L4b--L6 remain downstream verification and approval. This boundary keeps ESA deterministic, repeatable, and fast enough to run on every commit.

## 5.2 Why "Static Analysis"

ESA borrows the term "static analysis" from software engineering because it shares three characteristics:

1. **No physical execution.** It reasons about declarations and constraints, not about simulated physics.
2. **Deterministic results.** The same ADL declaration always yields the same pass/fail verdict.
3. **Low cost.** It completes in milliseconds to hundreds of milliseconds, suitable for pre-commit hooks and CI gates.

Just as lint and type checking do not replace unit tests, ESA does not replace CAE/CFD or human review. It intercepts a large class of low-level, deterministic errors so that expensive validation can focus on problems that genuinely require expert judgment.

## 5.3 Four Operational Principles

ESA is governed by four principles designed to make it usable in real engineering practice.

**Principle I: Rules are waivable.** Physical boundary conditions cannot be fully captured by any finite rule set. ESA allows authorized engineers to waive specific rules, but every waiver must be recorded as part of the design history and must trigger downstream strengthened validation (e.g., higher-fidelity CAE simulation or physical testing). The goal is to convert "above-spec" decisions from informal judgment into auditable risk management.

**Principle II: Focus on baseline rules.** Initial deployments should target mechanical, deterministic clauses: fire separations, egress widths, minimum clearances, power budgets, U-space conflicts. These rules have binary verdicts, small dispute space, and high automation payoff. Rule libraries should be modular so that projects can compose national codes, local standards, and internal controls.

**Principle III: Shift left and optimize signal-to-noise.** Software engineering has shown that lint and type checks, run before commit, free code review to focus on architecture and logic [@chiari2024iacstatic]. ESA applies the same logic to engineering: it intercepts power-budget violations, U-space conflicts, and interface mismatches before they reach human reviewers or downstream tools.

**Principle IV: AI-assisted rule authoring.** Rule-library construction is a key adoption bottleneck. Under expert supervision, large language models can extract candidate formal rules from regulation text, historical review comments, and design guidelines [@yang2024llmacc; @nakhaee2024kgllm], lowering the initial cost of rule engineering. Long-term, rule libraries should be community-governed: core rules maintained by standards bodies, domain rules contributed by practitioners, and quality assured through version control and certification.

## 5.4 Rule Catalog

As of this writing, piki implements 64 rules, 62 registered by plugins and 2 built-in interface checks. Table 3 breaks them down by plugin and level.

| Plugin                    | Rules  | Primary domain                                     |
| ------------------------- | ------ | -------------------------------------------------- |
| telecom                   | 28     | Telecom rooms, racks, servers, PDUs, cables, fiber |
| keyboard                  | 14     | Mechanical-keyboard assembly, DFX, matrix          |
| datacenter                | 9      | Modular containers, power units                    |
| environments              | 4      | Operating environment, material compatibility      |
| manufacturing             | 5      | Process and material constraints                   |
| consumer_electronics      | 3      | Small-electronics netlist-style connections        |
| Built-in interface checks | 2      | Interface-type existence, direction consistency    |
| **Total**                 | **64** | —                                                  |

The telecom plugin is the most mature. Representative rules include:

| Rule ID                 | Name                    | Level | Description                                                    |
| ----------------------- | ----------------------- | ----- | -------------------------------------------------------------- |
| `INTERFACE-COMPAT-001`  | Interface compatibility | L2    | Mate or Connection endpoints have pairable interface types     |
| `INTERFACE-CABLE-001`   | Cable-interface match   | L2    | Selected `cable_type` matches port interface type              |
| `TELECOM-POWER-001`     | PDU power budget        | L3    | PDU load does not exceed capacity threshold                    |
| `TELECOM-RACK-001`      | U-space conflict        | L3    | Devices in the same rack do not occupy overlapping U positions |
| `TELECOM-RACK-002`      | Rack capacity           | L3    | Total device height does not exceed available rack units       |
| `TELECOM-COLLISION-001` | In-rack 3D collision    | L4a   | AABB-based spatial conflict detection                          |
| `TELECOM-WEIGHT-001`    | Rack load               | L3    | Total device weight does not exceed rack load limit            |
| `TELECOM-FLOOR-002`     | Aisle width             | L4a   | In-row rack spacing satisfies maintenance aisle requirement    |

Rules are registered through a `@rule(rule_id, name, priority, severity)` decorator. The layered registration allows projects to enable only L2 during logical design and add L3--L4a during detailed layout.

## 5.5 Waiver Mechanism

A structured waiver system is part of the ESA design, though the current piki prototype only supports `--skip <rule_id>` and `warning_only` configuration. The target design records each waiver as a YAML file containing:

| Field                   | Meaning                              | Example                                          |
| ----------------------- | ------------------------------------ | ------------------------------------------------ |
| `rule_id`               | Waived rule                          | `TELECOM-FLOOR-002`                              |
| `target`                | Affected object(s)                   | `RACK-A01`, `RACK-A02`                           |
| `scope`                 | Single file, branch, or global       | `branch:feature/legacy-room`                     |
| `rationale`             | Technical and business justification | "Existing building column grid limits expansion" |
| `author`                | Requester                            | engineer ID                                      |
| `approver`              | Authorizer                           | senior engineer / compliance lead                |
| `expires_at`            | Expiration (optional)                | `2027-06-20`                                     |
| `downstream_tasks`      | Strengthened validation tasks        | `["CFD-thermal-sim", "site-survey"]`             |
| `created_at` / `commit` | Audit trail                          | timestamp and Git hash                           |

Waivers are submitted with ADL files and reviewed in pull requests. A waiver is not a bypass; it transfers responsibility from the deterministic rule engine to a higher-cost validation activity. If the downstream task fails, the waiver is reconsidered.

## 5.6 Diagnostic Output

ESA produces a uniform diagnostic structure that can be consumed by humans, CI dashboards, IDEs, and PR bots. On the telecom rack sample, `piki check` completes in under 200 ms on a laptop and reports one warning and 29 passes:

```text
[PASS] INTERFACE-COMPAT-001: Interface type compatibility
...
[FAIL] TELECOM-FLOOR-002: Aisle width check
       Racks RACK-A01 and RACK-A02 are -600.0 mm apart; required 600.0 mm
============================================================
Total: 0 errors, 1 warning, 29 passed
============================================================
```

The JSON form exposes the same data:

```json
{
  "passed": true,
  "error_count": 0,
  "warning_count": 1,
  "pass_count": 29,
  "results": [
    {
      "rule_id": "TELECOM-FLOOR-002",
      "name": "Aisle width check",
      "passed": false,
      "message": "Racks RACK-A01 and RACK-A02 are -600.0 mm apart; required 600.0 mm",
      "severity": "WARNING"
    }
  ]
}
```

The diagnostic model is compatible with the Language Server Protocol (LSP), so the same output can drive terminal summaries, JUnit XML dashboards, IDE overlays, and GitHub Checks API comments.

## 5.7 Integration with CI/CD and Pre-commit

ESA is designed to run inside the same workflows that software engineers already use. A typical EaC CI/CD pipeline has the following stages:

| Stage              | Trigger      | Content                                                   | Failure policy    |
| ------------------ | ------------ | --------------------------------------------------------- | ----------------- |
| Lint               | Every commit | YAML/TOML format, trailing whitespace, naming conventions | Block commit      |
| Parse              | Every commit | ADL syntax (L0)                                           | Block merge       |
| Schema Check       | Every commit | pydantic / JSON Schema (L1)                               | Block merge       |
| Link Check         | Every PR     | Reference integrity, Mate consistency (L2)                | Block merge       |
| Rule Check         | Every PR     | Business and fast-geometry rules (L3--L4a)                | Block merge       |
| Deliverable Build  | Post-merge   | BOM, drawings, port maps                                  | Report warnings   |
| Nightly Regression | Scheduled    | Full sample suite, geometry, CAE/CFD                      | Report and notify |

Pre-commit hooks mirror the cheaper checks locally, giving engineers sub-second feedback before a commit is made. The same configuration file drives both pre-commit and CI, preventing "passes locally, fails in CI" inconsistencies.

# 6. Evaluation

This section evaluates whether EaC meets its design goals through a pilot experiment on the piki prototype and a roadmap for a larger benchmark.

## 6.1 Research Questions and Methodology

We address the three research questions from \S 1:

- **RQ1.** Can ADL express real engineering designs in a text-native, machine-checkable form?
- **RQ2.** Can ESA detect common design violations at design time with latency suitable for CI/CD gates?
- **RQ3.** Does the representation provide the verifiable reward signal needed for RLVR-based agents?

The pilot uses three sample projects in the piki repository. We measure:

1. **Expressiveness:** whether each sample can be fully declared in ADL;
2. **Check latency:** the time for `piki check` to complete L0--L4a validation;
3. **Rule coverage:** the number and type of rules that apply;
4. **Deliverable generation:** whether downstream artifacts (BOM, panel views, port maps) can be produced.

All measurements are taken on a laptop-class machine with warm caches; timings are the median of five runs.

## 6.2 Sample Projects and Results

Table 4 summarizes the three samples.

| Sample                 | Domain                       | ADL files | Rules applied | Result | Errors | Warnings | Check latency |
| ---------------------- | ---------------------------- | --------- | ------------- | ------ | ------ | -------- | ------------- |
| 01-telecom-expansion   | Telecom rack deployment      | 42        | 30            | Pass   | 0      | 1        | 175 ms        |
| 02-modular-datacenter  | Modular container datacenter | 38        | 34            | Fail   | 12     | 0        | 210 ms        |
| 03-mechanical-keyboard | Keyboard assembly            | 29        | 28            | Fail   | 4      | 0        | 185 ms        |

**Sample 01: Telecom rack expansion.** This is the most mature sample. It declares two racks, multiple servers, PDUs, switches, transceivers, and fiber connections. `piki check` passes all L2--L4a rules and produces one warning: the aisle between `RACK-A01` and `RACK-A02` is narrower than the required 600 mm, because the two racks are placed back-to-back in the sample layout. The sample demonstrates expressiveness (all entities have ADL declarations), fast feedback (sub-200 ms), and deliverable generation (BOM, rack panel views, port maps, cable lists).

**Sample 02: Modular datacenter.** This sample pushes into container-level power and cooling. It currently fails 12 rules, dominated by 3D collision false positives from coarse bounding boxes and `LAYOUT-001` errors where the current PLL model does not fully capture container-relative coordinates. These failures are not hidden defects; they document the current boundary of PLL expressiveness and collision-detection precision.

**Sample 03: Mechanical keyboard.** This sample exercises consumer-electronics-style part mating and matrix wiring. It fails four `LAYOUT-001` errors because the keyboard layout uses a continuous 2D grid that is not yet fully supported by the discrete PLL model.

**Answers to RQ1 and RQ2.** ADL can express a representative telecom rack design completely and correctly (RQ1). ESA detects violations in under 200 ms, meeting the latency budget for CI/CD pre-commit and PR gates (RQ2). The two failing samples honestly delimit the current coverage boundary rather than invalidating the approach.

## 6.3 SD-HWE-Bench: A Planned Agent Benchmark

The pilot validates feasibility, but it does not test whether an agent can generate ADL from a natural-language requirement. We are designing **SD-HWE-Bench** (Software-Defined Hardware Engineering Benchmark) to fill this gap. It will be reported in a companion paper; here we describe its design so that readers can assess the larger evaluation plan.

**Task paradigm.**

```text
Input:  natural-language engineering requirement
Output: structured ADL declaration (piki YAML)
Score:  L0--L4 rule-check pass rate + deliverable quality + L6 sign-off assessment
```

Unlike SWE-bench, which tests patch generation against existing code bases [@jimenez2024swebench], SD-HWE-Bench tests creation from scratch, because declarative engineering design as a practice does not yet exist at scale.

**Initial domain: telecom rack deployment.** We choose this domain because it matches the current ADL and ESA capabilities:

- Space is discrete (rack units), avoiding continuous 3D constraint solving.
- Constraints are mostly algebraic (power budget, weight, U-space conflict).
- Interface types are enumerable (SFP28, RJ45, IEC-C13/C14).
- `piki check` completes in ~200 ms, satisfying RLVR's need for fast reward signals.

**Planned metrics.**

| Metric           | Definition                                                          |
| ---------------- | ------------------------------------------------------------------- |
| `Pass@1`         | Percentage of tasks whose first ADL output passes all enabled rules |
| `Pass@k`         | Percentage passing at least one of $k$ sampled outputs              |
| `Latency`        | Median `piki check` time per output                                 |
| `Coverage`       | Fraction of task requirements reflected in generated ADL            |
| `Human sign-off` | Fraction rated acceptable by domain experts (L6 proxy)              |

**Connection to RQ3.** SD-HWE-Bench directly tests the RLVR causal chain: if ADL + ESA provide a structured, deterministic reward signal, then agents trained with that signal should outperform agents trained only on text completion or human preference. The benchmark will include both a zero-shot/generation track and a reinforcement-learning track.

**Current status.** SD-HWE-Bench is in design. A task schema, annotation protocol, and initial set of 20 tasks have been drafted. Large-scale agent training and evaluation are planned for the companion paper.

## 6.4 Threats to Validity

**Construct validity.** Our measures of "expressiveness" and "correctness" are operationalized through ADL loading and rule passing. This may miss requirements that are not yet codified as rules. We mitigate this by involving domain experts in task design for SD-HWE-Bench.

**Internal validity.** The three samples are hand-authored by the development team, so they may reflect the capabilities the language was built to support. The failing samples partially address this by showing where the language does not yet work.

**External validity.** The evaluation is limited to telecom, datacenter, and consumer-electronics assembly. Generalization to civil, mechanical, HVAC, and fluid systems requires additional Part Families, Mate types, and PLL extensions.

**Reliability.** Check latency depends on machine load and cache state. We report medians of five warm runs, but a dedicated CI environment will give more stable numbers.

## 6.5 Summary of Evaluation

The pilot provides preliminary evidence for RQ1 and RQ2: ADL can express a real telecom rack design, and ESA can validate it in under 200 ms. RQ3 remains open and is the target of SD-HWE-Bench. The evaluation is intentionally modest: rather than overclaim, we state the current boundary and the next validation step.

# 7. Related Work

EaC sits at the intersection of software engineering, model-driven engineering, AI benchmarks, and physical-system design. We organize related work by community and highlight the gap EaC fills.

## 7.1 Automated Compliance Checking

Automated Compliance Checking (ACC) interprets building codes and checks BIM or IFC models against them [@eastman2009acc; @zhang2019acc]. Recent work applies LLMs to parse regulations and generate formal rule candidates [@fuchs2024llmregs; @yang2024llmacc; @nakhaee2024kgllm].

ACC is downstream: it audits finished artifacts. ESA is upstream: it gates declarations during generation. ACC cannot provide millisecond rewards to a design agent; ESA is designed for that purpose. ACC and ESA are complementary---ACC remains necessary for L6 approval, while ESA catches deterministic violations early.

## 7.2 Model-Driven Engineering and SysML v2

SysML v2 is a standardized systems-modeling language with rich semantics for structure, behavior, and requirements [@omg2024sysml]. It is primarily human-facing and repository-centric. ADL is narrower: it focuses on the subset of systems engineering needed for physical assembly---parts, mates, layouts, and deterministic rules---and is optimized for agent generation and Git-based workflows. SysML v2 could in principle be a target serialization for ADL; ADL could be viewed as a domain-specific, text-first front end.

## 7.3 BIM and IFC

BIM and IFC dominate architecture and construction. IFC provides a neutral exchange format, but it couples identity, geometry, and relations in a graph that admits multiple equivalent serializations [@liu2023ifcversion]. This makes line-level version control and deterministic checking difficult. ADL treats IFC as a downstream exchange target, not as a source of truth.

## 7.4 Infrastructure as Code Static Analysis

IaC tools such as Terraform and Ansible express infrastructure as textual declarations, and static-analysis tools (tfsec, Checkov) detect security and compliance violations in seconds [@chiari2024iacstatic]. EaC generalizes this pattern to physical engineering. The key difference is that IaC describes an already-digitized domain, whereas EaC must first define the digital abstraction of physical objects.

## 7.5 Chip Design and DRC

Chip design has long used textual netlists (Verilog) as the source of truth and runs Design Rule Checking during placement and routing [@ieee1364]. Recent work applies reinforcement learning to macro placement, using fast DRC signals as rewards [@mirhoseini2020rlchip], and benchmarks LLM agents on DRC script synthesis [@kim2025rule2drc]. Rule2DRC is particularly close in spirit: it treats executable verification as the target for agents. EaC extends this philosophy from 2D/2.5D chip layouts to general 3D physical assemblies.

## 7.6 Code Agents and Benchmarks

SWE-bench evaluates agents on resolving real GitHub issues, with test-suite pass/fail as the objective [@jimenez2024swebench]. Multi-SWE-bench extends the paradigm to multiple programming languages. SWE-RL shows that reinforcement learning on these verifiable signals improves bug-fixing success [@sweagent2025swerl]. EaC aims to create an analogous verifiable artifact for engineering design, so that similar agent-training methods can apply.

## 7.7 AI Benchmarks for Engineering Design

Recent benchmarks assess LLMs on engineering tasks: EngDesign covers broad engineering problem solving [@engdesign2025], AEC-Bench targets architecture, engineering, and construction [@galanos2026aecbench], and TeleQnA tests telecommunications knowledge [@maatouk2023teleqna]. These benchmarks evaluate knowledge or final-answer correctness. SD-HWE-Bench will instead evaluate the ability to produce a structured, checkable design declaration---a different construct that aligns with RLVR training.

## 7.8 Comparison Matrix

Table 5 positions EaC against the closest related work.

| Work                  | Target                      | Representation            | Validation timing     | Reward signal for RL | Open source   |
| --------------------- | --------------------------- | ------------------------- | --------------------- | -------------------- | ------------- |
| ACC (Eastman, Zhang)  | Building compliance         | BIM / IFC                 | Downstream audit      | No                   | Partial       |
| SysML v2              | Systems modeling            | Repository model          | Model checking        | No                   | Specification |
| BIM / IFC             | AEC design                  | Central model             | Collision detection   | No                   | Standard      |
| IaC static analysis   | Cloud config                | Text (HCL/YAML)           | Pre-commit / CI       | Indirect             | Yes           |
| Chip DRC / RL         | Chip layout                 | Verilog netlist           | During placement      | Yes (DRC)            | Partial       |
| SWE-bench             | Code repair                 | Git repo + patch          | CI test execution     | Yes (tests)          | Yes           |
| EngDesign / AEC-Bench | Engineering QA              | Natural language / images | Human or model judged | No                   | Varies        |
| **EaC (this work)**   | Physical engineering design | ADL text                  | Design-time ESA       | **Yes (rules)**      | Yes (piki)    |

The differentiating feature of EaC is the combination of a **text-native, structured design representation** and a **deterministic, design-time rule engine** that can serve as a reward signal for generative agents.

# 8. Conclusion and Future Work

This paper proposes Engineering as Code, a paradigm that treats structured, textual design declarations as the source of truth for physical engineering systems. Our central claim, the Information Representation Hypothesis, is that the lag of AI in engineering is primarily a representational problem: without a machine-readable, checkable design language, agents cannot receive the fast deterministic feedback that has enabled progress in code, math, and chip design.

We make three contributions. First, we articulate the hypothesis and its testable predictions. Second, we introduce ADL, a three-layer language that separates part identity, mating relationships, and spatial layout. Third, we introduce ESA, a deterministic rule engine that moves compliance checking upstream, and we define its scope, principles, and diagnostic format. The piki prototype validates the approach on a telecom rack sample, checking 64 rules in under 200 ms.

## Limitations

We have been explicit about the current boundaries of the work:

- **Evaluation scale.** The pilot has only three samples, two of which fail. The results support feasibility, not generalizability.
- **Geometric coverage.** PLL supports discrete coordinates and simple continuous transforms, but not complex parametric assemblies or continuous 3D routing.
- **Downstream verification.** L4b (exact geometry), L5 (physics simulation), and L6 (human/AI approval) are outside ESA and are not yet implemented.
- **Waiver system.** Only `--skip` and `warning_only` are implemented; the structured waiver workflow is a design, not code.
- **EPM and AssemblyHub.** The package manager and collaboration platform are conceptual.
- **No agent experiment yet.** SD-HWE-Bench is in design; no RLVR training results are reported.

## Future Work

The immediate next step is SD-HWE-Bench: a benchmark that evaluates agents on generating ADL from natural-language requirements. It will test the core prediction of the Information Representation Hypothesis---that a structured, checkable representation improves agent design capability even when the underlying model is unchanged.

Beyond the benchmark, several directions are important:

1. **PLL extensions.** Support continuous 3D constraints, parametric assemblies, and routing problems such as HVAC and cable trays, possibly by integrating external geometric solvers.
2. **Structured waivers.** Implement the waiver data model and its integration with Git, CI, and downstream CAE tools.
3. **EPM and AssemblyHub.** Build the package manager and collaboration platform needed for community-scale reuse of Part libraries and rule sets.
4. **Domain expansion.** Develop Families and rules for civil, structural, mechanical, and fluid systems.
5. **RLVR training.** Train design agents using ESA rule pass/fail as the reward signal and compare against baselines trained on text completion or human preference.

Engineering as Code reframes a familiar question. Instead of asking how to make AI better at engineering, we ask how to make engineering better for AI---and for the humans who work with it.

## Data Availability

The piki prototype, sample projects, and replication scripts are available as an anonymous artifact at [ANONYMOUS LINK]. The artifact includes installation instructions, the rule catalog, and the commands used to produce the results in \S 6.

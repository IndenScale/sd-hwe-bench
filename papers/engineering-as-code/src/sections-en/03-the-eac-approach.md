# The Engineering as Code Approach

EaC is a proposition about infrastructure. It says: before we ask whether AI can design physical systems, we should ask whether those systems are represented in a form that is operable by a software engineering toolchain. This section defines the paradigm, articulates its core hypothesis, and connects that hypothesis to the RLVR literature and the layered design of the ESA.

## What Is EaC

**Engineering as Code (EaC)** is the practice of treating a structured, textual design declaration as the single source of truth for a physical engineering system, and building a software engineering toolchain — version control, static analysis, CI/CD, and automated verification — around that representation.

EaC is not a replacement for CAD or BIM. Physical engineering will always need geometric modeling, simulation, and manufacturing output. EaC separates concerns: *design intent* (what parts to use, how they connect, where they are placed) is expressed textually in the ADL, while *geometry instantiation* and *analysis* consume that declaration as input. This is the same separation that chip design achieves with hardware description languages: Verilog/VHDL describe intent; placement tools generate geometry; DRC checks the result [@ieee1364].

EaC has three pillars, but forms a single integrated proposition:

1. **ADL** (§4) is the *representation layer*: an engineering design language designed to be read, checked, diffed, and versioned by a SE toolchain.
2. **ESA** (§5) is the *verification layer*: a rule engine that provides fast, deterministic correctness feedback, making RLVR possible.
3. **The Information Representation Hypothesis** (§3.2) is the *theoretical anchor*: connecting these technical choices to a testable claim about why AI progress in physical engineering has stalled.

## The Information Representation Hypothesis

We assert:

> **The Information Representation Hypothesis**. The lag of AI in physical engineering is primarily caused by the absence of a structured, text-native, machine-checkable design representation, rather than by insufficient model capability or the intrinsic complexity of physics.

This hypothesis is **information-theoretic**, not computational. It does not claim that physics is simple, or that current models are already capable enough to design complex systems. It claims that *even if* models had the capability, current representations would prevent them from improving, because those representations do not support the learning signal that has driven AI progress in code, mathematics, and chip design — fast, deterministic correctness feedback.

### Evidence from Adjacent Domains

The hypothesis rests on measurable regularities from three domains:

**Code**. SWE-bench tasks require an agent to fix real GitHub issues [@jimenez2024swebench]. The reward signal is a test suite: the agent's patch either passes or fails. SWE-RL demonstrated that with this signal alone, without human demonstrations, agents could be trained to solve 42% of SWE-bench Verified tasks [@sweagent2025swerl]. The representation — a Git repository with a test suite — is the scaffolding that makes RLVR feasible.

**Mathematics**. DeepSeekMath and DeepSeek-R1 trained on formal theorem proving, where the correctability of each proof step is verifiable [@shao2024deepseekmath; @deepseek2025r1]. A key finding from Let's Verify Step by Step is that a process-supervised reward model (PRM) outperforms an outcome-supervised reward model (ORM) [@lightman2023letsverify]. For PRM to be effective, intermediate steps must be individually verifiable — a property that only a structured, decomposable representation can provide.

**Chip Design**. Google's chip placement work uses Verilog netlists as input and design rule checking (DRC) as the reward signal [@mirhoseini2020rlchip]. DRC checks manufacturability constraints (spacing, layer rules, timing) and returns a pass/fail verdict. The representation (netlist + standard cell library) decouples functional intent from geometric implementation, making the reward computable.

The common structure is:

```text
Structured representation → Deterministic checker → Fast feedback loop → RLVR training feasible
```

Physical engineering currently lacks the first two items. CAD/BIM models are not structured for checking; downstream review is not fast enough. The loop is broken.

### Testable Predictions

The hypothesis yields concrete predictions:

- **P1.** Agents that receive deterministic ESA pass/fail feedback on their ADL outputs will produce designs with fewer violations than agents that receive only natural-language task descriptions.
- **P2.** The improvement in P1 holds when controlling for model capability (same base model, same task difficulty).
- **P3.** The L0–L4 layered diagnostic format will achieve faster error correction than a flat error list, because structured diagnostics allow agents to localize and prioritize failures by layer.
- **P4.** Agent designs that pass the ESA will produce fewer downstream errors (collisions, assembly failures) than designs verified with coarser-grained checkers or with no checking at all.

SD-HWE-Bench (§6.3) is specifically designed to test P1–P3. P4 is a long-term empirical goal.

## Why This Is a Software Engineering Contribution

Designing a source-code representation for a new domain is a software engineering problem. It requires decisions about:

- **Syntax and semantics**. What is the atomic unit (Part)? How are relationships declared (Mate)? How is spatial layout expressed without embedding part identity? These are language design questions, analogous to designing a type system or IR.
- **Layered verification**. Which checks are cheap enough to run on every keystroke (L0)? Which checks require global analysis but remain deterministic (L3–L4)? Which checks are inherently non-deterministic or too expensive (L5–L6)? This is a static analysis pipeline design problem.
- **Toolchain integration**. How do design artifacts interact with Git (diff, blame, bisect), CI (pre-commit hooks, gating), and diagnostics (structured output, editor integration)? These are software engineering infrastructure questions.
- **Extensibility**. How do users add new Part Families, rules, or domain vocabularies without modifying the core engine? This is a plugin and API design problem.

EaC answers these questions for physical engineering, but its framework — text-native DSL + layered static analysis + toolchain integration — is domain-agnostic. The same template can be applied to clinical trial protocols, legal contracts, or infrastructure configurations. In this sense, EaC is both a concrete system for physical engineering and a methodology for extending SE infrastructure to domains that are textualizable but currently under-structured.

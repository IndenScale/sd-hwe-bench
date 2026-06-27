# SWE-Bench for HWE

---

**The single most important bottleneck in AI for engineering is not model capability. It's the "representation gap."**

We don't have a SWE-bench for hardware engineering. Without it, AI can't learn to design.

Here's what I'm building — and why.

---

## The Problem

Software engineering has had its renaissance in AI. SWE-bench turned GitHub issues into reproducible benchmarks. Agents went from <5% to >40% resolve rate in two years. Code is text-native — compilers, linters, test suites give millisecond feedback.

Hardware engineering? We're still in the dark ages.

Design data lives in CAD binaries, PDF spec sheets, Excel spreadsheets, and commercial GUI sessions. There is no "design as code" — no standard text representation that an AI can read, write, and diff. No compiler. No test suite. No benchmark.

This creates a **negative feedback loop**: no representation → no evaluation → no training → no capability.

I call this the **Representation Gap**. It's the reason AI excels at chip design (which has HDL) but struggles with telecom racks, data centers, and mechanical assemblies.

---

## What I'm Building: SD-HWE-Bench

**SD-HWE-Bench** is the first executable benchmark for declarative hardware engineering.

The core insight: hardware engineering has *even richer verifiable constraints* than software. Physics doesn't negotiate. But nobody has built the infrastructure to expose those constraints to AI agents.

Here's the loop:

1. **Natural language requirement** — "Design a 42U rack deployment with 8 servers..."
2. **AI Agent** generates YAML declarations (instances, layouts, connections, mates)
3. **Rule engine** checks L0-L4: syntax → schema → reference integrity → business rules → geometry
4. **Millisecond-to-second deterministic feedback** — no CFD, no FEA, no human review

The benchmark covers **19 telecom design tasks** across 6 task types (instance declaration, layout, connection, mating, comprehensive, incremental). Each task is a real engineering design increment, extracted from a canonical ADL project's git history — exactly how SWE-bench mines real GitHub issues.

---

## Early Results

| Model | Pass@1 | Avg Score |
|---|---|---|
| **Kimi (k2.7)** | **100%** | **87%** |
| DeepSeek-v4-Flash | 84% | 81% |
| DeepSeek-v4-Pro | 81% | 79% |

A few things stand out:

- **The benchmark discriminates.** Kimi at 100% vs DeepSeek Pro at 81% — this is one of the widest model capability spreads I've seen in any benchmark.
- **Failures cluster at L2-L3.** Cross-file reference integrity and engineering constraints (U-slot conflicts, power budgets) are the real bottlenecks, not syntax.
- **Comprehensive design is the hardest differentiator.** Kimi: 100%. Flash: 20%. Pro: 0%. This is the task that separates engineers from code generators.
- **Self-repair is barely engaged.** Average self-check rounds < 0.5. The agents aren't even trying to fix their own mistakes — yet. This means the real ceiling is much higher.

---

## The Bigger Picture: Engineering RLVR

This isn't just a benchmark. It's infrastructure for **Engineering RLVR** — Reinforcement Learning from Verifiable Rewards applied to physical design.

The RLVR expansion path is clear: AlphaGo (game rules) → DeepSeek-R1 (math answers) → SWE-bench (code + tests) → **HWE** (engineering constraints).

The winner-take-all question: which domain builds deterministic, cheap, automated verification infrastructure first?

Software won Round 1. Hardware engineering is Round 2 — and it has *orders of magnitude more verifiable constraint density* than code.

---

## Why "Just Use CAD MCP" or "Computer-Using Agents" Is a Trap

Two seductive shortcuts are getting a lot of attention:

- **CUA (Computer-Using Agents)**: Let AI click buttons in CAD like a human. Fatal flaws: pixel-level fragility, no deterministic verification signal, impossible to parallelize at RLVR scale.
- **CAD MCP**: Wrap proprietary CAD in a tool API. Fatal flaw: the source of truth remains the proprietary binary. You're still locked out of multi-domain interoperability and millisecond verification.

The right approach: **text-native, declarative, separation of concerns.** The engineering description *is* the source of truth. Tools compile from it. The representation layer must be independent of any vendor's kernel.

---

## What I'm Looking For

I'm writing two papers on this work — one on **Engineering as Code** as a paradigm (targeting FSE 2027 Vision Track), one on **SD-HWE-Bench** as a benchmark (targeting NeurIPS 2027).

I'm actively seeking:

- **Academic collaborators** in SE/ML with benchmark publication experience
- **Industry partners** with real engineering design datasets (telecom, data center, energy)
- **Anyone who sees the same representation gap** and wants to close it

If this resonates, **DM me here on X**. I'd love to talk.

---

**More details:** [indenscale.github.io](https://indenscale.github.io/)

**Engineering as Code series:** [indenscale.github.io/eac](https://indenscale.github.io/eac/)

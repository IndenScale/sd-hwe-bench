# How SD-HWE-Bench Mirrors SWE-Bench (And Why That Matters)

---

If you work in an AI lab, you already have a muscle for SWE-bench.

You know the ritual: pick a GitHub issue, generate a patch, run the test suite, score pass/fail. The loop is deterministic, reproducible, and scales to millions of trials. That's why it works.

If you want AI labs to help hardware engineers, you don't ask them to learn CAD. You speak their language.

---

## The SWE-Bench Formula: Issue → Patch → Tests

AI labs have built their entire RLVR training pipeline around three primitives:

| Primitive | Software                                        | Why it matters                                             |
| --------- | ----------------------------------------------- | ---------------------------------------------------------- |
| **Issue** | GitHub issue describing a bug/feature           | Defines _what needs to change_, with full context          |
| **Patch** | Diff that modifies source files                 | The agent's output — text-native, diffable, verifiable     |
| **Tests** | Test suite that passes iff the patch is correct | Deterministic reward signal, millisecond-to-minute latency |

Strip away everything else — the leaderboard, the paper, the community drama — and SWE-bench is just a generator of (issue, patch, tests) triples at scale. Every triple is a self-contained training example. Feed them into an RL pipeline, and the model learns to solve real engineering problems.

The AI lab doesn't need to understand your domain. It just needs a steady supply of clean triples.

---

## Building the HWE Triple

SD-HWE-Bench maps each SWE-bench primitive to its hardware engineering equivalent:

### Issue → Natural Language Engineering Requirement

A SWE-bench issue says: "Fix the race condition in the connection pool timeout handler."

An SD-HWE-Bench issue says: "Design a 42U rack with 8 servers, 2 switches, 2 PDUs. Servers need dual power. All devices must be assigned non-overlapping U-slots. Generate BOM and port-map."

Same structure. Same clarity. Same "here's the problem, here's the constraints." The only difference: instead of describing a bug in code, it describes what needs to be built.

### Patch → YAML Declarations

A SWE-bench patch is a git diff that modifies `.py` files.

An SD-HWE-Bench patch is a set of YAML files the agent creates:

- `instances/` — what equipment is present, with which attributes
- `layouts/` — where each device sits in the rack
- `connections/` — which ports connect to which
- `mates/` — physical coupling constraints

Same principle: the agent's output is **text that can be read, written, diffed, and version-controlled**. No CAD binaries. No GUI sessions. Just files.

### Tests → L0-L4 Verifier

A SWE-bench test suite runs `pytest` and returns pass/fail.

SD-HWE-Bench runs a layered verifier that returns pass/fail **per layer** — giving the agent more nuanced reward signals:

| Layer | What it checks                                                                            | Latency |
| ----- | ----------------------------------------------------------------------------------------- | ------- |
| L0    | Syntax: is the YAML valid?                                                                | <1ms    |
| L1    | Schema: are all required fields present and typed correctly?                              | ~10ms   |
| L2    | Reference integrity: do all referenced Part IDs, port names, and rack IDs actually exist? | ~50ms   |
| L3    | Business rules: does the power budget hold? Are U-slots overlapping?                      | ~100ms  |
| L4    | Geometry: do 3D placements cause collisions?                                              | ~500ms  |

All layers together run in under a second. The whole verifier is a single command: `piki check --format json`. The output is machine-readable scores per layer.

This is the HWE test suite. Deterministic. Fast. Ready for RLVR.

---

## Where the Tasks Come From: Canonical Projects

SWE-bench mines real GitHub repos — issues, commits, and test suites from actual open-source projects. The tasks are real software engineering work that humans actually did.

SD-HWE-Bench does the same, but for engineering design.

We maintain **canonical ADL projects** — complete, incrementally-built engineering designs in a specific domain (currently telecom rack design). Each canonical project evolves through a git history where each commit represents a distinct design increment:

```text
canonical/telecom-rack/
├── git history:
│   commit 1: Declare 4 servers with correct TDP and interfaces
│   commit 2: Add layout — assign devices to U-slots
│   commit 3: Connect servers to switches via SFP28
│   ...
│   commit N: Full 42U rack with all devices, connections, and mates
└── task_manifest.yaml   ← maps commit boundaries to task definitions
```text

From each commit boundary, `extract_tasks.py` generates a task:

- **Scaffold**: the project state _before_ the commit (what the agent sees)
- **Solution**: the project state _after_ the commit (ground truth, hidden from agent)
- **Requirement**: the natural language description of what the commit achieves

This is the HWE equivalent of "here's a repo at a broken state, here's the issue, here's the fix." The agent gets the scaffold and the requirement. It must produce the solution.

---

## Why This Matters: Lowering the Adoption Barrier

AI labs don't need to understand telecom engineering. They don't need to learn CAD. They don't need to hire domain experts.

They just need to plug SD-HWE-Bench into their existing RLVR pipeline:

```python
for task in benchmark.tasks():
    scaffold = task.scaffold()
    requirement = task.requirement()

    patch = model.generate(scaffold, requirement)
    score = verifier.check(patch, task.expected())

    pipeline.record(task, patch, score)
```text

That's it. The same pipeline that trains on SWE-bench trains on SD-HWE-Bench. Same infra. Same abstractions. Same scaling properties.

The hardware engineering community's job isn't to convince AI labs to care about engineering. It's to **make caring effortless** — by providing clean, self-contained (issue, patch, test) triples in the format the labs already consume.

---

## The Vision Ladder: This Is a Prototype

What we have today is the **minimum viable verifier** — millisecond rule checks that replace the most tedious, repetitive parts of design review. It works. It already discriminates between models (Kimi 100% vs DeepSeek Pro 81%). It already surfaces the right failure patterns (L2 reference integrity, L3 constraint violations).

But this is a prototype. The real thing looks like this:

**With AI lab and industrial partners, we build a CI cluster behind SD-HWE-Bench.** The cluster runs:

| Stage                              | What it does                                           | Latency   |
| ---------------------------------- | ------------------------------------------------------ | --------- |
| **L0-L4 verifier** (today)         | Syntax, schema, references, rules, geometry            | <1 second |
| **High-precision geometry kernel** | Parasolid/ACIS-grade collision, clearance, tolerancing | seconds   |
| **FEM/CFD simulation**             | Thermal, structural, airflow — automated mesh + solve  | minutes   |
| **HIL/VIL**                        | Hardware-in-the-loop, virtual integration lab          | hours     |

The agent proposes a design. The L0-L4 gate catches 80% of errors in under a second. If it passes, the design flows to the geometry kernel. If that passes, it hits FEM/CFD. If the sponsor wants to go all the way, it reaches HIL/VIL — physical hardware validating the AI's output.

This is an **AI-native industrial design pipeline**. The agent doesn't just pass a benchmark. It produces designs that survive every verification gate a real engineering organization cares about.

The verifier scales with the ambition of the sponsor. The triples stay the same. The RLVR pipeline doesn't change.

---

## Domain Roadmap

SD-HWE-Bench currently covers **telecom room capacity expansion** — 19 tasks on rack-level design, from single-device declaration to full 42U multi-rack deployment. This is our starting domain.

We plan to expand into:

| Domain                    | Example design problems                                                                                  | Key verifiers                                                 |
| ------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **Telecom base stations** | Channel modeling expansion, antenna placement, power distribution                                        | RF propagation, inter-site interference, structural wind load |
| **Data centers**          | HVAC layout, liquid cooling topology, maintainability corridors, PUE estimation                          | Thermal CFD, airflow modeling, energy efficiency metrics      |
| **More to come**          | We're domain-agnostic by design — any engineering discipline with declarative constraints is a candidate | —                                                             |

If your organization works in a domain where design is currently bottlenecked by manual review cycles, we want to talk. SD-HWE-Bench is designed to be extended. The task format, verifier interface, and canonical project methodology are domain-independent. Adding a new domain means contributing domain-specific rules and canonical projects — not rebuilding the infrastructure.

---

**This is Article 2/3 on SD-HWE-Bench.**

- Article 1: [SWE-Bench for HWE](https://x.com) — the vision
- → **Article 2: How it mirrors SWE-Bench** — the mechanics
- Article 3: How designs are expressed — ADL

DM me if you're building in this space, or visit [indenscale.github.io](https://indenscale.github.io/).

# 2. Related Work

This chapter is organized in three tiers: first reviewing the evolution of LLM evaluation and agent benchmarks, then focusing on the "computable representation + execution-based evaluation" paradigm in software engineering benchmarks, and finally analyzing the current state and systematic gaps of AI work in hardware engineering.

## 2.1 LLM Evaluation and Agent Benchmarks

The landscape of LLM evaluation has evolved from static knowledge probing (MMLU, HellaSwag) to dynamic, environment-interactive tasks. Agent benchmarks like SWE-bench [@jimenez2024swebench], SWE-bench Multimodal, and WebArena represent the state of the art: agents interact with repositories, browsers, or operating systems, and their outputs are evaluated through executable tests rather than reference strings.

Three design principles from this lineage inform SD-HWE-Bench:

1. **Executable evaluation**: pass/fail is determined by running real checks (unit tests, linters, compilers), not by LLM-as-judge or n-gram overlap.
2. **Realistic task sourcing**: tasks are extracted from real-world artifacts (GitHub issues, commit histories) rather than hand-crafted toy problems.
3. **Containerized reproducibility**: evaluation environments are packaged as Docker images to ensure cross-platform consistency.

## 2.2 The "Computable Representation + Execution" Paradigm

Software engineering benchmarks succeed because code is inherently computable: a compiler can check syntax, a test runner can verify behavior, and a linter can enforce style. This creates a tight feedback loop—agent generates code, tools evaluate it, agent iterates.

Physical engineering lacks this loop. CAD models require proprietary viewers, FEM simulations take hours, and manufacturing checks involve human inspectors. The EaC paradigm [@song2025eac] proposes to retrofit this computability onto engineering by representing designs as declarative text (ADL) and validating them through deterministic rule engines (DTS/piki). SD-HWE-Bench is the first benchmark to instantiate this paradigm at scale.

## 2.3 AI in Hardware Engineering: Current State and Gaps

Existing AI-for-engineering work falls into three categories, each with limitations that SD-HWE-Bench addresses:

1. **Generative design** (topology optimization, generative CAD): produces *geometry* but not structured, constraint-checkable *declarations*. The output is a mesh, not a part list with validated ports, power budgets, and mating constraints.

2. **NLP for requirements engineering**: extracts structured requirements from natural language documents but does not verify whether the resulting designs satisfy those requirements.

3. **Domain-specific copilots** (PCB routing, FPGA synthesis): operate within specialized, single-domain tools and cannot evaluate cross-disciplinary coordination (e.g., electrical + structural + fire safety constraints on the same design).

SD-HWE-Bench fills these gaps by providing a multi-domain, multi-constraint, executable evaluation framework where agents produce complete engineering declarations and are scored on correctness across electrical, structural, thermal, and electromagnetic compatibility dimensions.

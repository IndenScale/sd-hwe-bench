# 9. Limitations and Future Work

## 9.1 Domain Coverage

Currently telecom-only (rack expansion, data center, outdoor base station). Other domains—automotive harness, medical device, aerospace, PCB design, piping systems—are not yet included. Multi-domain expansion requires building new canonical projects and corresponding DTS rule plugins. An incremental path: reuse piki's plugin architecture to develop domain-specific DTS rules per new domain, then extract tasks from corresponding canonical projects.

## 9.2 Task Scale and Statistical Power

33 tasks (18% increase over v2's 28), but absolute count is far below mature code benchmarks (SWE-bench: 2294). Hard tasks increased from 7 to 13, but experiments use only one model (DeepSeek-v4-Flash) with single-pass sampling—insufficient to expose systematic inter-model differences. Multi-model comparison (GPT-4.1, Claude 4, Gemini 2.5, Kimi k2.7, DeepSeek-v4-Pro) and pass@5 multi-pass sampling are the next experimental priorities.

## 9.3 The Fundamental Differentiation Bottleneck: Deterministic Design Space

SD-HWE-Bench's core design constraint—all tasks sourced from deterministic canonical project increments—is both its strength (reproducible, automatable scoring) and its fundamental bottleneck. Deterministic tasks mean each has a unique correct solution; agent correctness is binary.

Real engineering's core challenges—multi-objective optimization, constraint conflict resolution, incomplete-information reasoning—are absent. Three new task types as future extension directions:

1. **Multi-objective optimization tasks**: given device lists and cost models, require minimizing rack count + minimizing cross-rack connections—infinitely many valid solutions scored by weighted metrics.
2. **Constraint conflict tasks**: PDU power insufficient for all devices; agent must choose between device downgrade or PDU addition—both paths valid, different costs.
3. **Incomplete-information tasks**: deliberately omit a specification section from scaffold; agent must infer implicit rules from existing designs.

These cannot be auto-extracted from git history—they require manual design.

## 9.4 L-Numeric Layer Limitations

L-Numeric demonstrated differentiation potential on site-stage6/7, but has current limits:

- **Path-structure coupling**: agent-produced YAML nesting differing from reference but semantically equivalent causes path resolution failures (already discovered and fixed, but highlights need for structural robustness).
- **Tolerance dependence on empirical judgment**: different computation types (surface area, link budget, safety factors) require different tolerances (5%-20%)—currently set manually.
- **Only 4 tasks with numeric assertions**: L-Numeric is currently enabled on site-stage4~7 only.

## 9.5 Cross-Entity Coupling Scale Requirements

TELECOM-TOPOLOGY-001 and TELECOM-SPECTRUM-001 are implemented in piki, but current canonical project scale is insufficient to trigger meaningful differentiation: dc-stage5's 2×2 Spine-Leaf poses no challenge; SPECTRUM-001 is not triggered because only one site exists. Scaling canonical projects (4+ Leaf, 3+ sites) is a prerequisite for activating these rules' differentiation potential.

## 9.6 Infeasibility of Human Baselines

SD-HWE-Bench does not include human engineer baselines. Reasons: (1) ADL/piki is our own DSL unfamiliar to human engineers—measuring "DSL learning speed" rather than "engineering capability"; (2) dedicated GUI development is prohibitively expensive and diverts from the research problem. Alternative strategy: use piki's 100% scoring as the "correct design" upper bound (solution oracle), supplemented by rich ablations (pass@1 vs. pass@5, repair, per-layer breakdown, per-rule error heatmaps).

## 9.7 Model Coverage and Experimental Scale

v3 experiments cover only DeepSeek-v4-Flash with pass@1. Minimum requirements before paper submission:

- **Multi-model pass@1**: GPT-4.1, Claude 4, Gemini 2.5, Kimi k2.7, DeepSeek-v4-Pro (+5 models)
- **Pass@5**: DeepSeek-v4-Flash 33 tasks × 5 passes
- **Repair ablation**: no-repair vs. max-repair=5
- **API Actor**: OpenAI/DeepSeek API path replication on v3 data

Data collection for these experiments is the current bottleneck, not paper writing.

## 9.8 Reproducibility

All v3 experiments run on macOS darwin arm64 with Docker-containerized DTS scoring (`sd-hwe-bench-piki:latest`). Containerized scoring guarantees cross-environment scoring reproducibility, but agent generation (Codex CLI) depends on locally installed Codex clients—version differences across environments may affect results. Long-term: migrating all experiments to unified containerized environments (agent generation + scoring both in containers).

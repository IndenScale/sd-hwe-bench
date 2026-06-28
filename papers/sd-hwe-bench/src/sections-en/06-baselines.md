# 6. Baseline Experiments

This chapter reports SD-HWE-Bench v3 main experimental results. Experiments cover 33 telecom tasks (11 merged stage + 5 POC + 5 compound easy + 4 emergent + 3 cross-disciplinary + 3 site deep + 1 dc Spine-Leaf + 1 site-stage4 RF), 1 CLI Actor (DeepSeek-v4-Flash via Codex CLI), under the pass@1 setting.

## 6.1 Experimental Setup

### 6.1.1 Model and Actor

| Actor | Model | CLI Framework | Notes |
|-------|-------|---------------|-------|
| Codex | DeepSeek-v4-Flash | Codex CLI (codex exec) | Filesystem operations, prompt guides active spec reading |

### 6.1.2 Evaluation Settings

- **Context**: Full Context (complete scaffold ADL project).
- **Passes**: 1 independent execution per task (pass@1).
- **DTS**: 32 rules (L1-L4 + L2a/L2b/L2c sub-layers + L3 cross-entity coupling), Docker container execution.
- **L-Numeric**: 4 deep tasks (site-stage4~7) include numeric_assertions.
- **Repair**: Not enabled in main experiment.

### 6.1.3 Metrics

pass@1, per-layer pass rate, Overall Score (weighted sum ≥ 75% = PASS).

## 6.2 Main Results

| Task Category | Count | pass@1 | Avg Overall Score | Primary Failure Mode |
|---------------|-------|--------|-------------------|---------------------|
| POC manual | 5 | 100% | 85% | — |
| Compound easy (dependency chains) | 5 | 100% | 85% | — |
| Merged stage | 11 | 100% | 85% | — |
| Emergent constraints | 4 | 100% | 85% | — |
| Cross-disciplinary | 3 | 67% | 78% | telecom-cross-001 DTS all pass but deliverable missing |
| RF engineering (site-stage4) | 1 | 100% | 85% | Formulae explicit in prompt, no computation deviation |
| Structural engineering (site-stage5) | 1 | 100% | 85% | Formula substitution—no challenge for LLM |
| Thermal management (site-stage6) | 1 | 100% | 82.5% | Surface area formula error (6.56 vs 4.64 m²) |
| EMC (site-stage7) | 1 | 100% | 82.7% | ΔRSSI direction misjudgment |
| Network topology (dc-stage5) | 1 | 100% | 85% | 2×2 Spine-Leaf full-mesh—no challenge for LLM |
| **Total** | **33** | **94% (31/33)** | **84.7% (avg)** | — |

Table: SD-HWE-Bench v3 main results (Full Context, pass@1, no-repair). {#tbl:main-results}

### 6.2.1 L-Numeric Layer Differentiation

| Task | L-Numeric Score | Failure Cause |
|------|----------------|---------------|
| site-stage4 (RF) | 100% (8/8) | Formulae and intermediate values given in requirement |
| site-stage5 (wind-load) | 100% (7/7) | Direct formula substitution, short computation chain |
| site-stage6 (thermal) | 75% (5/7) | Surface area formula error (6.56 vs 4.64) → cascading temp rise error |
| site-stage7 (interference) | 77% (6/6) | overall_risk misjudged as true (ΔRSSI direction error) |

**Key finding**: L-Numeric produces real differentiation in "open computation" scenarios (surface area requires self-derived formula, ΔRSSI requires physical sign interpretation), while ceiling effects recur in "closed computation" scenarios (substitute into given formula).

### 6.2.2 Cross-Entity Coupling Results

dc-stage5 Spine-Leaf task: TELECOM-TOPOLOGY-001 (full-mesh check) passed—the agent correctly produced 4 full-mesh connections for 2 Spine × 2 Leaf. The 2×2 scale is insufficient to expose LLM weaknesses in topology completeness; connection omission probability rises significantly at 4+ Leaf scale.

## 6.3 Difficulty Distribution and Differentiation

| Difficulty | Count | DS-Flash pass@1 | Differentiation Source |
|------------|-------|----------------|----------------------|
| easy | 7 | 100% | None—declarative tasks unchallenging for CLI Actor |
| medium | 13 | 100% | None—mating/layout/connection correctly executed |
| hard | 13 | 85% (11/13) | telecom-cross-001 (deliverable missing) + site-stage6/7 (numerical deviation lowers Overall Score) |

Table: pass@1 by difficulty. {#tbl:difficulty-breakdown}

## 6.4 Per-Layer Pass Rates

| Scoring Layer | Rules | Pass Rate | Typical Failure Rules |
|--------------|-------|-----------|----------------------|
| L0 Syntax | — | 100% | — |
| L1 Schema | 5 | 100% | — |
| L2a Identity/FK | 5 | 100% | — |
| L2b Interface/Port | 7 | 100% | — |
| L2c Mate/Catalog | 4 | 100% | — |
| L3 Engineering/Cross-Entity | 7 | 100% | — |
| L4 Geometric/Spatial | 5 | 100% | — |
| L-Numeric | task-defined | 88% (26/28 assertions) | site-stage6: surface area, temp rise; site-stage7: overall_risk |
| L5/L6 Deliverable | task-defined | 97% | telecom-cross-001: rack-face-panel-svg missing |

Table: Per-layer rule pass rates. {#tbl:layer-pass-rate}

## 6.5 Comparison with v2

| Metric | v2 (2026-06-27) | v3 (2026-06-28) | Change |
|--------|-----------------|-----------------|--------|
| Task count | 28 | 33 | +5 |
| Hard ratio | 25% (7/28) | 39% (13/33) | +14pp |
| Scoring layers | 6 (L0-L4+Deliverable) | 8 (+L-Numeric+Rubric) | +2 |
| piki rules | 30 | 32 | +2 cross-entity |
| Differentiation sources | Deliverable only | Deliverable + numerical + cross-entity | 3 dimensions |
| DS-Flash pass@1 | 92.9% | 94% | +1.1pp |
| DS-Flash Avg Score | 92.7% | 84.7% | -8pp (L-Numeric exposure) |

pass@1 rose slightly (92.9%→94%) because only telecom-cross-001 causes hard failure among new tasks; Avg Score dropped significantly (92.7%→84.7%) because L-Numeric exposes numerical deviations in site-stage6/7. **pass@1 and Avg Score provide complementary differentiation dimensions.**

## 6.6 Per-Task Detailed Results

The complete 33-task leaderboard is available in `leaderboard/results.md` and `leaderboard/results.json`.

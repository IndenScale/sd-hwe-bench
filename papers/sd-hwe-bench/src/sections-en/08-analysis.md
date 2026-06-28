# 8. Error Patterns and Difficulty Analysis

This chapter provides in-depth diagnostic analysis of agent results—not just reporting numbers, but analyzing *why* 31/33 tasks pass, where the bottlenecks lie, and what drives differentiation.

## 8.1 Overall Results: Ceiling and Breakthroughs

DeepSeek-v4-Flash achieves 94% pass@1 (31/33) with 100% DTS layer (L1-L4) pass rate. This continues v2's high-baseline characteristic, but v3 achieves the following breakthroughs via new deep tasks and the L-Numeric layer:

1. **pass@1 ceiling slightly softened from 92.9% to 94%**—only one of five new hard tasks causes hard failure.
2. **Avg Score dropped from 92.7% to 84.7%**—L-Numeric exposes numerical computation deviations on site-stage6 (82.5%) and site-stage7 (82.7%).
3. **Differentiation expanded from 1 to 3 dimensions**: v2 had only deliverable completeness; v3 adds numerical computation fidelity and cross-entity coupling integrity.

## 8.2 Numerical Computation Deviations: site-stage6 and site-stage7

### 8.2.1 site-stage6: Surface Area Error in Thermal Redundancy

Core computation chain:

```text
A_surface = 2 × (W×H + W×D + H×D) = 2 × (0.6×2.0 + 0.6×0.8 + 2.0×0.8) = 4.64 m²
ΔT = P_total / (h × A_surface) = 350 / (5 × 4.64) = 15.1°C
T_internal = 45 + 15.1 = 60.1°C > 50°C (thermal throttling risk)
```

The agent cited the correct formula but produced 6.56 m² instead of 4.64 m²—a parenthesis expansion error typical of LLM multi-step arithmetic. ΔT dropped from 15.1°C to 12.2°C (2.9°C low). L-Numeric's 5% tolerance vs. 41% deviation successfully amplified this error.

**Essence**: Not "the agent can't compute" but "intermediate arithmetic errors in multi-step formula evaluation"—analogous to LLMs' known weakness in exact arithmetic. Numerical assertion tolerance-based comparison surfaces this weakness.

### 8.2.2 site-stage7: ΔRSSI Direction Error in Interference Coordination

Core logic:

```text
d_overlap = d_coverage × cos(beamwidth/2) = 2.8 × cos(32.5°) = 2.36 km
RSSI_serving = EIRP - Lpath(d_overlap)
RSSI_interferer = EIRP - Lpath(d_coverage - d_overlap × cos(beamwidth/2))
ΔRSSI = RSSI_serving - RSSI_interferer ≈ 8.5 dB ≥ 6 dB → no risk
```

The agent correctly executed Okumura-Hata path loss computation but produced ΔRSSI = −16.2 dB (negative sign, inflated magnitude), leading to misclassified risk=true. Root cause: incorrect interferer distance definition (0.81 km vs. expected value), causing underestimation of interferer path loss and overestimation of interferer signal strength.

**Essence**: Physical modeling fidelity—the agent understood the formula framework but misapplied the geometric relationship "interferer distance = coverage radius − overlap zone projection component." L-Numeric's overall_risk assertion captured this misjudgment.

### 8.2.3 site-stage5: The "Formula Substitution" Effect

site-stage5's wind-load computation scored 100% L-Numeric because the requirement explicitly states F_wind = 0.5 × ρ × v² × Cd × A. The agent merely substituted numbers. **L-Numeric differentiation is inversely correlated with formula givenness**—when all required formulae appear in the prompt, LLMs execute perfectly.

## 8.3 Cross-Entity Coupling: dc-stage5's Scale Ceiling

dc-stage5 Spine-Leaf task: TELECOM-TOPOLOGY-001 (full-mesh integrity) passed—the agent produced the correct 4 full-mesh connections. 2×2 topology is trivial for LLMs because:

- 4 connections for full-mesh is the only valid topology (no design freedom)
- Total connection count is low; LLMs won't omit any

To produce differentiation: 4+ Leaf scale (8+ connections, LLM may omit one), or require repairing a deliberately broken topology. dc-stage5 currently provides mechanism verification for cross-entity coupling but no pass/fail differentiation.

## 8.4 telecom-cross-001: The Sole Hard Failure

telecom-cross-001 remains the only pass/fail failure point. All DTS layers pass; `rack-face-panel-svg` deliverable missing. Consistent with v2—not a design error but a piki engine limitation for non-rack facility SVG rendering.

**Implication**: Deliverable-based differentiation is saturated (the only failure is an engine edge case). Future experiments should focus on L-Numeric and cross-entity coupling as new differentiation dimensions.

## 8.5 Differentiation Improvement Pathways

Based on v3 results, SD-HWE-Bench's differentiation comes from three non-overlapping dimensions:

| Dimension | Representative Task | Failure Pattern | LLM Capability Gap |
|-----------|-------------------|-----------------|-------------------|
| Deliverable completeness | telecom-cross-001 | SVG rendering path unsupported | Toolchain understanding + deliverable checking |
| Numerical computation fidelity | site-stage6, site-stage7 | Surface area formula error, ΔRSSI direction | Multi-step arithmetic + physical modeling |
| Cross-entity coupling integrity | dc-stage5 (not triggered) | Full-mesh omission (needs larger scale) | Global consistency (2×2 insufficient) |

Future directions:

1. **More open-computation tasks**: reduce formula givenness in task requirements; require self-derived formulas.
2. **Larger topology scale**: Spine-Leaf from 2×2 to 4+×2.
3. **Fault injection tasks**: pre-embed errors in scaffold; require agent to discover and fix—testing "repair" not just "create."

"""Decision critic for conceptual-design multi-scheme selection tasks (ADR 0006).

A conceptual-design task hands the Actor a *scenario* (climate, tariffs, water /
carbon quotas, supplier maturity, plus explicit ``criteria_weights``) and a fixed
small design space of candidate schemes.  The Actor must submit:

- ``comparison.yaml`` — a comparison matrix (scheme × criterion) of metric values.
- ``recommendation.yaml`` — the recommended scheme id + rationale.

The bench carries the answer key as ``l7_config.scheme_library``: a per-scheme
deterministic criteria table plus feasibility flags.  ``DecisionCritic`` scores
three tiers (the MVP of ADR 0006; the diagnostic LLM-judge rationale tier is left
for a later phase):

1. **Feasibility gate** — the recommended scheme must exist in the design space
   and be marked feasible.
2. **Matrix correctness** — every (feasible scheme, weighted criterion) value the
   Actor reports must match the bench's deterministic criteria within tolerance,
   so the recommendation cannot rest on a fabricated matrix.
3. **Decision quality** — the bench ranks feasible schemes by a deterministic
   weighted-sum over min-max normalized criteria; the recommendation must be
   Pareto-optimal (hard) and earns rank-distance partial credit (diagnostic).

``passed`` requires tiers 1-3 hard conditions; ``score`` is the diagnostic
decision quality (rank-distance) in ``[0, 1]``.  Everything is a pure function of
the scenario, the library, and the Actor files — no randomness, no model calls —
so repeated scoring of the same inputs is bit-for-bit identical (ADR 0006 MVP
reproducibility gate).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sd_hwe_bench.critics.base import Critic, CriticResult

# Default optimization direction per criterion. "min" = lower is better,
# "max" = higher is better. Tasks may override via
# ``scheme_library.criteria_directions``.
DEFAULT_DIRECTIONS: dict[str, str] = {
    "pue": "min",
    "capex_cny": "min",
    "water_m3_per_year": "min",
    "carbon_t_per_year": "min",
    "flexibility": "max",
    "supplier_risk": "min",
}


def _within_tol(reported: Any, truth: Any, tol: float) -> bool:
    """Relative tolerance check with an absolute fallback when truth is ~0."""
    try:
        a = float(reported)
        b = float(truth)
    except (TypeError, ValueError):
        return False
    if b == 0:
        return abs(a) <= tol
    return abs(a - b) <= tol * abs(b)


def normalize_criterion(
    values: dict[str, float], direction: str
) -> dict[str, float]:
    """Min-max normalize one criterion across schemes so 1.0 = best.

    When all schemes share a value (no discrimination), every scheme scores 1.0.
    """
    nums = list(values.values())
    lo, hi = min(nums), max(nums)
    spread = hi - lo
    out: dict[str, float] = {}
    for sid, v in values.items():
        if spread == 0:
            out[sid] = 1.0
        elif direction == "max":
            out[sid] = (v - lo) / spread
        else:  # min is better
            out[sid] = (hi - v) / spread
    return out


def weighted_scores(
    criteria: dict[str, dict[str, float]],
    weights: dict[str, float],
    directions: dict[str, str],
) -> dict[str, float]:
    """Weighted-sum MCDA score per scheme over normalized criteria (higher=better)."""
    crit_names = [c for c in weights if any(c in row for row in criteria.values())]
    normalized: dict[str, dict[str, float]] = {}
    for c in crit_names:
        col = {sid: float(row[c]) for sid, row in criteria.items() if c in row}
        direction = directions.get(c, "min")
        normalized[c] = normalize_criterion(col, direction)

    scores: dict[str, float] = {}
    for sid in criteria:
        total = 0.0
        for c in crit_names:
            total += float(weights[c]) * normalized[c].get(sid, 0.0)
        scores[sid] = total
    return scores


def rank_of(scores: dict[str, float], scheme_id: str) -> int:
    """1-based rank of a scheme (ties share the better rank)."""
    if scheme_id not in scores:
        return len(scores) + 1
    target = scores[scheme_id]
    return 1 + sum(1 for s in scores.values() if s > target + 1e-12)


def pareto_front(
    criteria: dict[str, dict[str, float]],
    weights: dict[str, float],
    directions: dict[str, str],
) -> set[str]:
    """Return the set of non-dominated schemes over the weighted criteria.

    Scheme A dominates B if A is at-least-as-good on every criterion and strictly
    better on at least one, where "good" follows each criterion's direction.
    """
    crit_names = [c for c in weights if any(c in row for row in criteria.values())]

    def better(c: str, x: float, y: float) -> bool:
        return x > y if directions.get(c, "min") == "max" else x < y

    def at_least(c: str, x: float, y: float) -> bool:
        return x >= y if directions.get(c, "min") == "max" else x <= y

    ids = list(criteria)
    dominated: set[str] = set()
    for b in ids:
        for a in ids:
            if a == b:
                continue
            shared = [c for c in crit_names if c in criteria[a] and c in criteria[b]]
            if not shared:
                continue
            if all(at_least(c, criteria[a][c], criteria[b][c]) for c in shared) and any(
                better(c, criteria[a][c], criteria[b][c]) for c in shared
            ):
                dominated.add(b)
                break
    return set(ids) - dominated


class DecisionCritic(Critic):
    """Evaluate a conceptual-design multi-scheme comparison and recommendation."""

    name = "Decision"

    def __init__(self, tolerance: float | None = None):
        self.tolerance_override = tolerance

    def evaluate(self, workspace_root: Path, task: Any) -> CriticResult:
        comments: list[str] = []
        meta = getattr(task, "metadata", None)
        scenario = dict(getattr(meta, "scenario", {}) or {})
        l7_config = getattr(meta, "l7_config", {}) if meta is not None else {}
        library = (l7_config or {}).get("scheme_library") or {}
        schemes_lib: dict[str, dict] = library.get("schemes") or {}

        if not schemes_lib:
            return CriticResult(
                name=self.name,
                passed=False,
                score=0.0,
                comments=["scheme_library.schemes missing or empty in task l7_config"],
            )

        weights: dict[str, float] = scenario.get("criteria_weights") or {}
        if not weights:
            return CriticResult(
                name=self.name,
                passed=False,
                score=0.0,
                comments=["scenario.criteria_weights missing"],
            )

        directions = {**DEFAULT_DIRECTIONS, **(library.get("criteria_directions") or {})}
        tolerance = (
            self.tolerance_override
            if self.tolerance_override is not None
            else float(library.get("tolerance", 0.05))
        )

        # Load Actor submission.
        comparison = self._load_yaml(workspace_root / "comparison.yaml", comments)
        recommendation = self._load_yaml(workspace_root / "recommendation.yaml", comments)
        if comparison is None or recommendation is None:
            return CriticResult(name=self.name, passed=False, score=0.0, comments=comments)

        feasible_ids = [
            sid for sid, s in schemes_lib.items() if s.get("feasible", True)
        ]
        truth: dict[str, dict[str, float]] = {
            sid: dict(schemes_lib[sid].get("criteria", {})) for sid in feasible_ids
        }
        rec_id = recommendation.get("recommended")

        # ── Tier 1: feasibility gate ──────────────────────────────────────
        tier1_msgs: list[str] = []
        if not rec_id:
            tier1_msgs.append("recommendation.yaml missing 'recommended' scheme id")
        elif rec_id not in schemes_lib:
            tier1_msgs.append(
                f"recommended scheme '{rec_id}' is not part of the design space"
            )
        elif not schemes_lib[rec_id].get("feasible", True):
            tier1_msgs.append(
                f"recommended scheme '{rec_id}' is infeasible and cannot be recommended"
            )

        # ── Tier 2: comparison-matrix correctness ─────────────────────────
        agent_rows: dict[str, dict] = comparison.get("schemes") or {}
        tier2_msgs: list[str] = []
        for sid in feasible_ids:
            if sid not in agent_rows:
                tier2_msgs.append(f"comparison.yaml missing feasible scheme '{sid}'")
                continue
            row = agent_rows[sid] or {}
            for crit in weights:
                if crit not in truth[sid]:
                    continue
                if crit not in row:
                    tier2_msgs.append(f"comparison '{sid}': missing criterion '{crit}'")
                    continue
                if not _within_tol(row[crit], truth[sid][crit], tolerance):
                    tier2_msgs.append(
                        f"comparison '{sid}.{crit}'={row[crit]} differs from bench "
                        f"value {truth[sid][crit]} (tolerance {tolerance:.0%})"
                    )

        # ── Tier 3: decision quality ──────────────────────────────────────
        scores = weighted_scores(truth, weights, directions)
        pareto = pareto_front(truth, weights, directions)
        n_feasible = len(feasible_ids)
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))

        if rec_id in truth:
            rank = rank_of(scores, rec_id)
            decision_score = max(0.0, 1.0 - (rank - 1) / n_feasible) if n_feasible else 0.0
            tier3_hard_ok = rec_id in pareto
            tier3_msgs: list[str] = []
            if not tier3_hard_ok:
                tier3_msgs.append(
                    f"recommended scheme '{rec_id}' is Pareto-dominated (not on the frontier)"
                )
        else:
            rank = None
            decision_score = 0.0
            tier3_hard_ok = False
            tier3_msgs = []  # tier 1 already reported the missing/infeasible recommendation

        passed = not tier1_msgs and not tier2_msgs and tier3_hard_ok
        score = decision_score

        comments.extend(tier1_msgs)
        comments.extend(tier2_msgs)
        comments.extend(tier3_msgs)
        best_id = ranked[0][0] if ranked else None
        comments.append(
            f"Decision: recommended '{rec_id}' rank {rank}/{n_feasible} "
            f"(bench optimum '{best_id}'), score {decision_score:.3f}, "
            f"Pareto-optimal={rec_id in pareto}"
        )

        artifacts = {
            "recommended": rec_id,
            "rank_of_recommended": rank,
            "n_feasible": n_feasible,
            "decision_score": decision_score,
            "weighted_ranking": ranked,
            "pareto_front": sorted(pareto),
            "tolerance": tolerance,
        }
        return CriticResult(
            name=self.name,
            passed=passed,
            score=score,
            comments=comments,
            artifacts=artifacts,
        )

    def _load_yaml(self, path: Path, comments: list[str]) -> dict[str, Any] | None:
        if not path.exists():
            comments.append(f"Missing required deliverable: {path.name}")
            return None
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            comments.append(f"{path.name}: YAML parse error - {exc}")
            return None
        except OSError as exc:
            comments.append(f"{path.name}: read error - {exc}")
            return None
        if not isinstance(data, dict):
            comments.append(f"{path.name}: expected a mapping at the document root")
            return None
        return data

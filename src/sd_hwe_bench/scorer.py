"""Scoring framework — computes Pass@k from piki check results.

Integrates deterministic rule checking (L0-L4) with optional
LLM-as-Judge rubrics evaluation powered by DeepEval GEval.

Piki integration: when real piki is available (piki >= 0.1.0), scorer uses
`piki check --format json` for structured output. Otherwise falls back to
static YAML checks (L0-L2) only.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from sd_hwe_bench.llm_judge import (
    LLMJudgeResult,
    collect_agent_output,
    evaluate_rubric_set,
)
from sd_hwe_bench.task import RubricSet

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class LayerScore:
    """Score for one check layer."""

    layer: str
    total: int
    passed: int
    failed: int
    errors: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class TaskScore:
    """Complete score for one task attempt."""

    task_id: str
    success: bool
    layers: dict[str, LayerScore] = dataclasses.field(default_factory=dict)
    deliverable_scores: dict[str, bool] = dataclasses.field(default_factory=dict)
    overall_score: float = 0.0
    rubric_results: list[LLMJudgeResult] = dataclasses.field(default_factory=list)
    rubric_score: float | None = None


# Layer weights aligned with initiative doc
LAYER_WEIGHTS = {
    "L0": 0.0,   # Gate: must pass, but no points
    "L1": 0.10,
    "L2": 0.15,
    "L3": 0.40,
    "L4": 0.20,
    "L5": 0.0,
    "L6": 0.0,
}

# ── Piki rule → layer mapping ───────────────────────────────────────────
# When piki --format json is available, rule failures are mapped to layers.
# Rules not explicitly listed default to L2 (reference/integrity).
PIKI_RULE_LAYERS: dict[str, str] = {
    # L1: Schema / validation
    "SCHEMA-001": "L1",
    # L3: Business / threshold / lifecycle rules
    "TELECOM-POWER-001": "L3",      # PDU power budget
    "TELECOM-POWER-002": "L3",      # PDU phase balance
    "CATALOG-LIFECYCLE-001": "L3",  # EOL lifecycle check
    # L4: Geometry / collision / spatial
    "TELECOM-RACK-001": "L4",       # U collision
    "TELECOM-RACK-002": "L4",       # Rack capacity
    "TELECOM-RACK-003": "L4",       # Physical fit
    "TELECOM-COLLISION-001": "L4",  # 3D collision
    # L2 (explicitly listed for clarity; all others default to L2):
    "REFS-001": "L2",
    "REFS-002": "L2",
    "FK-001": "L2",
    "TAGS-001": "L2",
    "INTERFACE-COMPAT-001": "L2",
    "INTERFACE-CABLE-001": "L2",
    "MATE-001": "L2",
    "MATE-002": "L2",
    "MATE-003": "L2",
    "CATALOG-001": "L2",
    "CATALOG-002": "L2",
    "TELECOM-FK-001": "L2",
    "TELECOM-PORT-001": "L2",
    "TELECOM-PORT-002": "L2",
    "TELECOM-CONN-001": "L2",
    "TELECOM-CONN-002": "L2",
    "TELECOM-CONN-003": "L2",
}

# ── Piki CLI ──────────────────────────────────────────────────────────────
_PIKI_PYTHON = "/Users/indenscale/workspace/piki/.venv/bin/python"
_PIKI_MODULE = "piki"


def run_piki_check(project_dir: Path, json_output: bool = True) -> dict[str, Any]:
    """Run `piki check` CLI on a project directory.

    When json_output=True, calls `piki check --format json` and returns
    the parsed JSON report plus availability metadata.
    """
    args = ["piki", "check"]
    if json_output:
        args.extend(["--format", "json"])

    try:
        result = subprocess.run(
            args,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if json_output:
            try:
                parsed = json.loads(result.stdout)
            except json.JSONDecodeError:
                parsed = {}
            return {
                "available": True,
                "success": result.returncode == 0,
                "parsed": parsed,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        return {
            "available": True,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "success": False,
            "stdout": "",
            "stderr": "piki check timed out",
        }
    except FileNotFoundError:
        return {
            "available": False,
            "success": False,
            "stdout": "",
            "stderr": "piki not installed",
        }


def run_piki_check_via_python(
    project_dir: Path,
    json_output: bool = True,
    piki_python: str | None = None,
) -> dict[str, Any]:
    """Run piki check using an explicit Python interpreter + module path.

    Preferred when piki is installed as a local editable package
    (e.g. `pip install -e /path/to/piki`) rather than a global CLI.
    """
    args = [
        piki_python or _PIKI_PYTHON,
        "-m",
        _PIKI_MODULE,
        "check",
    ]
    if json_output:
        args.extend(["--format", "json"])

    try:
        result = subprocess.run(
            args,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if json_output:
            try:
                parsed = json.loads(result.stdout)
            except json.JSONDecodeError:
                parsed = {}
            return {
                "available": True,
                "success": result.returncode == 0,
                "parsed": parsed,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        return {
            "available": True,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "success": False,
            "stdout": "",
            "stderr": "piki check timed out",
        }
    except FileNotFoundError:
        return {
            "available": False,
            "success": False,
            "stdout": "",
            "stderr": "piki not installed",
        }


# ── Static YAML checks (fallback when piki is unavailable) ──────────────

def _static_check_yaml(project_dir: Path) -> dict[str, Any]:
    """Run static YAML checks (L0-L2) — fallback when piki is unavailable."""
    import yaml as _yaml

    errors: dict[str, list[str]] = {"L0": [], "L1": [], "L2": []}
    yaml_files = sorted(project_dir.rglob("*.yaml")) + sorted(project_dir.rglob("*.yml"))

    if not yaml_files:
        errors["L0"].append("No YAML files found in project directory")
        return {"errors": errors}

    declared_ids: set[str] = set()
    referenced_ids: set[str] = set()
    model_files: set[str] = set()

    for fpath in yaml_files:
        rel = str(fpath.relative_to(project_dir))
        try:
            raw = fpath.read_text()
            doc = _yaml.safe_load(raw)
        except _yaml.YAMLError as e:
            errors["L0"].append(f"{fpath.name}: YAML parse error: {e}")
            continue
        except Exception as e:
            errors["L0"].append(f"{fpath.name}: {e}")
            continue

        if doc is None:
            continue
        if not isinstance(doc, (dict, list)):
            continue

        # Detect model definition files
        is_model_file = (
            isinstance(doc, dict)
            and "id" not in doc
            and ("model" in doc or "family" in doc)
            and ("models" in rel or rel.startswith("models/"))
        )
        if is_model_file:
            model_files.add(rel)
            continue

        items = doc if isinstance(doc, list) else [doc]
        for item in items:
            if not isinstance(item, dict):
                continue

            _check_schema(item, fpath.name, errors["L1"])

            if "id" in item and isinstance(item["id"], str):
                declared_ids.add(item["id"])

            _collect_references(item, referenced_ids)

    undefined = referenced_ids - declared_ids
    for uid in sorted(undefined):
        errors["L2"].append(f"FK-UNDEFINED: '{uid}' is referenced but never declared")

    result: dict[str, Any] = {
        "errors": errors,
        "declared_count": len(declared_ids),
        "referenced_count": len(referenced_ids),
        "undefined_count": len(undefined),
        "model_files": list(model_files),
    }
    if declared_ids:
        result["declared_ids"] = sorted(declared_ids)
    if undefined:
        result["undefined_ids"] = sorted(undefined)
    return result


def _check_schema(item: dict, filename: str, errors: list[str]) -> None:
    """Check item-level schema requirements (L1)."""
    item_type = None
    if "id" not in item:
        errors.append(f"{filename}: missing 'id' field")
        return

    if "kind" in item:
        item_type = item["kind"]
    elif "family" in item:
        item_type = item["family"]
    elif "model" in item:
        item_type = item["model"]

    if item_type is None:
        return

    schema_checks = {
        "ServerFamily": ["tdp_w", "height_u", "psu_count"],
        "SwitchFamily": ["tdp_w", "height_u", "psu_count"],
        "RackFamily": ["total_u", "depth_mm", "width_mm"],
        "PDUFamily": ["max_power_watts"],
        "FiberFamily": ["from_port", "to_port"],
    }

    required = schema_checks.get(str(item_type), [])
    for field in required:
        if field not in item:
            errors.append(f"{filename}: {item_type} missing required field '{field}'")


def _collect_references(item: dict, refs: set) -> None:
    """Walk item dict and collect all referenced IDs."""
    for field in ("instance", "device_id", "rack_id", "pdu_id"):
        if field in item and isinstance(item[field], str):
            refs.add(item[field])

    for field in ("source", "target"):
        if field in item:
            val = item[field]
            if isinstance(val, str):
                refs.add(val)
            elif isinstance(val, dict) and "instance" in val:
                refs.add(val["instance"])

    for field in ("from_port", "to_port"):
        if field in item and isinstance(item[field], str):
            port_ref = item[field]
            if "/" in port_ref:
                dev_id = port_ref.split("/")[0]
                refs.add(dev_id)


# ── Layer scoring from piki JSON ────────────────────────────────────────

def _layer_scores_from_static(score: TaskScore, static_result: dict[str, Any]) -> None:
    """Populate layer scores from static YAML check results."""
    errors = static_result.get("errors", {})
    for layer in LAYER_WEIGHTS:
        layer_errors = errors.get(layer, [])
        total = 1
        passed = 0 if layer_errors else 1
        score.layers[layer] = LayerScore(
            layer=layer,
            total=total,
            passed=passed,
            failed=total - passed,
            errors=list(layer_errors),
        )
        if passed and layer in LAYER_WEIGHTS:
            score.overall_score += LAYER_WEIGHTS[layer]


def _layer_scores_from_piki_json(
    score: TaskScore, parsed: dict[str, Any]
) -> None:
    """Populate layer scores from parsed piki `--format json` output.

    Maps piki rule failures to L1-L4 layers using PIKI_RULE_LAYERS.
    A layer passes when ALL rules mapped to that layer pass.
    """
    layer_errors: dict[str, list[str]] = {
        "L1": [], "L2": [], "L3": [], "L4": [],
    }

    # Collect failed rules from piki results
    for result in parsed.get("results", []):
        if result.get("passed"):
            continue
        rule_id = result.get("rule_id", "")
        layer = PIKI_RULE_LAYERS.get(rule_id, "L2")
        if layer in layer_errors:
            layer_errors[layer].append(
                f"{rule_id}: {result.get('message', 'failed')}"
            )

    # Collect diagnostics with severity >= ERROR
    for diag in parsed.get("diagnostics", []):
        severity = str(diag.get("severity", "")).upper()
        if severity not in ("ERROR", "FATAL"):
            continue
        code = diag.get("code", "")
        layer = PIKI_RULE_LAYERS.get(code, "L2")
        if layer in layer_errors:
            loc = diag.get("location", {})
            uri = loc.get("uri", "") if isinstance(loc, dict) else ""
            layer_errors[layer].append(
                f"{code}: {diag.get('message', 'failed')}"
                + (f" @ {uri}" if uri else "")
            )

    # Build layer scores
    for layer in ("L1", "L2", "L3", "L4"):
        errors = layer_errors[layer]
        total = 1
        passed = 0 if errors else 1
        score.layers[layer] = LayerScore(
            layer=layer,
            total=total,
            passed=passed,
            failed=total - passed,
            errors=errors,
        )
        if passed:
            score.overall_score += LAYER_WEIGHTS[layer]

    # L0: gate — fail if piki ran 0 real checks (empty project)
    results_count = len(parsed.get("results", []))
    l0_passed = 1
    l0_errors: list[str] = []
    if results_count == 0:
        l0_passed = 0
        l0_errors.append("Piki returned no results — project not found")
    score.layers["L0"] = LayerScore(
        layer="L0", total=1, passed=l0_passed, failed=1 - l0_passed, errors=l0_errors
    )
    # L5, L6: not scored
    score.layers["L5"] = LayerScore(layer="L5", total=0, passed=0, failed=0)
    score.layers["L6"] = LayerScore(layer="L6", total=0, passed=0, failed=0)


def _layer_scores_from_piki_stderr(
    score: TaskScore, check_result: dict[str, Any]
) -> None:
    """Parse piki stderr output (legacy fallback for older piki versions)."""
    stderr = check_result.get("stderr", "")

    has_schema_error = (
        "validation error" in stderr.lower()
        or "schema" in stderr.lower()
        or "YAML" in stderr
    )
    has_ref_error = "FK-" in stderr or "not found" in stderr.lower()
    has_business_error = "threshold" in stderr.lower() or "violat" in stderr.lower()
    has_geometry_error = "collision" in stderr.lower() or "overlap" in stderr.lower()

    for layer in LAYER_WEIGHTS:
        total = 1
        if layer == "L0":
            passed = 1
        elif layer == "L1":
            passed = 0 if has_schema_error else 1
        elif layer == "L2":
            passed = 0 if has_ref_error else 1
        elif layer == "L3":
            passed = 0 if has_business_error else 1
        elif layer == "L4":
            passed = 0 if has_geometry_error else 1
        elif layer in ("L5", "L6"):
            passed = 1
        else:
            passed = 1

        score.layers[layer] = LayerScore(
            layer=layer, total=total, passed=passed, failed=total - passed
        )
        if passed:
            score.overall_score += LAYER_WEIGHTS[layer]



def _init_default_layers(score: TaskScore) -> None:
    """Initialize all layers to pass (used as fallback when gates fail)."""
    for layer in ("L1", "L2", "L3", "L4"):
        score.layers[layer] = LayerScore(layer=layer, total=1, passed=1, failed=0, errors=[])
    score.layers["L5"] = LayerScore(layer="L5", total=0, passed=0, failed=0)
    score.layers["L6"] = LayerScore(layer="L6", total=0, passed=0, failed=0)


def _piki_check_and_score(score: TaskScore, project_dir: Path) -> bool:
    """Run piki check and score — tries JSON, falls back to stderr, then static.

    Returns True if piki was available and used successfully.
    """
    # Quick L0 gate: are there any YAML files outside models/?
    yaml_files = (
        list(project_dir.rglob("*.yaml")) + list(project_dir.rglob("*.yml"))
    )
    instance_files = [
        f for f in yaml_files
        if "models/" not in str(f.relative_to(project_dir))
        and f.name != "piki.toml"
    ]
    if not instance_files:
        # No instance YAML — project is empty. L0 fails.
        score.layers["L0"] = LayerScore(
            layer="L0", total=1, passed=0, failed=1,
            errors=["No YAML instance files found (empty project)"],
        )
        _init_default_layers(score)
        return True

    # Try piki module (local editable install) first
    piki_result = run_piki_check_via_python(project_dir, json_output=True)
    if piki_result.get("available"):
        parsed = piki_result.get("parsed", {})
        if parsed and parsed.get("results") is not None:
            _layer_scores_from_piki_json(score, parsed)
            return True
        if parsed:
            return False

    # Try piki CLI (system PATH)
    piki_result = run_piki_check(project_dir, json_output=True)
    if piki_result.get("available"):
        parsed = piki_result.get("parsed", {})
        if parsed and parsed.get("results") is not None:
            _layer_scores_from_piki_json(score, parsed)
            return True
        if parsed:
            return False

    return False


# ── Rubric scoring ──────────────────────────────────────────────────────

def _score_rubrics(
    score: TaskScore,
    rubric_sets: list[RubricSet],
    requirement: str,
    project_dir: Path,
    model: str | None = None,
) -> None:
    """Run LLM-as-Judge rubric evaluation and attach results to the TaskScore."""
    if not rubric_sets:
        return

    from sd_hwe_bench.llm_judge import _DEFAULT_MODEL

    judge_model = model or _DEFAULT_MODEL
    output_text = collect_agent_output(project_dir)

    results: list[LLMJudgeResult] = []
    for rubric_set in rubric_sets:
        try:
            result = evaluate_rubric_set(
                rubric_set, requirement, output_text, model=judge_model
            )
            results.append(result)
        except Exception as e:
            logger.exception("Rubric set %s failed", rubric_set.name)
            results.append(
                LLMJudgeResult(
                    rubric_name=rubric_set.name,
                    overall_score=0.0,
                    passed=False,
                    threshold=rubric_set.threshold,
                    criteria_scores=[],
                    raw_errors=[str(e)],
                )
            )

    score.rubric_results = results

    if results:
        score.rubric_score = sum(r.overall_score for r in results) / len(results)


# ── Main entry point ────────────────────────────────────────────────────

def score_task(
    task_id: str,
    agent_output_dir: Path,
    expected_deliverables: list[str] | None = None,
    rubric_sets: list[RubricSet] | None = None,
    requirement: str = "",
    rubrics_model: str | None = None,
) -> TaskScore:
    """Score a single task attempt."""
    score = TaskScore(task_id=task_id, success=False)

    # Phase 1: piki engine checks (L0-L4) — preferred path
    piki_used = _piki_check_and_score(score, agent_output_dir)

    # Phase 2: fallback to static YAML checks if piki unavailable
    if not piki_used:
        static_result = _static_check_yaml(agent_output_dir)
        _layer_scores_from_static(score, static_result)

    # Phase 3: Deliverable checks
    if expected_deliverables:
        for d in expected_deliverables:
            score.deliverable_scores[d] = _check_deliverable(agent_output_dir, d)

    # Determine success: all L0-L4 checks passed
    critical_layers = ["L0", "L1", "L2", "L3", "L4"]
    score.success = all(
        score.layers.get(l) and score.layers[l].passed
        for l in critical_layers
    )

    # Phase 4: LLM-as-Judge rubrics (optional)
    if rubric_sets:
        _score_rubrics(score, rubric_sets, requirement, agent_output_dir, model=rubrics_model)

    return score


# ── Deliverable checks ──────────────────────────────────────────────────

def _check_deliverable(project_dir: Path, deliverable_name: str) -> bool:
    """Check if a generator deliverable was produced successfully."""
    dist_root = _read_dist_root(project_dir)

    deliverable_paths = {
        "bom-csv": ("bom-csv", "bom.csv", "采购清单"),
        "rack-face-panel-svg": ("rack-face-panel-svg", "rack-panel.svg", "施工图"),
        "power-budget": ("power-budget", "power-budget.csv", "设计评审"),
        "cable-list": ("cable-list", "cable-list.csv", "采购清单"),
        "port-map": ("port-map", "port-map.csv", "设计评审"),
    }

    info = deliverable_paths.get(deliverable_name)
    if not info:
        return False

    config_key, filename, category = info

    toml_config = _read_piki_toml_dist(project_dir)
    if config_key in toml_config:
        cat = toml_config[config_key]
    else:
        cat = category

    target = dist_root / cat / filename
    if target.exists():
        return True

    if dist_root.exists():
        for f in dist_root.rglob(filename):
            return True

    return False


def _read_dist_root(project_dir: Path) -> Path:
    """Read dist root from piki.toml or return default 'dist'."""
    piki_toml = project_dir / "piki.toml"
    if piki_toml.exists():
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        try:
            data = tomllib.loads(piki_toml.read_text())
            return project_dir / data.get("generators", {}).get("dist", {}).get("root", "dist")
        except Exception:
            pass
    return project_dir / "dist"


def _read_piki_toml_dist(project_dir: Path) -> dict[str, str]:
    """Read generator dist targets from piki.toml."""
    piki_toml = project_dir / "piki.toml"
    if not piki_toml.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]
    try:
        data = tomllib.loads(piki_toml.read_text())
        return data.get("generators", {}).get("dist", {}).get("targets", {})
    except Exception:
        return {}


# ── Aggregate metrics ───────────────────────────────────────────────────

def compute_pass_at_k(scores: list[list[TaskScore]], k: int) -> float:
    """Compute Pass@k from per-attempt scores."""
    total = len(scores)
    if total == 0:
        return 0.0

    passed = 0
    for task_scores in scores:
        best_k = task_scores[:k]
        if any(s.success for s in best_k):
            passed += 1

    return passed / total


def compute_partial_credit(scores: list[TaskScore]) -> list[dict]:
    """Compute per-layer pass rates across all task attempts."""
    layer_stats: dict[str, dict] = {}
    for layer in LAYER_WEIGHTS:
        layer_stats[layer] = {"total": 0, "passed": 0}

    for score in scores:
        for layer, ls in score.layers.items():
            if layer not in layer_stats:
                continue
            layer_stats[layer]["total"] += ls.total
            layer_stats[layer]["passed"] += ls.passed

    return [
        {
            "layer": layer,
            "weight": LAYER_WEIGHTS[layer],
            "pass_rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0,
            "passed": stats["passed"],
            "total": stats["total"],
        }
        for layer, stats in layer_stats.items()
    ]

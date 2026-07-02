"""Diagnostic normalization and rendering for repair experiments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sd_hwe_bench.constraints.catalog import ConstraintCatalog, ConstraintSpec


@dataclass(frozen=True)
class Diagnostic:
    """A normalized critic failure."""

    constraint_id: str
    family: str
    layer: str
    message: str
    critic: str = ""
    object_id: str = ""
    file: str = ""
    field: str = ""
    expected: str = ""
    actual: str = ""
    repair_hint: str = ""
    localization: str = "task-level"

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "family": self.family,
            "layer": self.layer,
            "message": self.message,
            "critic": self.critic,
            "object_id": self.object_id,
            "file": self.file,
            "field": self.field,
            "expected": self.expected,
            "actual": self.actual,
            "repair_hint": self.repair_hint,
            "localization": self.localization,
        }


def collect_score_diagnostics(score: Any, catalog: ConstraintCatalog) -> list[Diagnostic]:
    """Normalize failures from a TaskScore into diagnostics."""

    diagnostics: list[Diagnostic] = []

    for critic_result in getattr(score, "critic_results", []):
        name = getattr(critic_result, "name", "")
        artifacts = getattr(critic_result, "artifacts", {}) or {}
        if name == "piki" and artifacts.get("parsed"):
            diagnostics.extend(_from_piki_parsed(artifacts["parsed"], catalog))
            continue
        if name == "deliverable" and not getattr(critic_result, "passed", True):
            diagnostics.extend(_from_comments(name, "Deliverable", getattr(critic_result, "comments", []), catalog))
            continue
        if not getattr(critic_result, "passed", True):
            diagnostics.extend(_from_comments(name, _layer_for_critic_result(name), getattr(critic_result, "comments", []), catalog))

    for layer, layer_score in getattr(score, "layers", {}).items():
        for err in getattr(layer_score, "errors", []) or []:
            if _is_failure_comment(str(err)):
                diagnostics.append(_diagnostic_from_message(str(err), layer, "layer", catalog))

    by_constraint: dict[str, Diagnostic] = {}
    for diag in diagnostics:
        current = by_constraint.get(diag.constraint_id)
        if current is None or _localization_rank(diag.localization) > _localization_rank(current.localization):
            by_constraint[diag.constraint_id] = diag
    return list(by_constraint.values())


def render_diagnostics(
    diagnostics: list[Diagnostic],
    verbosity: str = "localized",
    max_items: int | None = None,
) -> list[dict[str, str]]:
    """Render diagnostics for a repair prompt.

    The underlying diagnostic set stays identical; only the exposed fields vary.
    """

    if verbosity not in {"none", "coarse", "attributed", "localized"}:
        raise ValueError("diagnostic verbosity must be one of: none, coarse, attributed, localized")
    if verbosity == "none":
        return []

    rendered: list[dict[str, str]] = []
    for diag in diagnostics[:max_items]:
        if verbosity == "coarse":
            rendered.append(
                {
                    "rule_id": diag.constraint_id,
                    "name": diag.family,
                    "message": _coarse_message(diag),
                }
            )
        elif verbosity == "attributed":
            rendered.append(
                {
                    "rule_id": diag.constraint_id,
                    "name": diag.family,
                    "message": diag.message,
                    "object_id": diag.object_id,
                    "layer": diag.layer,
                }
            )
        else:
            item = diag.to_dict()
            item["rule_id"] = diag.constraint_id
            item["name"] = diag.family
            rendered.append({k: str(v) for k, v in item.items() if v not in ("", None)})
    return rendered


def summarize_diagnostics(
    diagnostics: list[Diagnostic],
    catalog: ConstraintCatalog,
    muted_constraint_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Return manifest-friendly diagnostic metrics."""

    muted_constraint_ids = muted_constraint_ids or set()
    failed_ids = {d.constraint_id for d in diagnostics}
    executable_total = sum(1 for spec in catalog.constraints if spec.executable)
    visible_executable_total = sum(
        1 for spec in catalog.constraints if spec.executable and spec.id not in muted_constraint_ids
    )
    hidden_failed = failed_ids & muted_constraint_ids

    by_family: dict[str, int] = {}
    by_layer: dict[str, int] = {}
    by_localization: dict[str, int] = {}
    for diag in diagnostics:
        by_family[diag.family] = by_family.get(diag.family, 0) + 1
        by_layer[diag.layer] = by_layer.get(diag.layer, 0) + 1
        by_localization[diag.localization] = by_localization.get(diag.localization, 0) + 1

    return {
        "count": len(diagnostics),
        "unique_constraints_failed": len(failed_ids),
        "omission_density": len(failed_ids) / executable_total if executable_total else 0.0,
        "visible_omission_density": (
            len(failed_ids - muted_constraint_ids) / visible_executable_total
            if visible_executable_total
            else 0.0
        ),
        "muted_constraint_violation_rate": (
            len(hidden_failed) / len(muted_constraint_ids) if muted_constraint_ids else 0.0
        ),
        "hidden_failed_constraints": sorted(hidden_failed),
        "by_family": dict(sorted(by_family.items())),
        "by_layer": dict(sorted(by_layer.items())),
        "by_localization": dict(sorted(by_localization.items())),
    }


def _from_piki_parsed(parsed: dict[str, Any], catalog: ConstraintCatalog) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for rule in parsed.get("results", []):
        if rule.get("passed"):
            continue
        cid = str(rule.get("rule_id") or "piki-rule")
        layer = _layer_from_catalog_or_rule(cid, catalog)
        diagnostics.append(
            _diagnostic_from_message(
                message=str(rule.get("message") or "failed"),
                layer=layer,
                critic="piki",
                catalog=catalog,
                constraint_id=cid,
                file=str(rule.get("file") or ""),
                object_id=str(rule.get("object_id") or rule.get("instance") or ""),
            )
        )

    for diag in parsed.get("diagnostics", []):
        severity = str(diag.get("severity", "")).upper()
        if severity not in ("ERROR", "FATAL"):
            continue
        cid = str(diag.get("code") or "piki-diagnostic")
        layer = _layer_from_catalog_or_rule(cid, catalog)
        diagnostics.append(
            _diagnostic_from_message(
                message=str(diag.get("message") or "failed"),
                layer=layer,
                critic="piki",
                catalog=catalog,
                constraint_id=cid,
                file=str(diag.get("file") or ""),
                field=str(diag.get("field") or ""),
                object_id=str(diag.get("object_id") or diag.get("instance") or ""),
            )
        )
    return diagnostics


def _from_comments(
    critic: str,
    layer: str,
    comments: list[str],
    catalog: ConstraintCatalog,
) -> list[Diagnostic]:
    return [
        _diagnostic_from_message(str(comment), layer=layer, critic=critic, catalog=catalog)
        for comment in comments
        if _is_failure_comment(str(comment))
    ]


def _is_failure_comment(comment: str) -> bool:
    text = comment.strip()
    if not text:
        return False
    lower = text.lower()
    if text.startswith(("✓", "✅")):
        return False
    if lower.startswith("no deliverables required"):
        return False
    if lower.startswith("l0 passed:"):
        return False
    return True


def _diagnostic_from_message(
    message: str,
    layer: str,
    critic: str,
    catalog: ConstraintCatalog,
    constraint_id: str | None = None,
    file: str = "",
    field: str = "",
    object_id: str = "",
) -> Diagnostic:
    structured = _parse_structured_contract_message(message)
    if structured:
        file = file or structured.get("file", "")
        field = field or structured.get("field", "")
        object_id = object_id or structured.get("object_id", "")
    cid = constraint_id or _structured_constraint_id(structured, layer, critic)
    if cid is None:
        cid = _constraint_id_from_message(message, layer, catalog)
    spec = _lookup_spec(cid, layer, critic, catalog)
    return Diagnostic(
        constraint_id=cid,
        family=spec.family,
        layer=spec.layer if spec.layer != "unknown" else layer,
        message=message.splitlines()[0],
        critic=critic or spec.critic,
        object_id=object_id,
        file=file,
        field=field,
        localization=_localization(file=file, field=field, object_id=object_id, default=spec.localization),
    )


def _parse_structured_contract_message(message: str) -> dict[str, str]:
    """Extract file/field/object hints from stable critic contract messages."""

    first_line = message.splitlines()[0]
    out: dict[str, str] = {}
    file_match = re.match(r"(?P<file>[\w./-]+\.ya?ml)\b", first_line)
    if file_match:
        out["file"] = file_match.group("file")

    field_patterns = (
        r"missing required field '(?P<field>[^']+)'",
        r"expected (?:root key|field) '(?P<field>[^']+)'",
        r"'(?P<field>[^']+)' must be a (?:list|mapping)",
        r"(?P<field>[\w.-]+): expected mapping",
    )
    for pattern in field_patterns:
        match = re.search(pattern, first_line)
        if match:
            out["field"] = match.group("field")
            break

    object_patterns = (
        r"activities\[(?P<object_id>[^\]]+)\]",
        r"resources\[(?P<object_id>[^\]]+)\]",
        r"decisions\[(?P<object_id>[^\]]+)\]",
        r"hoists\[(?P<object_id>[^\]]+)\]",
        r"workfaces\[(?P<object_id>[^\]]+)\]",
        r"Facility (?P<object_id>[^:]+):",
        r"decision (?P<object_id>[^:]+):",
        r"workface (?P<object_id>[^:]+):",
    )
    for pattern in object_patterns:
        match = re.search(pattern, first_line)
        if match:
            out["object_id"] = match.group("object_id")
            break
    return out


def _structured_constraint_id(
    structured: dict[str, str], layer: str, critic: str
) -> str | None:
    if not structured:
        return None
    parts = [
        layer,
        critic or "critic",
        structured.get("file", "file"),
        structured.get("object_id", ""),
        structured.get("field", ""),
    ]
    suffix = ":".join(part for part in parts if part)
    return suffix or None


def _lookup_spec(cid: str, layer: str, critic: str, catalog: ConstraintCatalog) -> ConstraintSpec:
    if cid in catalog.by_id:
        return catalog.by_id[cid]
    for spec in catalog.constraints:
        if spec.layer == layer and (not critic or not spec.critic or spec.critic == critic):
            return spec
    return ConstraintSpec(
        id=cid,
        family=_family_for_layer(layer),
        layer=layer,
        executable=True,
        critic=critic,
        localization="task-level",
    )


def _constraint_id_from_message(message: str, layer: str, catalog: ConstraintCatalog) -> str:
    prefix = message.split(":", 1)[0].strip()
    if prefix and " " not in prefix:
        return prefix
    for spec in catalog.constraints:
        if spec.layer == layer:
            return spec.id
    return f"{layer}:unknown"


def _layer_from_catalog_or_rule(cid: str, catalog: ConstraintCatalog) -> str:
    if cid in catalog.by_id:
        return catalog.by_id[cid].layer
    if cid.startswith(("SCHEMA", "TELECOM-SCHEMA")):
        return "L1"
    if cid.startswith(("FK", "TELECOM-FK", "REF")):
        return "L2"
    if cid.startswith(("TELECOM-COLLISION", "GEOM", "LAYOUT")):
        return "L5"
    if cid.startswith(("POWER", "THERMAL", "STRUCT", "TELECOM-")):
        return "L3"
    return "L2"


def _layer_for_critic_result(critic: str) -> str:
    if critic in {"epc", "aidc-performance", "decision"}:
        return "L4"
    if critic == "constructability":
        return "L5"
    if critic == "syntax":
        return "L0"
    return "unknown"


def _family_for_layer(layer: str) -> str:
    return {
        "L0": "syntax",
        "L1": "schema",
        "L2": "reference",
        "L3": "static",
        "L4": "dynamic",
        "L5": "layout",
        "Deliverable": "deliverable",
    }.get(layer, "unspecified")


def _localization(file: str, field: str, object_id: str, default: str) -> str:
    if field:
        return "field-level"
    if file:
        return "file-level"
    if object_id:
        return "object-level"
    return default


def _coarse_message(diag: Diagnostic) -> str:
    family = diag.family.replace("-", " ")
    layer = diag.layer
    return f"{layer} {family} constraint failed."


def _localization_rank(localization: str) -> int:
    return {
        "task-level": 0,
        "object-level": 1,
        "file-level": 2,
        "field-level": 3,
    }.get(localization, 0)

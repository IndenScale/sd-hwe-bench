"""Constructability critic for detailed AIDC design tasks.

Checks that heavy facilities (chillers, transformers) have a viable hoisting
plan, a covering equipment rental schedule, and VDC workface definitions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sd_hwe_bench.critics.base import Critic, CriticResult
from sd_hwe_bench.task import TaskInstance


HEAVY_FACILITY_MODELS = {
    "chiller-10mw-facility",
    "transformer-40mva-facility",
}


class ConstructabilityCritic(Critic):
    """Evaluate construction planning deliverables for an AIDC workspace."""

    name = "Constructability"

    def evaluate(self, workspace_root: Path, task: TaskInstance) -> CriticResult:
        """Check hoisting plan, equipment rental, and VDC workfaces."""
        comments: list[str] = []

        # 1. Discover heavy facilities.
        heavy_facilities = self._load_heavy_facilities(workspace_root, comments)

        # 2. Load construction deliverables.
        hoisting_plan = self._load_yaml_list(
            workspace_root / "construction" / "hoisting-plan.yaml",
            "hoists",
            comments,
            aliases=("hoisting_plan",),
        )
        rental = self._load_yaml(
            workspace_root / "construction" / "equipment-rental.yaml", comments
        )
        workfaces = self._load_yaml_list(
            workspace_root / "construction" / "vdc-workface.yaml",
            "workfaces",
            comments,
            aliases=("vdc_workfaces",),
        )

        # Index hoisting entries by equipment id and find the latest referenced day.
        hoists_by_id: dict[str, dict[str, Any]] = {}
        max_day = 0
        for entry in hoisting_plan:
            if not isinstance(entry, dict):
                continue
            eid = entry.get("equipment_id")
            if not eid and "equipment" in entry:
                comments.append(
                    "hoisting-plan.yaml hoist entry: expected field 'equipment_id' "
                    "matching facility id; found 'equipment'"
                )
            if eid:
                hoists_by_id[eid] = entry
            try:
                day = int(entry.get("day", 0))
            except (TypeError, ValueError):
                day = 0
            if day > max_day:
                max_day = day

        # 3. Validate hoisting for each heavy facility.
        for facility in heavy_facilities:
            self._check_facility_hoist(facility, hoists_by_id, workspace_root, comments)

        # 4. Validate equipment rental.
        self._check_rental(rental, max_day, comments)

        # 5. Validate VDC workfaces.
        self._check_workfaces(workfaces, comments)

        passed = not comments
        return CriticResult(
            name=self.name,
            passed=passed,
            score=1.0 if passed else 0.0,
            comments=comments,
        )

    def _load_heavy_facilities(
        self, workspace_root: Path, comments: list[str]
    ) -> list[dict[str, Any]]:
        facilities_dir = workspace_root / "facilities"
        heavy: list[dict[str, Any]] = []
        if not facilities_dir.exists():
            comments.append("Missing facilities/ directory")
            return heavy

        for path in sorted(facilities_dir.glob("*.yaml")):
            data = self._safe_load(path, comments)
            if data is None:
                continue
            if isinstance(data, list):
                comments.append(f"{path.name}: expected mapping at root; found list")
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        comments.append(f"{path.name}: entry {idx} is not a mapping")
                        continue
                    if item.get("model") in HEAVY_FACILITY_MODELS:
                        heavy.append(item)
                continue
            if not isinstance(data, dict):
                comments.append(f"{path.name}: expected mapping at root")
                continue
            if data.get("model") in HEAVY_FACILITY_MODELS:
                heavy.append(data)
        return heavy

    def _check_facility_hoist(
        self,
        facility: dict[str, Any],
        hoists_by_id: dict[str, dict[str, Any]],
        workspace_root: Path,
        comments: list[str],
    ) -> None:
        fid = facility.get("id")
        model = facility.get("model")
        if not fid or not model:
            comments.append("Heavy facility missing id or model")
            return

        weight_kg = self._resolve_weight_kg(facility, model, workspace_root, comments)
        if weight_kg is None:
            comments.append(f"Facility {fid}: could not determine weight_kg")
            return

        hoist = hoists_by_id.get(fid)
        if not hoist:
            comments.append(f"Facility {fid}: missing hoisting-plan entry")
            return

        required_ton = 1.25 * (weight_kg / 1000.0)
        crane_ton = hoist.get("crane_ton")
        if crane_ton is None or float(crane_ton) < required_ton:
            comments.append(
                f"Facility {fid}: crane_ton {crane_ton} < required {required_ton:.2f}t"
            )

        radius_m = hoist.get("radius_m")
        if radius_m is None or float(radius_m) <= 0:
            comments.append(f"Facility {fid}: radius_m must be > 0")

        clearance_mm = hoist.get("clearance_mm")
        if clearance_mm is None or float(clearance_mm) < 1000:
            comments.append(f"Facility {fid}: clearance_mm must be >= 1000")

        hoist_point = hoist.get("hoist_point", {})
        if not isinstance(hoist_point, dict) or not all(
            k in hoist_point for k in ("x_mm", "y_mm", "z_mm")
        ):
            comments.append(f"Facility {fid}: hoist_point must contain x_mm, y_mm, z_mm")

    def _resolve_weight_kg(
        self,
        facility: dict[str, Any],
        model: str,
        workspace_root: Path,
        comments: list[str],
    ) -> float | None:
        # Prefer explicit facility weight.
        weight = facility.get("weight_kg")
        if weight is not None:
            return float(weight)

        # Fall back to the facility model definition.
        model_path = workspace_root / "models" / "facilities" / f"{model}.yaml"
        if model_path.exists():
            model_data = self._safe_load(model_path, comments)
            if isinstance(model_data, dict) and "weight_kg" in model_data:
                return float(model_data["weight_kg"])
        return None

    def _check_rental(
        self, rental: dict[str, Any] | None, max_day: int, comments: list[str]
    ) -> None:
        if rental is None:
            return
        equipment = rental.get("equipment", []) if isinstance(rental, dict) else []
        if not equipment and isinstance(rental, dict) and "equipment_rental" in rental:
            comments.append(
                "equipment-rental.yaml: expected root key 'equipment' as a list; "
                "found 'equipment_rental'"
            )
        if isinstance(rental, dict) and "equipment" not in rental:
            comments.append("equipment-rental.yaml: missing root key 'equipment' as a list")
        if equipment and not isinstance(equipment, list):
            comments.append("equipment-rental.yaml: 'equipment' must be a list")
            equipment = []
        main_crane = next(
            (
                e
                for e in equipment
                if isinstance(e, dict) and e.get("type") == "main-crane"
            ),
            None,
        )
        if main_crane is None and isinstance(rental, dict) and "main-crane" in rental:
            comments.append(
                "equipment-rental.yaml: expected main crane as list item "
                "under 'equipment' with type: main-crane; found root key 'main-crane'"
            )
        if main_crane is None:
            comments.append(
                "equipment-rental.yaml: missing equipment list item with type: main-crane, "
                "start_day, end_day, crane_ton"
            )
            return

        for field in ("type", "start_day", "end_day", "crane_ton"):
            if field not in main_crane:
                comments.append(
                    f"equipment-rental.yaml main-crane: missing required field '{field}'"
                )

        try:
            start_day = int(main_crane.get("start_day"))
            end_day = int(main_crane.get("end_day"))
        except (TypeError, ValueError):
            comments.append("main-crane: start_day and end_day must be integers")
            return

        try:
            if float(main_crane.get("crane_ton")) <= 0:
                comments.append("equipment-rental.yaml main-crane: crane_ton must be > 0")
        except (TypeError, ValueError):
            comments.append("equipment-rental.yaml main-crane: crane_ton must be numeric")

        if max_day > end_day or start_day > max_day:
            comments.append(
                f"main-crane rental [{start_day}, {end_day}] does not cover max hoisting day {max_day}"
            )

    def _check_workfaces(
        self, workfaces: list[Any], comments: list[str]
    ) -> None:
        if len(workfaces) < 2:
            comments.append(
                f"vdc-workface.yaml: need at least 2 workfaces, found {len(workfaces)}"
            )

        for idx, wf in enumerate(workfaces):
            if not isinstance(wf, dict):
                comments.append(f"vdc-workface.yaml: entry {idx} is not a mapping")
                continue
            prefix = f"workface {wf.get('id', idx)}"
            for field in ("id", "zone", "access_gate"):
                if not wf.get(field):
                    comments.append(f"{prefix}: missing or empty {field}")
            try:
                if float(wf.get("max_wind_speed_m_s", 0)) <= 0:
                    comments.append(f"{prefix}: max_wind_speed_m_s must be > 0")
            except (TypeError, ValueError):
                comments.append(f"{prefix}: max_wind_speed_m_s must be numeric")
            try:
                if float(wf.get("isolation_distance_mm", -1)) < 0:
                    comments.append(f"{prefix}: isolation_distance_mm must be >= 0")
            except (TypeError, ValueError):
                comments.append(f"{prefix}: isolation_distance_mm must be numeric")

    def _load_yaml(
        self, path: Path, comments: list[str]
    ) -> dict[str, Any] | None:
        if not path.exists():
            comments.append(f"Missing {path.relative_to(path.parents[1])}")
            return None
        data = self._safe_load(path, comments)
        if data is None:
            return None
        if not isinstance(data, dict):
            comments.append(f"{path.name}: expected mapping at root")
            return None
        return data

    def _load_yaml_list(
        self,
        path: Path,
        key: str,
        comments: list[str],
        aliases: tuple[str, ...] = (),
    ) -> list[Any]:
        data = self._load_yaml(path, comments)
        if data is None:
            return []
        for alias in aliases:
            if key not in data and alias in data:
                comments.append(
                    f"{path.name}: expected root key '{key}' as a list; found '{alias}'"
                )
        value = data.get(key, [])
        if not isinstance(value, list):
            comments.append(f"{path.name}: '{key}' must be a list")
            return []
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                comments.append(f"{path.name}: {key}[{idx}] must be a mapping")
                continue
            if key == "hoists":
                label = str(item.get("equipment_id") or item.get("equipment") or idx)
                for field in (
                    "equipment_id",
                    "day",
                    "crane_ton",
                    "radius_m",
                    "clearance_mm",
                    "hoist_point",
                ):
                    if field not in item:
                        comments.append(
                            f"{path.name} hoists[{label}]: missing required field '{field}'"
                        )
            elif key == "workfaces":
                label = str(item.get("id") or idx)
                for field in (
                    "id",
                    "zone",
                    "access_gate",
                    "max_wind_speed_m_s",
                    "isolation_distance_mm",
                ):
                    if field not in item:
                        comments.append(
                            f"{path.name} workfaces[{label}]: missing required field '{field}'"
                        )
        return value

    def _safe_load(self, path: Path, comments: list[str]) -> Any:
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            comments.append(f"{path.name}: YAML parse error - {exc}")
        except OSError as exc:
            comments.append(f"{path.name}: read error - {exc}")
        return None

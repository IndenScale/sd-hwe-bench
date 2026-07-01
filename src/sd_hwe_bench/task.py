"""Task schema — the canonical definition of a benchmark task."""

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from sd_hwe_bench.settings import settings


class Domain(str, Enum):
    TELECOM = "telecom"
    DATACENTER = "datacenter"
    MECHANICAL = "mechanical"
    HVAC = "hvac"
    STRUCTURAL = "structural"
    ELECTRICAL = "electrical"


class TaskType(str, Enum):
    INSTANCE_DECLARATION = "instance-declaration"
    LAYOUT_DESIGN = "layout-design"
    CONNECTION_DESIGN = "connection-design"
    MATING_DESIGN = "mating-design"
    COMPREHENSIVE = "comprehensive"
    INCREMENTAL = "incremental"
    CO_DESIGN = "co-design"
    EPC = "epc"
    DETAILED_DESIGN = "detailed-design"
    CONCEPTUAL_DESIGN = "conceptual-design"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RubricCriterion(BaseModel):
    """A single rubric criterion for LLM-as-Judge evaluation."""

    id: str = Field(description="Unique criterion identifier within the task")
    name: str = Field(description="Human-readable criterion label")
    description: str = Field(description="What the judge should look for")
    weight: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Weight of this criterion in the rubric score"
    )
    evaluation_steps: list[str] = Field(
        default_factory=list,
        description="Specific evaluation sub-steps the judge should follow",
    )


class RubricSet(BaseModel):
    """A named set of rubric criteria for LLM-as-Judge scoring."""

    name: str = Field(default="default", description="Rubric set name")
    criteria: list[RubricCriterion] = Field(description="List of rubric criteria")
    threshold: float = Field(
        default=settings.DEFAULT_RUBRIC_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Pass threshold for this rubric set",
    )


class NumericAssertion(BaseModel):
    """A numeric value check for an expected output file."""

    file: str = Field(description="Relative path from workspace root, e.g. reports/link-budget.yaml")
    yaml_path: str = Field(description="Dot-separated path, e.g. results.coverage_radius_km")
    expected: float = Field(description="Expected numeric value")
    tolerance: float = Field(default=0.05, description="Relative tolerance (0.05 = 5%)")
    weight: float = Field(default=1.0, description="Weight of this assertion within numeric layer")


class EvaluationSpec(BaseModel):
    """Declarative spec for one analysis critic bound to a scoring layer.

    When a task supplies ``evaluation``, it overrides the task_type-derived
    default dispatch in the critic registry.
    """

    critic: str = Field(
        description="Registered analysis critic name (e.g. epc, aidc-performance, constructability)"
    )
    layer: str = Field(default="L4", description="Scoring layer this critic writes (L4/L5/...)")
    mode: str = Field(
        default="replace",
        description="replace=overwrite the layer; merge=combine with the existing layer",
    )
    provides_performance: bool = Field(
        default=False,
        description="Whether this critic's score sets the diagnostic performance_score",
    )
    params: dict = Field(default_factory=dict, description="Critic-specific parameters")


class ConstraintMetadata(BaseModel):
    """An explicit applicable constraint for constraint-gap experiments."""

    id: str = Field(description="Stable constraint id")
    family: str = Field(
        default="unspecified",
        description="Constraint family, e.g. schema, reference, electrical, thermal",
    )
    layer: str = Field(default="unknown", description="Scoring layer, e.g. L1-L5")
    executable: bool = Field(default=True, description="Whether a deterministic critic checks it")
    critic: str = Field(default="", description="Critic or rule that checks this constraint")
    localization: str = Field(
        default="task-level",
        description="Best diagnostic localization supported by the critic",
    )
    description: str = Field(default="", description="Human-readable constraint text")


class TaskMetadata(BaseModel):
    """Metadata for a single benchmark task."""

    task_id: str = Field(description="Unique task identifier")
    name: str = Field(default="", description="Human-readable task name (Chinese)")
    description: str = Field(default="", description="Short description of the task (Chinese)")
    domain: Domain = Field(description="Engineering domain")
    task_type: TaskType = Field(description="Category of design task")
    difficulty: Difficulty = Field(description="Estimated difficulty level")
    requirement: str = Field(description="Natural language requirement")
    plugins: list[str] = Field(default_factory=lambda: list(settings.DEFAULT_PLUGINS))
    expected_files: list[str] = Field(default_factory=list)
    scoring_layers: list[str] = Field(default_factory=lambda: list(settings.DEFAULT_SCORING_LAYERS))
    expected_deliverables: list[str] = Field(default_factory=list)
    numeric_assertions: list[NumericAssertion] = Field(
        default_factory=list,
        description="Optional numeric value checks for reports with tolerance",
    )
    rubrics: list[RubricSet] = Field(
        default_factory=list,
        description="Optional LLM-as-Judge rubric sets for qualitative evaluation",
    )
    decision_variables: dict = Field(
        default_factory=dict,
        description="For co-design tasks: map of ADL paths → allowed value ranges",
    )
    scenario: dict = Field(
        default_factory=dict,
        description=(
            "For conceptual-design tasks: scenario parameters (climate, tariff, "
            "quotas, supplier maturity) and criteria_weights driving multi-scheme selection"
        ),
    )
    l7_config: dict = Field(
        default_factory=dict,
        description="L7 simulation config: weather, hours, objective_weights",
    )
    evaluation: list[EvaluationSpec] = Field(
        default_factory=list,
        description="Optional explicit analysis-critic specs; overrides task_type-derived defaults",
    )
    constraints: list[ConstraintMetadata] = Field(
        default_factory=list,
        description="Explicit constraint catalog entries for gap experiments",
    )
    scale_level: str = Field(
        default="unknown",
        description="Task scale for experiment stratification: low, medium, high",
    )
    coupling_level: str = Field(
        default="unknown",
        description="Constraint coupling level for stratified reporting",
    )
    task_family: str = Field(default="", description="Experiment family label")
    constraint_families: list[str] = Field(
        default_factory=list,
        description="Constraint families expected to appear in this task",
    )
    expected_saturation: bool = Field(
        default=False,
        description="Whether this is expected to be a low-coupling saturated task",
    )


class TaskInstance:
    """Runtime representation of a benchmark task."""

    def __init__(self, task_dir: Path):
        self.task_dir = Path(task_dir)
        raw = yaml.safe_load((self.task_dir / "task.yaml").read_text())
        self.metadata = TaskMetadata(**raw)
        self.scaffold_dir = self.task_dir / "scaffold"
        self.solution_dir = self.task_dir / "solution"
        self.expected_dir = self.task_dir / "expected"

    @property
    def task_id(self) -> str:
        return self.metadata.task_id

    @property
    def requirement(self) -> str:
        return self.metadata.requirement

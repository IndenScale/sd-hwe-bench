"""Task schema — the canonical definition of a benchmark task."""

from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


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


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RubricCriterion(BaseModel):
    """A single rubric criterion for LLM-as-Judge evaluation."""

    id: str = Field(description="Unique criterion identifier within the task")
    name: str = Field(description="Human-readable criterion label")
    description: str = Field(description="What the judge should look for")
    weight: float = Field(default=1.0, ge=0.0, le=1.0,
                          description="Weight of this criterion in the rubric score")
    evaluation_steps: list[str] = Field(
        default_factory=list,
        description="Specific evaluation sub-steps the judge should follow",
    )


class RubricSet(BaseModel):
    """A named set of rubric criteria for LLM-as-Judge scoring."""

    name: str = Field(default="default", description="Rubric set name")
    criteria: list[RubricCriterion] = Field(description="List of rubric criteria")
    threshold: float = Field(default=0.6, ge=0.0, le=1.0,
                             description="Pass threshold for this rubric set")


class TaskMetadata(BaseModel):
    """Metadata for a single benchmark task."""

    task_id: str = Field(description="Unique task identifier")
    name: str = Field(default="", description="Human-readable task name (Chinese)")
    description: str = Field(default="", description="Short description of the task (Chinese)")
    domain: Domain = Field(description="Engineering domain")
    task_type: TaskType = Field(description="Category of design task")
    difficulty: Difficulty = Field(description="Estimated difficulty level")
    requirement: str = Field(description="Natural language requirement")
    plugins: list[str] = Field(default_factory=lambda: ["telecom"])
    expected_files: list[str] = Field(default_factory=list)
    scoring_layers: list[str] = Field(default_factory=lambda: ["L0", "L1", "L2", "L3"])
    expected_deliverables: list[str] = Field(default_factory=list)
    rubrics: list[RubricSet] = Field(
        default_factory=list,
        description="Optional LLM-as-Judge rubric sets for qualitative evaluation",
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

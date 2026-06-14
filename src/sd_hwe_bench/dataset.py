"""Dataset management — discover, load, and validate benchmark tasks."""

from pathlib import Path

from sd_hwe_bench.task import TaskInstance


class Dataset:
    """Collection of benchmark tasks organized by domain."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self._tasks: dict[str, TaskInstance] = {}

    def discover(self) -> list[str]:
        """Discover all task directories and return task IDs."""
        task_ids = []
        tasks_dir = self.root_dir / "tasks"

        if not tasks_dir.exists():
            return task_ids

        for domain_dir in sorted(tasks_dir.iterdir()):
            if not domain_dir.is_dir():
                continue
            for task_dir in sorted(domain_dir.iterdir()):
                if not task_dir.is_dir():
                    continue
                task_yaml = task_dir / "task.yaml"
                if task_yaml.exists():
                    task_id = f"{domain_dir.name}/{task_dir.name}"
                    task_ids.append(task_id)

        return task_ids

    def load_task(self, task_id: str) -> TaskInstance:
        """Load a single task by ID."""
        if task_id in self._tasks:
            return self._tasks[task_id]

        task_path = self.root_dir / "tasks" / task_id
        task = TaskInstance(task_path)
        self._tasks[task_id] = task
        return task

    def list_by_domain(self) -> dict[str, list[str]]:
        """Group task IDs by domain."""
        by_domain: dict[str, list[str]] = {}
        for task_id in self.discover():
            domain = task_id.split("/")[0]
            by_domain.setdefault(domain, []).append(task_id)
        return by_domain

    def list_by_type(self) -> dict[str, list[str]]:
        """Group task IDs by task type."""
        by_type: dict[str, list[str]] = {}
        for task_id in self.discover():
            task = self.load_task(task_id)
            ttype = task.metadata.task_type.value
            by_type.setdefault(ttype, []).append(task_id)
        return by_type

    def __len__(self) -> int:
        return len(self.discover())

    def __repr__(self) -> str:
        return f"Dataset({self.root_dir}, {len(self)} tasks)"

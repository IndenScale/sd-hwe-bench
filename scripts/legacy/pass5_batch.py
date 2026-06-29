#!/usr/bin/env python3
"""Batch run pass@5 on the 30-task benchmark set for kimi and deepseek-v4-pro.

Task set: 28-task leaderboard + aidc-operation-002 + aidc-co-design-002.
Each model runs 30 tasks × 5 passes = 150 rollouts.
"""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

BENCH_DIR = Path("/Users/indenscale/workspace/sd-hwe-bench")
LOG_DIR = BENCH_DIR / "logs" / "pass5-20260628"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TASKS = [
    "telecom/comprehensive-001",
    "telecom/connection-design-001",
    "telecom/dc-stage1-foundation-rackmount-deploy-thermal",
    "telecom/dc-stage2-foundation-rackmount-deploy-thermal",
    "telecom/dc-stage3-foundation-rackmount-deploy-thermal",
    "telecom/dc-stage4-foundation-rackmount-deploy-thermal",
    "telecom/instance-declare-001",
    "telecom/layout-design-001",
    "telecom/mating-design-001",
    "telecom/rack-stage1-init-deploy-connect-verify",
    "telecom/rack-stage2-init-deploy-connect-verify",
    "telecom/rack-stage3-init-deploy-connect-verify",
    "telecom/rack-stage4-init-deploy-connect-verify",
    "telecom/site-stage1-tower-feeder-grounding",
    "telecom/site-stage2-tower-feeder-grounding",
    "telecom/site-stage3-tower-feeder-grounding",
    "telecom/telecom-cross-001",
    "telecom/telecom-cross-002",
    "telecom/telecom-cross-003",
    "telecom/telecom-easy-compound-001",
    "telecom/telecom-easy-compound-002",
    "telecom/telecom-easy-compound-003",
    "telecom/telecom-easy-compound-004",
    "telecom/telecom-easy-compound-005",
    "telecom/telecom-emergent-001",
    "telecom/telecom-emergent-002",
    "telecom/telecom-emergent-003",
    "telecom/telecom-emergent-004",
    "telecom/aidc-operation-002",
    "telecom/aidc-co-design-002",
]

MODELS = {
    "kimi": "kimi",
    "deepseek-v4-pro": "codex:deepseek-v4-pro",
}

MAX_WORKERS = 4
TIMEOUT_PER_TASK_S = 3600  # 1 hour per task (5 passes)


def run_task(model_name: str, actor_spec: str, task_id: str) -> tuple[str, bool, str]:
    safe_task = task_id.replace("/", "_")
    log_file = LOG_DIR / f"{model_name}_{safe_task}.log"
    start = time.time()

    cmd = [
        "uv", "run", "sd-hwe-bench", "run", task_id,
        "--actor", actor_spec,
        "--passes", "5",
        "--jobs", "5",
        "--sandbox", "none",
        "--run-dir", f"runs/pass5-{model_name}-20260628",
        "--timeout", "600",
    ]

    with open(log_file, "w") as f:
        proc = subprocess.run(
            cmd,
            cwd=BENCH_DIR,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_PER_TASK_S,
        )
        f.write(proc.stdout)
        f.write(proc.stderr)

    elapsed = time.time() - start
    stdout = proc.stdout

    # Parse pass@k line from stdout, e.g. "Pass@1: 100.0% | Pass@5: 100.0%"
    if "Pass@1:" in stdout and "Pass@5:" in stdout:
        try:
            p1 = stdout.split("Pass@1:")[-1].split("|")[0].strip()
            p5 = stdout.split("Pass@5:")[-1].split()[0].strip()
            return task_id, True, f"p1={p1} p5={p5} ({elapsed:.0f}s)"
        except Exception:
            pass
    return task_id, False, f"rc={proc.returncode} ({elapsed:.0f}s)"


def run_model(model_name: str, actor_spec: str) -> None:
    total = len(TASKS)
    completed = 0
    passed = 0
    failed = 0

    print(f"\n=== {model_name} pass@5 batch: {total} tasks, {MAX_WORKERS} concurrent ===")
    print(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Logs: {LOG_DIR}")
    print()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(run_task, model_name, actor_spec, task_id): task_id
            for task_id in TASKS
        }

        for future in as_completed(futures):
            task_id, ok, msg = future.result()
            completed += 1
            if ok:
                passed += 1
            else:
                failed += 1
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] [{completed}/{total}] {model_name} {msg} — {task_id}")

    print()
    print(f"=== {model_name} Done at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"Scored: {passed}/{total} ({100*passed/total:.1f}%)")
    print(f"Failed: {failed}/{total}")


def main() -> None:
    for model_name, actor_spec in MODELS.items():
        run_model(model_name, actor_spec)


if __name__ == "__main__":
    main()

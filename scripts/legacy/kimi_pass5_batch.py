#!/usr/bin/env python3
"""Batch run all 46 telecom tasks with kimi pass@5, 4 concurrent tasks."""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

BENCH_DIR = Path("/Users/indenscale/workspace/sd-hwe-bench")
LOG_DIR = BENCH_DIR / "logs" / "kimi-pass5-20260627"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TASKS = [
    "telecom/comprehensive-001",
    "telecom/connection-design-001",
    "telecom/datacenter-001",
    "telecom/datacenter-002",
    "telecom/datacenter-003",
    "telecom/datacenter-004",
    "telecom/datacenter-005",
    "telecom/datacenter-006",
    "telecom/datacenter-007",
    "telecom/datacenter-008",
    "telecom/instance-declare-001",
    "telecom/layout-design-001",
    "telecom/mating-design-001",
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
    "telecom/telecom-rack-001",
    "telecom/telecom-rack-002",
    "telecom/telecom-rack-003",
    "telecom/telecom-rack-004",
    "telecom/telecom-rack-005",
    "telecom/telecom-rack-006",
    "telecom/telecom-rack-007",
    "telecom/telecom-rack-008",
    "telecom/telecom-rack-009",
    "telecom/telecom-rack-010",
    "telecom/telecom-rack-011",
    "telecom/telecom-rack-012",
    "telecom/telecom-rack-013",
    "telecom/telecom-rack-014",
    "telecom/telecom-rack-015",
    "telecom/telecom-site-001",
    "telecom/telecom-site-002",
    "telecom/telecom-site-003",
    "telecom/telecom-site-004",
    "telecom/telecom-site-005",
    "telecom/telecom-site-006",
]

MAX_WORKERS = 4
TOTAL = len(TASKS)
completed = 0
passed = 0
failed = 0

print(f"=== kimi pass@5 batch: {TOTAL} tasks, {MAX_WORKERS} concurrent ===")
print(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Logs: {LOG_DIR}")
print()

def run_task(task_id: str, idx: int) -> tuple[str, bool, str]:
    log_file = LOG_DIR / f"{task_id.replace('/', '_')}.log"
    start = time.time()
    
    with open(log_file, "w") as f:
        proc = subprocess.run(
            [
                "uv", "run", "sd-hwe-bench", "run", task_id,
                "--actor", "kimi",
                "--passes", "5",
                "--jobs", "5",
                "--sandbox", "docker",
                "--self-check",
            ],
            cwd=BENCH_DIR,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour per task
        )
        f.write(proc.stdout)
        f.write(proc.stderr)
    
    elapsed = time.time() - start
    stdout = proc.stdout
    
    # Determine pass/fail from output
    if "Pass@1:" in stdout:
        if "Pass@1: 100%" in stdout:
            return task_id, True, f"PASS 100% ({elapsed:.0f}s)"
        else:
            return task_id, False, f"FAIL {stdout.split('Pass@1:')[-1].split()[0].strip()} ({elapsed:.0f}s)"
    else:
        rc = proc.returncode
        return task_id, False, f"FAIL rc={rc} ({elapsed:.0f}s)"

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {}
    for i, task_id in enumerate(TASKS):
        futures[executor.submit(run_task, task_id, i + 1)] = task_id
    
    for future in as_completed(futures):
        task_id, ok, msg = future.result()
        completed += 1
        if ok:
            passed += 1
        else:
            failed += 1
        
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{completed}/{TOTAL}] {msg} — {task_id}")

print()
print(f"=== Done at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
print(f"Passed: {passed}/{TOTAL} ({100*passed/TOTAL:.1f}%)")
print(f"Failed: {failed}/{TOTAL}")

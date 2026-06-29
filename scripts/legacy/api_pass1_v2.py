#!/usr/bin/env python3
"""Re-run API actors pass@1 with fixed prompt + parser. 3 concurrent actors."""

import subprocess, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

BENCH_DIR = Path("/Users/indenscale/workspace/sd-hwe-bench")
LOG_DIR = BENCH_DIR / "logs" / "api-pass1-v2-20260627"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TASKS = [
    "telecom/comprehensive-001","telecom/connection-design-001",
    "telecom/datacenter-001","telecom/datacenter-002","telecom/datacenter-003",
    "telecom/datacenter-004","telecom/datacenter-005","telecom/datacenter-006",
    "telecom/datacenter-007","telecom/datacenter-008",
    "telecom/instance-declare-001","telecom/layout-design-001","telecom/mating-design-001",
    "telecom/telecom-cross-001","telecom/telecom-cross-002","telecom/telecom-cross-003",
    "telecom/telecom-easy-compound-001","telecom/telecom-easy-compound-002",
    "telecom/telecom-easy-compound-003","telecom/telecom-easy-compound-004","telecom/telecom-easy-compound-005",
    "telecom/telecom-emergent-001","telecom/telecom-emergent-002",
    "telecom/telecom-emergent-003","telecom/telecom-emergent-004",
    "telecom/telecom-rack-001","telecom/telecom-rack-002","telecom/telecom-rack-003",
    "telecom/telecom-rack-004","telecom/telecom-rack-005","telecom/telecom-rack-006",
    "telecom/telecom-rack-007","telecom/telecom-rack-008","telecom/telecom-rack-009",
    "telecom/telecom-rack-010","telecom/telecom-rack-011","telecom/telecom-rack-012",
    "telecom/telecom-rack-013","telecom/telecom-rack-014","telecom/telecom-rack-015",
    "telecom/telecom-site-001","telecom/telecom-site-002","telecom/telecom-site-003",
    "telecom/telecom-site-004","telecom/telecom-site-005","telecom/telecom-site-006",
]

ACTORS = [
    ("deepseek-flash", ["--actor", "openai:deepseek-chat"]),
    ("deepseek-pro", ["--actor", "openai:deepseek-reasoner"]),
]

TOTAL = len(TASKS) * len(ACTORS)
print(f"=== API pass@1 v2: {len(TASKS)} tasks x {len(ACTORS)} actors = {TOTAL} ===")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}")

results = {}

def run_one(actor_name, actor_args, task_id):
    slug = f"{actor_name}_{task_id.replace('/', '_')}"
    log_file = LOG_DIR / f"{slug}.log"
    start = time.time()
    cmd = ["uv","run","sd-hwe-bench","run",task_id,*actor_args,
           "--passes","1","--jobs","1","--sandbox","docker","--self-check"]
    with open(log_file,"w") as f:
        proc = subprocess.run(cmd,cwd=BENCH_DIR,capture_output=True,text=True,timeout=1800)
        f.write(proc.stdout); f.write(proc.stderr)
    elapsed = time.time()-start
    stdout = proc.stdout
    success = False; score = None
    for line in stdout.split("\n"):
        if line.startswith("PASS "): success = True
        elif line.startswith("FAIL "): success = False
        if "overall score:" in line:
            try: score = float(line.split("overall score:")[-1].strip().replace("%",""))
            except: pass
    score_str = f"{score:.0f}%" if score is not None else "?"
    status = "PASS" if success else "FAIL"
    return actor_name, task_id, success, f"{status} {score_str} ({elapsed:.0f}s)", score

jobs = [(an,aa,tid) for an,aa in ACTORS for tid in TASKS]
completed = 0

with ThreadPoolExecutor(max_workers=3) as ex:
    futures = {ex.submit(run_one,an,aa,tid):(an,tid) for an,aa,tid in jobs}
    for f in as_completed(futures):
        an,tid,ok,msg,score = f.result()
        completed += 1
        results.setdefault(an,{"passed":0,"failed":0,"scores":[]})
        results[an]["passed" if ok else "failed"] += 1
        if score is not None: results[an]["scores"].append(score)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{completed}/{TOTAL}] [{an}] {msg} — {tid}")

print(f"\n=== Done: {datetime.now().strftime('%H:%M:%S')} ===")
for an in sorted(results):
    s = results[an]; t = s["passed"]+s["failed"]
    avg = sum(s["scores"])/len(s["scores"]) if s["scores"] else 0
    print(f"{an}: {s['passed']}/{t} pass@1 = {100*s['passed']/t:.1f}%, avg = {avg:.1f}%")

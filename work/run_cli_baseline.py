"""Baseline runner using CLI -p mode for Gemini and Kimi, API for DeepSeek."""
import os, sys, json, time, subprocess, shutil, re, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
os.environ["PIPKIPATH"] = "/Users/indenscale/workspace/piki/.venv/bin/python"

from sd_hwe_bench.dataset import Dataset
from sd_hwe_bench.agents.prompt_builder import build_agent_prompt
from sd_hwe_bench.scorer import score_task
from openai import OpenAI

DEEPSEEK_CLIENT = OpenAI(base_url="https://api.deepseek.com/v1", api_key="__REDACTED__")
DATASET_ROOT = os.getcwd()

SYSTEM_PROMPT = """You are a hardware engineering design agent. Produce piki YAML declarations.
Follow directory conventions EXACTLY:
- instances/devices/ — device instances
- instances/racks/ — rack instances  
- instances/pdus/ — PDU instances
- instances/ports/ — port instances
- instances/transceivers/ — transceiver instances
- instances/fibers/ — fiber instances
- instances/port_connections/ — port connection instances
- layouts/layout.yaml — rack layout
- mates/rack-mount/ — rack mount mates
- mates/power-iec/ — power IEC mates
- mates/sfp28-cage/ — SFP28 cage mates
- mates/lc-connector/ — LC connector mates

Output each file as a separate ```yaml code block with file path as comment on first line.
Example:
```yaml
# instances/devices/SRV-01.yaml
id: SRV-01
...
```"""


def parse_and_write_files(text, run_dir):
    """Parse YAML blocks with file path comments and write to disk."""
    # Pattern: ```yaml\n# path/to/file.yaml\n...content...```
    blocks = list(re.finditer(r'```yaml\n(.*?)```', text, re.DOTALL))
    count = 0
    
    for match in blocks:
        block = match.group(1).strip()
        lines = block.split('\n')
        
        # Check if first line is a file path comment
        filepath = None
        if lines and lines[0].startswith('#'):
            filepath = lines[0].lstrip('#').strip()
            yaml_content = '\n'.join(lines[1:]).strip()
        else:
            yaml_content = block
            # Try to infer path from id
            id_match = re.search(r'^id:\s*(\S+)', block, re.MULTILINE)
            if not id_match:
                continue
            yaml_id = id_match.group(1)
            if 'mate:' in block:
                mate_m = re.search(r'mate:\s*(\S+)', block)
                mate_type = mate_m.group(1) if mate_m else 'unknown'
                filepath = f"mates/{mate_type}/{yaml_id}.yaml"
            elif any(k in block for k in ('rack:', 'ru_position:', 'position_u:')):
                if yaml_id == 'layout' or block.strip().startswith('-'):
                    filepath = "layouts/layout.yaml"
                else:
                    filepath = f"instances/racks/{yaml_id}.yaml"
            elif 'from_port:' in block or 'to_port:' in block:
                if 'family:' in block:
                    filepath = f"instances/port_connections/{yaml_id}.yaml"
                elif 'fiber_type:' in block:
                    filepath = f"instances/fibers/{yaml_id}.yaml"
                else:
                    filepath = f"instances/port_connections/{yaml_id}.yaml"
            elif 'port_type:' in block:
                filepath = f"instances/ports/{yaml_id}.yaml"
            elif 'tdp_w:' in block or 'interface' in block:
                filepath = f"instances/devices/{yaml_id}.yaml"
            elif 'capacity_w:' in block:
                filepath = f"instances/pdus/{yaml_id}.yaml"
            else:
                filepath = f"instances/{yaml_id}.yaml"
        
        if filepath:
            fpath = run_dir / filepath
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(yaml_content, encoding="utf-8")
            count += 1
    
    return count


def run_api_model(model_name, task_id):
    """Run via OpenAI-compatible API."""
    ds = Dataset(Path(DATASET_ROOT))
    task = ds.load_task(task_id)
    meta = {
        "task_id": task_id, "name": task.metadata.name,
        "task_type": task.metadata.task_type.value,
        "difficulty": task.metadata.difficulty.value,
        "plugins": task.metadata.plugins,
        "requirement": task.metadata.requirement,
        "expected_files": task.metadata.expected_files,
        "expected_deliverables": task.metadata.expected_deliverables,
    }
    prompt = build_agent_prompt(meta, task.scaffold_dir)
    
    start = time.time()
    resp = DEEPSEEK_CLIENT.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0, max_tokens=8192,
    )
    elapsed = time.time() - start
    text = resp.choices[0].message.content
    
    run_dir = Path(f"work/baseline-runs/api_{model_name.replace('/','_')}/{task_id.replace('/','_')}/pass_0")
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy scaffold
    if task.scaffold_dir.exists():
        for item in task.scaffold_dir.iterdir():
            if item.name.startswith("."): continue
            dest = run_dir / item.name
            if item.is_dir():
                if not dest.exists():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                if not dest.exists():
                    shutil.copy2(item, dest)
    
    (run_dir / ".model_response.txt").write_text(text, encoding="utf-8")
    file_count = parse_and_write_files(text, run_dir)
    
    score = score_task(
        task_id=task_id, agent_output_dir=run_dir,
        expected_deliverables=task.metadata.expected_deliverables,
        rubric_sets=None, requirement=task.metadata.requirement, rubrics_model=None,
    )
    
    return {
        "model": model_name, "task_id": task_id,
        "pass": score.success, "overall_score": score.overall_score,
        "elapsed_s": elapsed, "files_written": file_count,
        "tokens": resp.usage.total_tokens if resp.usage else None,
        "layers": {name: f"{ls.passed}/{ls.total}" for name, ls in score.layers.items() if ls.total > 0},
    }


def run_cli_model(cli_cmd, model_label, task_id):
    """Run via CLI -p mode (Gemini or Kimi)."""
    ds = Dataset(Path(DATASET_ROOT))
    task = ds.load_task(task_id)
    meta = {
        "task_id": task_id, "name": task.metadata.name,
        "task_type": task.metadata.task_type.value,
        "difficulty": task.metadata.difficulty.value,
        "plugins": task.metadata.plugins,
        "requirement": task.metadata.requirement,
        "expected_files": task.metadata.expected_files,
        "expected_deliverables": task.metadata.expected_deliverables,
    }
    prompt = build_agent_prompt(meta, task.scaffold_dir)
    full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
    
    run_dir = Path(f"work/baseline-runs/cli_{model_label.replace('/','_')}/{task_id.replace('/','_')}/pass_0")
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy scaffold
    if task.scaffold_dir.exists():
        for item in task.scaffold_dir.iterdir():
            if item.name.startswith("."): continue
            dest = run_dir / item.name
            if item.is_dir():
                if not dest.exists():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                if not dest.exists():
                    shutil.copy2(item, dest)
    
    start = time.time()
    try:
        result = subprocess.run(
            cli_cmd,
            input=full_prompt,
            text=True, capture_output=True, timeout=300,
            cwd=str(run_dir),
        )
        elapsed = time.time() - start
        text = result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        text = "[TIMEOUT]"
    
    (run_dir / ".model_response.txt").write_text(text, encoding="utf-8")
    file_count = parse_and_write_files(text, run_dir)
    
    score = score_task(
        task_id=task_id, agent_output_dir=run_dir,
        expected_deliverables=task.metadata.expected_deliverables,
        rubric_sets=None, requirement=task.metadata.requirement, rubrics_model=None,
    )
    
    return {
        "model": model_label, "task_id": task_id,
        "pass": score.success, "overall_score": score.overall_score,
        "elapsed_s": elapsed, "files_written": file_count,
        "layers": {name: f"{ls.passed}/{ls.total}" for name, ls in score.layers.items() if ls.total > 0},
    }


if __name__ == "__main__":
    # Config
    models = [
        # DeepSeek via API
        ("api", "deepseek-v4-flash", None),
        ("api", "deepseek-v4-pro", None),
        # Gemini via CLI
        ("cli", "gemini-2.5-flash", ["gemini", "-p", "-m", "gemini-2.5-flash", "--output-format", "text", "--skip-trust"]),
        # Kimi via CLI  
        ("cli", "kimi-k2.7-code", ["kimi", "-p", "-m", "kimi-code/kimi-for-coding", "--output-format", "text"]),
    ]
    
    task_ids = [
        "telecom/comprehensive-001",
        "telecom/connection-design-001",
        "telecom/instance-declare-001",
        "telecom/layout-design-001",
        "telecom/mating-design-001",
    ]
    
    all_results = []
    
    for run_type, model_label, cli_cmd in models:
        print(f"\n{'='*60}")
        print(f"[{run_type}] {model_label}")
        print(f"{'='*60}")
        
        for tid in task_ids:
            print(f"  {tid}...", end=" ", flush=True)
            try:
                if run_type == "api":
                    result = run_api_model(model_label, tid)
                else:
                    result = run_cli_model(cli_cmd, model_label, tid)
                status = "✅" if result["pass"] else "❌"
                print(f"{status} {result['overall_score']:.0%} | {result['elapsed_s']:.1f}s | {result.get('tokens','?')}t | {result['files_written']} files")
                all_results.append(result)
            except Exception as e:
                print(f"❌ ERROR: {e}")
                all_results.append({"model": model_label, "task_id": tid, "error": str(e)})
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for run_type, model_label, _ in models:
        model_results = [r for r in all_results if r.get("model") == model_label and "error" not in r]
        if model_results:
            passed = sum(1 for r in model_results if r["pass"])
            avg_score = sum(r["overall_score"] for r in model_results) / len(model_results)
            print(f"{model_label}: Pass@1={passed}/{len(model_results)}({passed/len(model_results):.0%}) | Avg={avg_score:.0%}")
    
    with open("work/baseline_all_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nSaved to work/baseline_all_results.json")

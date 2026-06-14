"""Baseline runner using OpenAI-compatible API to call DeepSeek models directly."""
import os, sys, json, time, subprocess, shutil, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
os.environ["PIPKIPATH"] = "/Users/indenscale/workspace/piki/.venv/bin/python"

from openai import OpenAI

BASE_URL = "https://api.deepseek.com/v1"
API_KEY = "__REDACTED__"
SYSTEM_PROMPT = """You are a hardware engineering design agent. You must produce piki YAML design declarations.
Follow the piki directory conventions exactly:
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
Output ONLY valid YAML files as code blocks."""

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def run_model(model_name, task_id, dataset_root):
    """Run a single model on a single task."""
    from sd_hwe_bench.dataset import Dataset
    from sd_hwe_bench.agents.prompt_builder import build_agent_prompt
    
    ds = Dataset(Path(dataset_root))
    task = ds.load_task(task_id)
    meta = {
        "task_id": task_id,
        "name": task.metadata.name,
        "task_type": task.metadata.task_type.value,
        "difficulty": task.metadata.difficulty.value,
        "plugins": task.metadata.plugins,
        "requirement": task.metadata.requirement,
        "expected_files": task.metadata.expected_files,
        "expected_deliverables": task.metadata.expected_deliverables,
    }
    prompt = build_agent_prompt(meta, task.scaffold_dir)
    
    start = time.time()
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=8192,
    )
    elapsed = time.time() - start
    text = resp.choices[0].message.content
    
    # Extract YAML files from code blocks and write them
    run_dir = Path(f"work/baseline-runs/api_{model_name.replace('/','_')}/{task_id.replace('/','_')}/pass_0")
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy scaffold
    if task.scaffold_dir.exists():
        for item in task.scaffold_dir.iterdir():
            if item.name.startswith("."):
                continue
            dest = run_dir / item.name
            if item.is_dir():
                if not dest.exists():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                if not dest.exists():
                    shutil.copy2(item, dest)
    
    # Parse YAML blocks from response and write files
    import re
    blocks = re.findall(r'```yaml\n(.*?)```', text, re.DOTALL)
    
    # Save raw response for debugging
    (run_dir / ".model_response.txt").write_text(text, encoding="utf-8")
    
    # Try to write each YAML block as a file, guessing path from content
    file_count = 0
    for i, block in enumerate(blocks):
        # Try to guess filename from id field
        id_match = re.search(r'^id:\s*(\S+)', block, re.MULTILINE)
        if id_match:
            yaml_id = id_match.group(1)
            # Determine directory based on content
            content = block.strip()
            if 'mate:' in content:
                mate_match = re.search(r'mate:\s*(\S+)', content)
                if mate_match:
                    mate_type = mate_match.group(1)
                    fname = f"mates/{mate_type}/{yaml_id}.yaml"
                else:
                    fname = f"mates/{yaml_id}.yaml"
            elif 'rack:' in content or 'ru_position:' in content or 'position_u:' in content:
                fname = f"layouts/{yaml_id}.yaml" if yaml_id != 'layout' else "layouts/layout.yaml"
            elif 'from_port:' in content and 'to_port:' in content and 'family:' not in content:
                fname = f"instances/port_connections/{yaml_id}.yaml"
            elif 'fiber_type:' in content:
                fname = f"instances/fibers/{yaml_id}.yaml"
            elif 'port_type:' in content or ('port_name:' in content and 'device_id:' in content):
                fname = f"instances/ports/{yaml_id}.yaml"
            elif 'interface_type:' in content:
                fname = f"instances/devices/{yaml_id}.yaml"
            elif 'total_u:' in content or ('family:' in content and 'Rack' in content):
                fname = f"instances/racks/{yaml_id}.yaml"
            elif 'capacity_w:' in content or 'phase:' in content:
                fname = f"instances/pdus/{yaml_id}.yaml"
            elif 'transceiver' in yaml_id.lower() or 'sfp' in yaml_id.lower():
                fname = f"instances/transceivers/{yaml_id}.yaml"
            elif isinstance(block, str) and '-' == block.strip()[0]:
                fname = "layouts/layout.yaml"
            else:
                fname = f"instances/{yaml_id}.yaml"
        else:
            # No ID found, might be a layout list
            if block.strip().startswith('- instance:'):
                fname = "layouts/layout.yaml"
            else:
                continue
        
        fpath = run_dir / fname
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(block.strip(), encoding="utf-8")
        file_count += 1
    
    # Score using the harness
    from sd_hwe_bench.scorer import score_task
    score = score_task(
        task_id=task_id,
        agent_output_dir=run_dir,
        expected_deliverables=task.metadata.expected_deliverables,
        rubric_sets=None,
        requirement=task.metadata.requirement,
        rubrics_model=None,
    )
    
    return {
        "model": model_name,
        "task_id": task_id,
        "pass": score.success,
        "overall_score": score.overall_score,
        "layers": {name: {"passed": ls.passed, "total": ls.total, "failed": ls.failed} for name, ls in score.layers.items()},
        "elapsed_s": elapsed,
        "tokens": resp.usage.total_tokens if resp.usage else None,
        "files_written": file_count,
    }

if __name__ == "__main__":
    models = ["deepseek-v4-flash", "deepseek-v4-pro"]
    task_ids = [
        "telecom/comprehensive-001",
        "telecom/connection-design-001",
        "telecom/instance-declare-001",
        "telecom/layout-design-001",
        "telecom/mating-design-001",
    ]
    
    dataset_root = os.getcwd()
    
    all_results = []
    for model in models:
        print(f"\n{'='*60}")
        print(f"Model: {model}")
        print(f"{'='*60}")
        for tid in task_ids:
            print(f"  Task: {tid}...", end=" ", flush=True)
            try:
                result = run_model(model, tid, dataset_root)
                status = "✅ PASS" if result["pass"] else "❌ FAIL"
                print(f"{status} | Score: {result['overall_score']:.0%} | {result['elapsed_s']:.1f}s | {result['tokens']}t")
                all_results.append(result)
            except Exception as e:
                print(f"ERROR: {e}")
                all_results.append({"model": model, "task_id": tid, "error": str(e)})
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for model in models:
        model_results = [r for r in all_results if r.get("model") == model and "error" not in r]
        if model_results:
            passed = sum(1 for r in model_results if r["pass"])
            avg_score = sum(r["overall_score"] for r in model_results) / len(model_results)
            print(f"{model}: Pass@1 = {passed}/{len(model_results)} ({passed/len(model_results):.0%}) | Avg Score = {avg_score:.0%}")
    
    # Save results
    with open("work/baseline_api_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to work/baseline_api_results.json")

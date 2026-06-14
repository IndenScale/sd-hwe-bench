"""CLI entry point for sd-hwe-bench."""

import argparse
import sys
from pathlib import Path

from sd_hwe_bench.harness import AgentConfig, Harness


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sd-hwe-bench",
        description="SD-HWE-Bench: Software-Defined Hardware Engineering Benchmark",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list
    list_parser = subparsers.add_parser("list", help="List available tasks")
    list_parser.add_argument(
        "--dataset", default=".", help="Path to dataset root (default: current dir)"
    )
    list_parser.add_argument("--domain", help="Filter by domain (telecom, datacenter, etc.)")

    # run (legacy: --output or --agent)
    run_parser = subparsers.add_parser("run", help="Run benchmark tasks")
    run_parser.add_argument(
        "task_id", nargs="?", help="Task ID or prefix (e.g. telecom/comprehensive-001)"
    )
    run_parser.add_argument("--dataset", default=".", help="Path to dataset root")
    run_parser.add_argument("--agent", help="Shell command to invoke the agent (legacy)")
    run_parser.add_argument("--output", help="Path to pre-generated agent output directory")
    run_parser.add_argument(
        "--format", choices=["text", "json", "markdown"], default="text"
    )
    run_parser.add_argument("--rubrics", action="store_true", help="Enable LLM rubrics")
    run_parser.add_argument("--rubrics-model", help="LLM model for judging")

    # run-agent (new: driver-based)
    agent_parser = subparsers.add_parser(
        "run-agent", help="Run with agent driver (codex/gemini)"
    )
    agent_parser.add_argument(
        "task_id", nargs="*", help="Task IDs (default: all)"
    )
    agent_parser.add_argument("--dataset", default=".", help="Path to dataset root")
    agent_parser.add_argument(
        "--driver",
        choices=["codex", "gemini"],
        required=True,
        action="append",
        dest="drivers",
        help="Agent driver (repeat for multi-model: --driver codex --driver gemini)",
    )
    agent_parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Model name per driver (repeat, same order as --driver)",
    )
    agent_parser.add_argument(
        "--passes", type=int, default=1, help="Number of runs per task (pass@k)"
    )
    agent_parser.add_argument(
        "--run-dir", help="Directory to store agent outputs (default: temp)"
    )
    agent_parser.add_argument("--rubrics", action="store_true", help="Enable LLM rubrics")
    agent_parser.add_argument("--rubrics-model", help="LLM model for judging")
    agent_parser.add_argument(
        "--format", choices=["text", "json", "markdown"], default="markdown"
    )

    # score (unchanged)
    score_parser = subparsers.add_parser("score", help="Score pre-generated outputs")
    score_parser.add_argument("output_dir", help="Path to agent output directory")
    score_parser.add_argument("--task", required=True, help="Task ID for scoring context")
    score_parser.add_argument("--dataset", default=".", help="Path to dataset root")
    score_parser.add_argument("--rubrics", action="store_true")
    score_parser.add_argument("--rubrics-model", help="LLM model for judging")

    args = parser.parse_args()

    if args.command == "list":
        dataset_root = Path(args.dataset)
        harness = Harness(dataset_root)
        task_ids = harness.dataset.discover()

        if args.domain:
            task_ids = [t for t in task_ids if t.startswith(args.domain)]

        by_domain = harness.dataset.list_by_domain()
        for domain, ids in sorted(by_domain.items()):
            if args.domain and domain != args.domain:
                continue
            print(f"\n[{domain}]（{len(ids)} 个任务）")
            for tid in ids:
                task = harness.dataset.load_task(tid)
                name = task.metadata.name or tid
                desc = task.metadata.description or ""
                print(f"  {tid}")
                print(f"    名称：{name}")
                if desc:
                    print(f"    说明：{desc}")
                print(f"    类型：{task.metadata.task_type.value}")
                print(f"    难度：{task.metadata.difficulty.value}")
                print(f"    插件：{', '.join(task.metadata.plugins)}")
                if task.metadata.rubrics:
                    rubric_names = [r.name for r in task.metadata.rubrics]
                    print(f"    Rubrics: {', '.join(rubric_names)}")

    elif args.command == "run":
        dataset_root = Path(args.dataset)
        harness = Harness(dataset_root)

        if args.task_id:
            all_ids = harness.dataset.discover()
            matched = [
                tid
                for tid in all_ids
                if tid == args.task_id or tid.startswith(args.task_id)
            ]
            if not matched:
                for tid in all_ids:
                    task = harness.dataset.load_task(tid)
                    if args.task_id in task.metadata.name:
                        matched.append(tid)
            task_ids = matched if matched else [args.task_id]
        else:
            task_ids = harness.dataset.discover()

        results = harness.run(
            task_ids=task_ids,
            agent_cmd=args.agent,
            agent_output_dir=Path(args.output) if args.output else None,
            rubrics_enabled=args.rubrics,
            rubrics_model=args.rubrics_model,
        )

        print(harness.report(results, format=args.format))

    elif args.command == "run-agent":
        dataset_root = Path(args.dataset)
        harness = Harness(dataset_root)

        # Resolve task IDs
        if args.task_id:
            task_ids = args.task_id
        else:
            task_ids = harness.dataset.discover()

        # Build agent configs
        drivers = args.drivers
        models = args.models or []
        # Pad models to match drivers
        while len(models) < len(drivers):
            models.append("")  # use driver default

        agent_configs = []
        for driver, model in zip(drivers, models):
            # Apply sensible defaults
            if not model:
                if driver == "codex":
                    model = "deepseek-chat"
                elif driver == "gemini":
                    model = "gemini-2.5-flash"
            agent_configs.append(
                AgentConfig(driver=driver, model=model, passes=args.passes)
            )

        print(f"Running with {len(agent_configs)} agent(s), {len(task_ids)} task(s), "
              f"{args.passes} pass(es) each...")
        print(f"Agents: {', '.join(f'{a.driver}/{a.model}' for a in agent_configs)}")
        print()

        all_results = harness.run_agent(
            task_ids=task_ids,
            agent_configs=agent_configs,
            rubrics_enabled=args.rubrics,
            rubrics_model=args.rubrics_model,
            run_dir=Path(args.run_dir) if args.run_dir else None,
        )

        print(harness.report_multi_model(all_results, format=args.format))

    elif args.command == "score":
        from sd_hwe_bench.scorer import score_task

        dataset_root = Path(args.dataset)
        harness = Harness(dataset_root)
        task = harness.dataset.load_task(args.task)
        score = score_task(
            task_id=args.task,
            agent_output_dir=Path(args.output_dir),
            expected_deliverables=task.metadata.expected_deliverables,
            rubric_sets=task.metadata.rubrics if args.rubrics else None,
            requirement=task.metadata.requirement,
            rubrics_model=args.rubrics_model,
        )
        print(f"任务：{score.task_id}")
        print(f"通过：{'是' if score.success else '否'}")
        print(f"总分：{score.overall_score:.2%}")
        for layer, ls in score.layers.items():
            print(f"  {layer}：{ls.passed}/{ls.total}")
        if score.rubric_results:
            print(
                f"\nRubrics 评分：{score.rubric_score:.2%}"
                if score.rubric_score
                else "\nRubrics:"
            )
            for rr in score.rubric_results:
                status = "✅" if rr.passed else "❌"
                print(
                    f"  [{status}] {rr.rubric_name}: {rr.overall_score:.2f} "
                    f"(threshold: {rr.threshold})"
                )
                for rs in rr.criteria_scores:
                    short_reason = rs.reason[:100].replace("\n", " ")
                    print(f"    - {rs.name}: {rs.score:.2f} — {short_reason}...")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

# Contributing to SD-HWE-Bench

## Task Contribution Workflow

1. **Propose**: Open an issue with a Task Proposal using the template below.
2. **Review**: A domain maintainer reviews the requirement for technical correctness.
3. **Implement**: Create the task directory with scaffold, solution, and expected outputs.
4. **Verify**: Ensure `sd-hwe-bench run` produces consistent scores on the reference solution.
5. **Submit**: Open a PR. The technical committee reviews scoring reproducibility.
6. **Merge**: Task is added to the dataset and included in the next release.

## Task Proposal Template

```markdown
### Domain
[telecom / datacenter / mechanical / hvac / etc.]

### Task Type
[instance-declaration / layout-design / connection-design / mating-design / comprehensive / incremental]

### Natural Language Requirement
[The requirement as the agent would see it — clear, self-contained, all context included]

### Expected Output Structure
- instances/: [what instances should be declared]
- layouts/: [what layouts should be defined]
- mates/: [what mates should be defined]
- connections/: [what connections should be defined]

### Scoring Rules
- L0-L4 rules that apply
- Generator deliverables expected
- Any partial credit considerations
```

## Task Directory Structure

```text
tasks/{domain}/{task-id}/
├── task.yaml              # Task metadata + requirement
├── scaffold/              # Files given to the agent as starting point
│   ├── piki.toml
│   ├── models/            # Available model catalog
│   └── instances/         # Pre-existing instances (for incremental tasks)
├── solution/              # Reference solution (NOT given to agent)
│   ├── instances/
│   ├── layouts/
│   ├── mates/
│   └── connections/
└── expected/              # Expected generator outputs
    └── bom.csv
```

## Domain Plugins

To add a new engineering domain:

1. Create a piki plugin with Family/Model definitions and rules
2. Add at least 10 benchmark tasks covering the domain
3. Propose as a domain maintainer

## Code Style

- Python 3.11+, follow ruff rules
- Task YAML must be valid piki format
- All tasks must include a `task.yaml` with complete metadata

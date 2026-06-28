# Appendix B: Prompt Templates

## B.1 Agent Initial Prompt Structure

The prompt used in the main experiment consists of three components:

1. **System Prompt**: Defines the agent role as "telecom hardware engineering design assistant", specifying the working directory and piki toolchain.
2. **piki Quick Reference**: ~200 lines of embedded ADL syntax and directory convention documentation.
3. **Task Requirement**: The `requirement` field from `task.yaml`.

### B.1.1 piki Quick Reference (Excerpt)

The complete piki quick reference is embedded in `src/sd_hwe_bench/prompts.py` and includes:

- Directory conventions (`instances/devices/`, `instances/ports/`, `layouts/`, etc.)
- Field name trap warnings (`capacity_w` vs `power_capacity_w`, PDU must have `rack_id`)
- YAML templates for each Instance type (device, port, transceiver, fiber, port connection, layout, mate)
- piki command reference (`piki check`, `piki generate`)
- Design spec documentation pointer (reminds agent to read `docs/`)

Reference code: ~860 lines (`src/sd_hwe_bench/prompts.py`).

## B.2 Repair Prompt Structure

The repair loop prompt appends to the initial prompt:

1. **Previous Round DTS Errors**: Categorized by L0-L4 layers, up to 10 errors per layer.
2. **Repair Instruction**: "Fix the engineering files based on the piki check errors above. Only modify files with errors; do not rewrite the entire project."
3. **Termination Conditions**: The agent declares termination by writing marker files: `.done` (repair complete), `.give_up` (abandoned), `.info_gap` (insufficient information), `.no_solution` (unsolvable).

## B.3 Prompt Evolution History

| Version | Change | Reason |
|---------|--------|--------|
| v1 | Initial prompt | POC phase |
| v2 | Added `capacity_w` vs `power_capacity_w` warning | API Actors frequently failed on this field |
| v3 | Added `rack_id` required hint, piki check self-verification instruction | High L2a foreign key error rate |

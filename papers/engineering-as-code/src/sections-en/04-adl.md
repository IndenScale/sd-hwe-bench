# ADL: Assembly Definition Language

ADL is the declarative design representation of Engineering as Code. It is deliberately designed to be text-native: design intent is authored in YAML, verified as code, rather than captured as geometric operations inside a CAD or BIM GUI. ADL is organized around three orthogonal sub-languages, separating "what exists," "how parts couple," and "where they are placed."

## Design Goals

ADL pursues three goals:

1. **Text-Native Representation**. Agents and humans can write and read design intent in plain text, enabling version control, diffing, and programmable generation.
2. **Agent-Oriented Syntax**. Files have explicit identity, references, and deterministic validation. No hidden state dependent on a GUI session exists.
3. **Orthogonality of Identity, Relationships, and Space**. A change in one dimension must not force a rewrite of files in another dimension.

The reference runtime is **piki**, an open-source engine that loads ADL declarations, runs a layered rule engine, and produces downstream deliverables. However, ADL is defined independently of any single tool.

## Part as the Engineering Atom

In ADL, a **Part** is the atomic unit of engineering description. A Part is more than just geometry; it is a semantically complete entity that exposes typed interfaces and participates in explicit relationships. A Part is defined by the following elements:

- **Family** (schema and value-domain constraints)
- **Model** (a concrete realization with default values)
- **Instance** (a deployed entity that can override defaults)
- A set of typed **Interfaces**
- Optional internal geometry, kept hidden unless high-precision analysis is required

The Part abstraction rests on four properties:

1. **Semantic Completeness**. A server Part type is `ServerFamily`, carrying fields such as `height_u`, `tdp_w`, `psu_count`, etc. A pump Part carries `flow_rate` and `head`. Type checking is enforced by plugin-registered pydantic schemas.
2. **Encapsulation**. Internal geometry is hidden; only standardized interfaces are visible to downstream consumers.
3. **Relationship-Built-In**. The role of a server within an assembly is expressed through relationships: it is a `child` in a `rack-mount-19inch` Mate; an optical transceiver is a `child` in an `sfp28-cage` Mate.
4. **Multi-View Projectability**. The same Part can be projected to CAD (USD/glTF), CAE (thermal or structural models), ERP (BOM entries), and lifecycle catalogs without changing its core declaration.

## PDL: Part Definition Language

PDL defines the Part type system at three levels: **Family**, **Model**, and **Instance**.

**Family**. A Family is a pydantic `BaseModel` class that declares the schema and value-domain constraints for a class of Parts. For example, `ServerFamily` requires `id`, `height_u` (1–48), `tdp_w` (>0), and a list of interface specifications. A Family is code, not configuration; it is registered by plugins.

**Model**. A Model provides concrete default values for a Family. An example model file:

```yaml
model: dell-r750
family: ServerFamily
brand: Dell
mpn: PowerEdge R750
height_u: 2
tdp_w: 600
psu_count: 2
```

**Instance**. An Instance is a deployed entity that can override Model defaults:

```yaml
id: SRV-01
model: dell-r750
family: ServerFamily
status: planned
```

At runtime, resolved values are computed as `Model.defaults + Instance.overrides`, then validated against the Family schema. An Instance's identity is derived from its filename (`SRV-01.yaml` → `SRV-01`). A key design decision is that **Instance files contain no layout information**; layout is declared separately in PLL. This separation means the same device can be used in multiple positions across different design alternatives without duplicating its definition.

## PML: Part Mating Language

PML describes relationships between Parts, distinguishing two categories: **Mate** and **Connection**.

**Mate** expresses design coupling: it constrains how two Parts fit or work together. Mates are stored as independent YAML files under `mates/<mate_type>/`. For example:

```yaml
type: rack-mount-19inch
parent: RACK-A02
child: SRV-01
at:
  u_start: 10
  u_span: 2
constrains:
  - field: depth_mm
    operator: "<="
    value_ref: depth_mm
```

The engine validates these constraints at load time. Registered Mate types include `sfp28-cage`, `power-iec-c14-c13`, and `lc-connector`.

**Connection** expresses the flow of signal, energy, or material between two interfaces. A Connection is itself a first-class Instance:

```yaml
id: CONN-ACCESS-SRV01
family: PortConnectionFamily
from_port: ACCESS-SW-01/10GE1/0/1
to_port: SRV-01/eth0
cable_type: OM4-LC-LC
```

The Mate/Connection separation maps to two independent design phases: mechanical or electrical feasibility (Mate) and functional topology correctness (Connection). CAD/BIM systems often merge them into a single object, making it impossible to validate one dimension without involving the other.

## PLL: Part Layout Language

The essence of PLL is **eliminating degrees of freedom** — including the geometric degrees of freedom retained in PML mates for operability, and the full-spatial degrees of freedom of free Parts with no Mate claims in the assembly.

PLL works through a priority chain. (1) For Parts that have a Mate in PML, Parts claimed as a child by a Mate have their pose determined primarily by the PML mating constraint solver; PLL provides parameterized DOF completion — assigning concrete values (`at.u_start`, `at.t`, `at.state`) for the continuous DOFs (translation, rotation, screw) and discrete states (normal/reverse/unplugged) retained in the Mate. The mating solver supports face-mating, axis-alignment, and positional mating paradigms, as well as dynamic collision avoidance for multi-axis translation and discrete state verification. (2) For Parts with no Mate, PLL directly assigns a global pose (absolute coordinates, parent-relative transform, or grid position). (3) In multi-solution scenarios, a layout may carry constraint optimization heuristics (such as minimum energy or shortest cabling defaults) to select among feasible solutions.

PLL further separates layout data from PDL and PML files, ensuring that layout changes (such as swapping a connector type) do not pollute each other, preserving the orthogonality of PDL/PML/PLL.

Known boundaries of the current PLL implementation: the geometric solving precision for continuous DOFs is currently principal-axis approximation and has not yet been extended to 1D continuous-path topologies such as piping/cabling. These are deferred to future solver precision enhancements and external CAE tool handling.

## Orthogonality

The orthogonality of PDL, PML, and PLL is the core design principle of ADL. Each sub-language resides in independent files: PDL in `instances/` and `models/`, PML in `mates/`, and PLL in `layouts/`. Because namespaces are separated, a change in one dimension does not rewrite files in another dimension.

**Incremental Validation**. An Agent can first generate PDL declarations and pass L0–L2 checks, then proceed to PML constraints and PLL spatial rules. This matches the phased error feedback of a compiler.

**Parallel Editing**. A device engineer editing `instances/SRV-01.yaml`, a layout engineer editing `layouts/layout.yaml`, and a mechanical engineer editing `mates/rack-mount/RACK-A02-SRV-01.yaml` can work simultaneously. Git merge conflicts only occur when the same decision dimension is changed.

**Semantic Diff**. A diff in `instances/` means "some device identity or attribute changed"; a diff in `mates/` means "some mating changed"; a diff in `layouts/` means "some position changed." For example:

```diff
- position_u: 10
+ position_u: 12
```

is unambiguously a layout change, while a change to `tdp_w` in `instances/SRV-01.yaml` is an electrical change. This interpretability supports both human code review and automatic reward attribution in RLVR training.

## Comparison with SysML v2 and BIM/IFC

ADL, SysML v2, and BIM/IFC all aim to formalize engineering systems, but they differ fundamentally in assumptions about source-of-truth form, collaboration units, and target users.

| Dimension | SysML v2 [@omg2024sysml] | BIM / IFC [@buildingsmart2023ifc] | ADL (piki) |
|-----------|--------------------------|-----------------------------------|------------|
| Source-of-Truth Form | Model repository | Central model file / IFC exchange | Text files (YAML + TOML) |
| Version Control Unit | Model version | File version | Git line-level history |
| Core Operation Unit | Model element | Geometric object / IFC entity | File (Instance, Mate, Layout) |
| Identity & Space | Mixed in part/occurrence | Geometry as identity | File-level separation of Instance and Layout |
| Inter-Part Relationships | `connection` / `interaction` | Implicit in geometric constraints | Binary `Mate` + `Connection` separation |
| Verification Method | Model checking | Clash detection (post-hoc) | ESA L2–L4a + load-time L0–L1 checks, millisecond-level |
| Target User | Human systems engineer (GUI) | Human designer (GUI) | AI Agent + human engineer (text) |

Table: Comparison of ADL with SysML v2 and BIM/IFC across source-of-truth, versioning, and verification dimensions {#tbl:adl-comparison}

SysML v2 and BIM are primarily modeling environments for human engineers. Their source of truth resides in repositories or large central files that are difficult to diff, branch, and automatically verify. IFC in particular couples identity, geometry, and relationships in a graph that permits multiple equivalent serializations, making line-level version control difficult [@liu2023ifcversion].

ADL inverts these priorities. It is oriented toward Agent-human collaboration, treats text as the sole source of truth, and makes verification a first-class concern. CAD and BIM are not eliminated; they become downstream consumers of ADL declarations, used for visualization, clash detection, and manufacturing.

## Core Syntax Summary

The following grammar summarizes the core constructs of ADL.

```text
Project       ::= piki.toml (ModelFile | InstanceFile | MateFile | LayoutFile)*

ModelFile     ::= "model:" id
                  "family:" FamilyName
                  Field*
                  ("interfaces:" InterfaceSpec*)?

InstanceFile  ::= "id:" id
                  ("family:" FamilyName | "model:" ModelName)
                  Field*
                  ("interfaces:" InterfaceSpec*)?

InterfaceSpec ::= "- id:" id
                  "interface_type:" Type
                  ("direction:" "input" | "output" | "bidirectional")?
                  ("local_transform:" Transform)?

MateFile      ::= "type:" MateType
                  "parent:" Ref
                  "child:" Ref
                  ("at:" Map)?
                  ("constrains:" MateConstraint*)?
                  ("pairings:" InterfacePairing*)?

MateConstraint::= "- field:" Field
                  "operator:" "<=" | ">=" | "<" | ">" | "==" | "!="
                  "value_ref:" FieldOrConstant
                  ("message:" String)?

LayoutFile    ::= LayoutEntry*
LayoutEntry   ::= "- instance:" id
                  (AbsolutePose | RelativePose | GridPose)

AbsolutePose  ::= ("position_x_mm:" num)+
RelativePose  ::= "parent:" id
                  "transform:" Transform
GridPose      ::= "grid_id:" id
                  ("grid_position:" [String, String]
                  | "row_id:" String "bay_index:" Int)

Transform     ::= "translation:" [num, num, num]
                  ("rotation:" [num, num, num])?
                  ("scale:" [num, num, num])?

Ref           ::= id | id "/" interface_id
```

Key semantic constraints not captured by the grammar include: `InstanceFile` must not contain layout fields; `LayoutEntry` must use exactly one of absolute, relative, or grid pose; interface references in `Ref` must resolve to an existing interface.

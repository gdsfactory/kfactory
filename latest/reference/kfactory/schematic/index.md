# schematic

This is still experimental.

Caution is advised when using this, as the API might suddenly change. In order to fix bugs etc.

Schematic (dbu based schematic) class diagram:

DSchematic (um based schematic) class diagram:

## Anchor

Bases: `BaseModel`

Base class for placement anchors.

Subclasses (e.g. `FixedAnchor`, `PortAnchor`) define reference points used to align an instance during placement. Anchors allow to place instances relative to to their bounding box or port positions.

## Array

Bases: `BaseModel`

General 2D array parameterization using two pitch vectors.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `na` | `int` | Repetition count along vector A. This vector needs to have a positive x component. |
| `nb` | `int` | Repetition count along vector B. This vector needs to have a positive y component |
| `pitch_a` | `tuple[Annotated[T, AfterValidator(_gez)], T]` | (dx, dy) pitch for vector A. dx must be \>= 0. |
| `pitch_b` | `tuple[T, Annotated[T, AfterValidator(_gez)]]` | (dx, dy) pitch for vector B. dy must be \>= 0. |

Fields:

- `na` (`int`)
- `nb` (`int`)
- `pitch_a` (`tuple[Annotated[T, AfterValidator(_gez)], T]`)
- `pitch_b` (`tuple[T, Annotated[T, AfterValidator(_gez)]]`)

## Connection

Bases: `SchematicNet[T]`

Hard connection between two ports.

Enforced as {PortRef | PortArrayRef | Port} x {PortRef | PortArrayRef}. Two `Port` objects (cell ports) cannot be connected directly.

Raises:

| Type | Description |
| --- | --- |
| `TypeError` | If connection attempts to join two `Port` objects. |

Fields:

- `net` (`tuple[PortArrayRef | PortRef | Port[T], PortArrayRef | PortRef]`)

Validators:

- `_sort_and_validate_net` → `net`

### from\_list

```
from_list(data: list[Any] | tuple[Any, ...] | dict[str, Any]) -> Connection[T]
```

Parse a Connection from a compact list/tuple/dict representation.

Used for parsing legacy gdsfactory like connections.

Supports array addressing like `( (inst, (ia, ib)), port )`.

## Constraint

Bases: `BaseModel`, `ABC`

Base class for schematic constraints.

Constraints operate in two phases:

1. **enforce** — called by the routing function during the post-process phase, before instances are placed. Receives the `ManhattanRouter` objects and routing context kwargs (e.g. `separation`, `bend90_radius`).
2. **check** — called by `TSchematic.create_cell` after routing is complete. Receives the materialized cell, the schematic, the resolved `Instance` objects for `instance_names`, and the `ManhattanRoute` results for `route_names`.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `route_names` | `list[str]` | Names of the routes this constraint applies to. |
| `instance_names` | `list[str]` | Names of the instances this constraint applies to. |
| `on_failure` | `Literal['error', 'show_error'] \| None` | Behaviour when `check` returns False. `"error"` raises a `ValueError`. `"show_error"` additionally opens the cell in KLayout with an lyrdb marker database. `None` silently ignores failures. |

Fields:

- `route_names` (`list[str]`)
- `instance_names` (`list[str]`)
- `on_failure` (`Literal['error', 'show_error'] | None`)

### check

```
check(c: KCell, schematic: TSchematic[Any], instances: dict[str, Instance], routes: dict[str, list[ManhattanRoute]]) -> bool
```

Return True if the constraint is satisfied after routing.

### enforce

```
enforce(c: KCell, routers: Sequence[ManhattanRouter], route_name: str | None) -> None
```

Enforce the constraint on the routers before placement.

Called by the routing function. `**kwargs` contains routing context such as `separation` and `bend90_radius`.

### lyrdb\_markers

```
lyrdb_markers(c: KCell, schematic: TSchematic[Any], instances: dict[str, Instance], routes: dict[str, list[ManhattanRoute]]) -> rdb.ReportDatabase
```

Build an lyrdb marker database for failing routes.

The default implementation highlights route backbones. Override for constraint-specific visualisation.

## DSchematic

Bases: `TSchematic[um]`

Schematic with a base unit of um for placements.

Fields:

- `name` (`str | None`)
- `instances` (`dict[str, SchematicInstance[T]]`)
- `placements` (`dict[str, Placement[T] | MirrorPlacement]`)
- `nets` (`list[RouteNet[T] | Connection[T] | VirtualConnection[T]]`)
- `routes` (`dict[str, Route[T]]`)
- `ports` (`dict[str, Port[T] | PortArrayRef | PortRef]`)
- `pins` (`dict[str, Pin | PinRef]`)
- `constraints` (`list[Constraint]`)
- `kcl` (`KCLayout`)
- `info` (`dict[str, JSONSerializable]`)
- `unit` (`Literal['um']`)

Validators:

- `val_schematic`
- `assign_backrefs`

### from\_pic\_yml

```
from_pic_yml(data: dict[str, Any], *, strict: bool | None = None) -> DSchematic
```

Validate a pydantic model instance.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `data` | `dict[str, Any]` | The dict to validate. | *required* |
| `strict` | `bool \| None` | Whether to enforce types strictly. | `None` |

## FixedAnchor

Bases: `Anchor`

Anchor an instance to a fixed point of its own bounding box.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `x` | `Literal['left', 'center', 'right'] \| None` | Horizontal anchor relative to the instance bbox ("left", "center", "right"). |
| `y` | `Literal['bottom', 'center', 'top'] \| None` | Vertical anchor relative to the instance bbox ("bottom", "center", "top"). |

Fields:

- `x` (`Literal['left', 'center', 'right'] | None`)
- `y` (`Literal['bottom', 'center', 'top'] | None`)

## MirrorPlacement

Bases: `BaseModel`

Mirror-only placement toggle for an instance.

Mirror only placements are used for connections. This ensures that the schematic can keep track of the relative mirror in case its placement is defined through connections only (i.e. purely relative to neighboring instances).

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `mirror` | `bool` | Whether the instance should be mirrored horizontally. |

Fields:

- `mirror` (`bool`)

## PathLengthMatch

Bases: `Constraint`

Constraint that equalises optical path lengths across a set of routes.

Uses the loop-based path-length matching already built into the optical router. The `enforce` method injects meander loops into the shorter routers so that all routes reach the same length before instances are placed. The `check` method verifies the final `ManhattanRoute` lengths are within `tolerance` of each other.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `loops` | `int` | Number of meander loops to use per route. |
| `loop_side` | `int` | Which side of the route to place the loop on. |
| `loop_position` | `int` | Where along the route to place the loop. |
| `element` | `int` | Index of the straight segment to insert the loop into. |
| `tolerance` | `int` | Maximum allowed length difference after enforcement. |

Fields:

- `route_names` (`list[str]`)
- `instance_names` (`list[str]`)
- `on_failure` (`Literal['error', 'show_error'] | None`)
- `loops` (`int`)
- `loop_side` (`int`)
- `loop_position` (`int`)
- `element` (`int`)
- `tolerance` (`int`)
- `length` (`int | None`)
- `all` (`bool`)

### check

```
check(c: KCell, schematic: TSchematic[Any], instances: dict[str, Instance], routes: dict[str, list[ManhattanRoute]]) -> bool
```

Return True if the constraint is satisfied after routing.

### enforce

```
enforce(c: KCell, routers: Sequence[ManhattanRouter], route_name: str | None) -> None
```

Enforce the constraint on the routers before placement.

Called by the routing function. `**kwargs` contains routing context such as `separation` and `bend90_radius`.

### lyrdb\_markers

```
lyrdb_markers(c: KCell, schematic: TSchematic[Any], instances: dict[str, Instance], routes: dict[str, list[ManhattanRoute]]) -> rdb.ReportDatabase
```

Build an lyrdb marker database for failing routes.

The default implementation highlights route backbones. Override for constraint-specific visualisation.

## Pin

Bases: `BaseModel`

A schematic-level pin grouping one or more schematic-level ports.

The pin will be materialized on the resulting cell at `create_cell` time as a `kfactory.Pin`. The `ports` list references entries in `TSchematic.ports` by name.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `name` | `str` | Pin name (key in `TSchematic.pins`). |
| `ports` | `list[str]` | Names of schematic-level ports that belong to this pin. |
| `pin_type` | `str` | Pin type (default `"DC"`). |
| `info` | `dict[str, JSONSerializable]` | Free-form info attached to the pin. |

Fields:

- `name` (`str`)
- `ports` (`list[str]`)
- `pin_type` (`str`)
- `info` (`dict[str, JSONSerializable]`)

## PinRef

Bases: `BaseModel`

Reference to a pin on a schematic instance.

Produced by `inst.pins["name"]` and used as the `pin` argument of `TSchematic.add_pin` to expose an instance pin as a top-level schematic pin.

Fields:

- `instance` (`str`)
- `pin` (`str`)

## Pins

Indexer for an instance's pins to produce `PinRef`.

> [!NOTE]
>
> **Example**
>
> `inst.pins["dc"]` -\> `PinRef`

### \_\_getitem\_\_

```
__getitem__(key: str) -> PinRef
```

Return a pin reference.

## Placement

Bases: `MirrorPlacement`

Absolute placement and orientation for an instance.

Coordinates may be absolute (`x`, `y`) with relative offsets (`dx`, `dy`), and can reference other instance ports via `PortRef`/`PortArrayRef`. These are still considered absolute placements, but allow relative

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `x` | `int \| T \| PortArrayRef \| PortRef \| AnchorRefX` | x position or a port reference providing the x coordinate. |
| `dx` | `int \| T` | Relative X offset added to `x`. |
| `y` | `int \| T \| PortArrayRef \| PortRef \| AnchorRefY` | y position or a port reference providing the y coordinate. |
| `dy` | `int \| T` | Relative Y offset added to `y`. |
| `orientation` | `float \| PortRef` | Rotation in degrees (0, 90, 180, 270). Can be a reference to another instance's port. |
| `anchor` | `FixedAnchor \| PortAnchor \| None` | Optional `FixedAnchor`/`PortAnchor` to align the instance relative to its bounding box or one of its ports. |
| `mirror` | `bool` | Whether the instance is to be mirrored or not. |

Fields:

- `mirror` (`bool`)
- `x` (`int | T | PortArrayRef | PortRef | AnchorRefX`)
- `dx` (`int | T`)
- `y` (`int | T | PortArrayRef | PortRef | AnchorRefY`)
- `dy` (`int | T`)
- `orientation` (`float | PortRef`)
- `anchor` (`FixedAnchor | PortAnchor | None`)

Validators:

- `_replace_rotation_orientation`

### is\_placeable

```
is_placeable(placed_instances: set[str], placed_ports: set[str]) -> bool
```

Return True if all referenced instances/ports are already placed.

If true, this means this instance can be placed now.

## Port

Bases: `BaseModel`

A schematic-level, placeable port.

This port is on the Schematic's cell's level, i.e. equivalent of `(D)KCell.ports` (or `Component.ports`).

The port position/orientation can be absolute or derived from other placed instance ports via `PortRef`/`PortArrayRef`.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `name` | `str` | Port name (key in schematic). |
| `x` | `T \| PortRef \| AnchorRefX` | x position or `PortRef`. |
| `y` | `T \| PortRef \| AnchorRefY` | y position or `PortRef`. |
| `dx` | `T` | Relative x offset. |
| `dy` | `T` | Relative y offset. |
| `cross_section` | `str` | Name of the cross-section to apply. |
| `orientation` | `Literal[0, 90, 180, 270] \| PortRef` | Orientation in degrees or `PortRef`. |

Methods:

| Name | Description |
| --- | --- |
| `is_placeable` | True if all references resolve to already placed instances. |

Fields:

- `name` (`str`)
- `x` (`T | PortRef | AnchorRefX`)
- `y` (`T | PortRef | AnchorRefY`)
- `dx` (`T`)
- `dy` (`T`)
- `cross_section` (`str`)
- `orientation` (`Literal[0, 90, 180, 270] | PortRef`)

## PortAnchor

Bases: `Anchor`

Anchor an instance using one of its ports.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `port` | `str` | Name of the port on the instance to use as the anchor point. |

Fields:

- `port` (`str`)

## Ports

Indexer for an instance's ports to produce `PortRef`/`PortArrayRef`.

> [!NOTE]
>
> **Example**
>
> `inst.ports["out"]` -\> `PortRef` `inst.ports["out", 1, 0]` -\> `PortArrayRef` (requires instance array)

### \_\_getitem\_\_

```
__getitem__(key: str | tuple[str, int, int]) -> PortRef | PortArrayRef
```

Return a port reference for a (standard or array) port.

## RegularArray

Bases: `BaseModel`

Rectangular array with uniform row/column pitch.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `columns` | `int` | Number of columns (\> 0). |
| `column_pitch` | `T` | Distance between columns. |
| `rows` | `int` | Number of rows (\> 0). |
| `row_pitch` | `T` | Distance between rows. |

Fields:

- `columns` (`int`)
- `column_pitch` (`T`)
- `rows` (`int`)
- `row_pitch` (`T`)

## Route

Bases: `BaseModel`

Bundle of `Link`s routed using a named strategy.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `name` | `str` | Route identifier (key in `(D)Schematic.routes`). |
| `routing_strategy` | `str` | Name of routing function registered on the `Schematic.create_cell` or registered in `KCLayout` if none are given. |
| `settings` | `dict[str, JSONSerializable]` | Keyword arguments forwarded to the routing strategy. |

Fields:

- `name` (`str`)
- `routing_strategy` (`str`)
- `settings` (`dict[str, JSONSerializable]`)

Validators:

- `_parse_nets`

## RouteNet

Bases: `SchematicNet[T]`

Net of two or more ports (refs or schematic ports) belonging to a route.

Fields:

- `net` (`tuple[PortRef | Port[T], ...]`)
- `route` (`str`)

## Schematic

Bases: `TSchematic[dbu]`

Schematic with a base unit of dbu for placements.

Fields:

- `name` (`str | None`)
- `instances` (`dict[str, SchematicInstance[T]]`)
- `placements` (`dict[str, Placement[T] | MirrorPlacement]`)
- `nets` (`list[RouteNet[T] | Connection[T] | VirtualConnection[T]]`)
- `routes` (`dict[str, Route[T]]`)
- `ports` (`dict[str, Port[T] | PortArrayRef | PortRef]`)
- `pins` (`dict[str, Pin | PinRef]`)
- `constraints` (`list[Constraint]`)
- `kcl` (`KCLayout`)
- `info` (`dict[str, JSONSerializable]`)
- `unit` (`Literal['dbu']`)

Validators:

- `val_schematic`
- `assign_backrefs`

### from\_pic\_yml

```
from_pic_yml(data: dict[str, Any], *, strict: bool | None = None) -> Schematic
```

Validate a pydantic model instance.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `data` | `dict[str, Any]` | The dict to validate. | *required* |
| `strict` | `bool \| None` | Whether to enforce types strictly. | `None` |

## SchematicInstance

Bases: `BaseModel`

Instance record within a schematic.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `name` | `str` | Instance name (unique within the schematic). |
| `component` | `str` | Factory (cell function) name used to create the underlying cell. |
| `settings` | `dict[str, JSONSerializable]` | Parameters passed to the factory. |
| `array` | `RegularArray[T] \| Array[T] \| None` | Optional array specification (`RegularArray` or `Array`). |
| `kcl` | `KCLayout` | Layout context (`KCLayout`) to build the instance from. Defaults to default object. |
| `virtual` | `bool` | If True, create a virtual instance (VInstance/ComponentAllAngle). |
| `placement` | `Placement[T] \| MirrorPlacement \| None` | Reference to a placement if the instance has a corresponding one. |

**Properties**

parent\_schematic: `(D)Schematic` owning this instance. ports: Accessing `PortRef`/`PortArrayRef` resulting from this instance.

Methods:

| Name | Description |
| --- | --- |
| `place` | Declare a placement, saved in the schematic owning this instance. |
| `connect` | Create and register a `Connection` from one of my ports. |

Fields:

- `name` (`str`)
- `component` (`str`)
- `settings` (`dict[str, JSONSerializable]`)
- `array` (`RegularArray[T] | Array[T] | None`)
- `kcl` (`KCLayout`)
- `virtual` (`bool`)

Validators:

- `_find_kcl` → `kcl`

### connect

```
connect(port: str | tuple[str, int, int], other: Port[T] | PortRef) -> Connection[T]
```

Connect one of my ports to `other` and register it on the schematic.

### place

```
place(x: T | PortRef | AnchorRefX = 0, y: T | PortRef | AnchorRefY = 0, dx: T = 0, dy: T = 0, orientation: float | PortRef = 0, mirror: bool = False, anchor: FixedAnchorDict | PortAnchorDict | None = None) -> Placement[T]
```

Declare placement/orientation/mirroring for this instance.

Returns:

| Type | Description |
| --- | --- |
| `Placement[T]` | The created `Placement` (also stored under `self.placement` which references |
| `Placement[T]` | `self.parent_schematic.placements`). |

## SchematicNet

Bases: `BaseModel`

Undirected association between ports (refs or schematic ports).

Subclasses may narrow `net`, e.g. to a sorted pair for stable equality and hashing.

Fields:

- `net` (`tuple[PortRef | Port[T], ...]`)

## TSchematic

Bases: `BaseModel`

Schematic of a cell / component.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `name` | `str \| None` | Optional schematic name. |
| `instances` | `dict[str, SchematicInstance[T]]` | Mapping of instance name -\> `SchematicInstance`. |
| `placements` | `dict[str, Placement[T] \| MirrorPlacement]` | Mapping of instance name -\> `Placement`/`MirrorPlacement`. |
| `connections` | `list[Connection[T]]` | List of `Connection`s. |
| `routes` | `dict[str, Route[T]]` | Mapping of route name -\> `Route`. |
| `ports` | `dict[str, Port[T] \| PortArrayRef \| PortRef]` | Mapping of port name -\> `Port`/`PortRef`/`PortArrayRef`. |
| `pins` | `dict[str, Pin \| PinRef]` | Mapping of pin name -\> `Pin`/`PinRef`. Pins are top-level groupings of schematic ports (purely structural — they do not participate in nets/connections). |
| `info` | `dict[str, JSONSerializable]` | dict which will be mapped to `KCell.info` (or any other derivate like Component). |
| `unit` | `Literal['dbu', 'um']` | Base coordinate unit ("dbu" or "um"). Fixed by subclass. |
| `kcl` | `KCLayout` | `KCLayout` context (excluded from model serialization). Needed for referencing and creation of the cell. |

Fields:

- `name` (`str | None`)
- `instances` (`dict[str, SchematicInstance[T]]`)
- `placements` (`dict[str, Placement[T] | MirrorPlacement]`)
- `nets` (`list[RouteNet[T] | Connection[T] | VirtualConnection[T]]`)
- `routes` (`dict[str, Route[T]]`)
- `ports` (`dict[str, Port[T] | PortArrayRef | PortRef]`)
- `pins` (`dict[str, Pin | PinRef]`)
- `constraints` (`list[Constraint]`)
- `kcl` (`KCLayout`)
- `unit` (`Literal['dbu', 'um']`)
- `info` (`dict[str, JSONSerializable]`)

Validators:

- `val_schematic`
- `assign_backrefs`

### add\_constraint

```
add_constraint(constraint: Constraint) -> Constraint
```

Register a constraint on this schematic.

Validates that all `route_names` and `instance_names` referenced by the constraint already exist in the schematic.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `constraint` | `Constraint` | The constraint to add. | *required* |

Returns:

| Type | Description |
| --- | --- |
| `Constraint` | The added constraint (for chaining). |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If any referenced route or instance name is unknown. |

### add\_pin

```
add_pin(name: str | None = None, *, pin: PinRef) -> None
```

Expose an existing instance pin as a schematic top-level pin.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `name` | `str \| None` | Name for the schematic pin; defaults to the underlying pin name. | `None` |
| `pin` | `PinRef` | Pin reference to expose. | *required* |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If a schematic pin with `name` already exists. |

### add\_port

```
add_port(name: str | None = None, *, port: PortRef | PortArrayRef) -> None
```

Expose an existing instance port as a schematic top-level port.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `name` | `str \| None` | Name for the schematic port; defaults to the underlying port name. | `None` |
| `port` | `PortRef \| PortArrayRef` | Port reference to expose. | *required* |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If a schematic port with `name` already exists. |

### add\_route

```
add_route(name: str, nets: Sequence[Sequence[PortRef | Port[T]]], routing_strategy: str, settings: dict[str, JSONSerializable]) -> Route[T]
```

Create a multi-link route bundle.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `name` | `str` | Route identifier (must be unique). | *required* |
| `nets` | `Sequence[Sequence[PortRef \| Port[T]]]` | List of net tuples. Each tuple contains 2 or more ports that belong to the same net. | *required* |
| `routing_strategy` | `str` | Name of the routing strategy function. | *required* |
| `**settings` | `dict[str, JSONSerializable]` | Extra keyword args forwarded to the strategy. | *required* |

Returns:

| Type | Description |
| --- | --- |
| `Route[T]` | The created `Route`. |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If `name` already exists or a net has fewer than 2 ports. |

### code\_str

```
code_str(imports: dict[str, str] = _schematic_default_imports, kfactory_name: str | None = None, ruff_format: bool = True) -> str
```

Generate Python code that reconstructs this schematic.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `imports` | `dict[str, str]` | Mapping of module -\> alias to emit at top of file. | `_schematic_default_imports` |
| `kfactory_name` | `str \| None` | Optional override for the `kfactory` import name. | `None` |
| `ruff_format` | `bool` | If True, format the generated code with `ruff`. | `True` |

Returns:

| Type | Description |
| --- | --- |
| `str` | The generated source code as a string. If `ruff` is unavailable or |
| `str` | fails, the unformatted string is returned. |

### create\_cell

```
create_cell(output_type: type[KC], factories: Mapping[str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]] | None = None, cross_sections: Mapping[str, CrossSection | DCrossSection | AsymmetricCrossSection | DAsymmetricCrossSection] | None = None, routing_strategies: dict[str, Callable[Concatenate[ProtoTKCell[Any], Sequence[Sequence[ProtoPort[Any]]], ...], Any]] | None = None, place_unknown: bool = False, ignore_errors: bool = False) -> KC
```

Materialize the schematic into a `KCell`/`DKCell`/`Component`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `output_type` | `type[KC]` | Cell type to return (e.g., `KCell`, `DKCell`). | *required* |
| `factories` | `Mapping[str, Callable[..., KCell] \| Callable[..., DKCell] \| Callable[..., VKCell]] \| None` | Optional mapping from factory name to callable returning a cell. | `None` |
| `cross_sections` | `Mapping[str, CrossSection \| DCrossSection \| AsymmetricCrossSection \| DAsymmetricCrossSection] \| None` | Optional mapping of cross-section names to definitions. If undefined uses `self.kcl`'s cross sections. | `None` |
| `routing_strategies` | `dict[str, Callable[Concatenate[ProtoTKCell[Any], Sequence[Sequence[ProtoPort[Any]]], ...], Any]] \| None` | Strategy functions keyed by name. If none uses `self.kcl`'s routing strategies | `None` |
| `place_unknown` | `bool` | If True, place otherwise unplaceable instances at (0, 0). This might cause unintended side effects as the schematic is seemingly not fully deterministic, therefore this is disabled by default. | `False` |

Returns:

| Type | Description |
| --- | --- |
| `KC` | A cell of type `output_type` with instances, ports, and routes realized. |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If placement or connection constraints cannot be satisfied. |

### create\_connection

```
create_connection(port1: PortRef | Port[T], port2: PortRef) -> Connection[T]
```

Create and register a connection between two instance ports.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port1` | `PortRef \| Port[T]` | First instance port. | *required* |
| `port2` | `PortRef` | Second instance port. | *required* |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If either referenced instance is unknown. |

Returns:

| Type | Description |
| --- | --- |
| `Connection[T]` | The created `Connection`. |

### create\_inst

```
create_inst(name: str, component: str, settings: dict[str, JSONSerializable] | None = None, array: RegularArray[T] | Array[T] | None = None, placement: Placement[T] | None = None, kcl: KCLayout | None = None, virtual: bool = False) -> SchematicInstance[T]
```

Create a schema instance.

This would be an SREF or AREF in the resulting GDS cell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `name` | `str` | Instance name. In a schematic, each instance must be named, unless created through routing functions. | *required* |
| `component` | `str` | Factory name of the component to instantiate. | *required* |
| `settings` | `dict[str, JSONSerializable] \| None` | Parameters passed to the factory (optional). | `None` |
| `array` | `RegularArray[T] \| Array[T] \| None` | If the instance should create an array instance (AREF), this can be passed here as an `Array` class instance. | `None` |
| `placement` | `Placement[T] \| None` | Optional placement for the instance. Can also be configured with `inst.place(...)` afterwards. | `None` |
| `kcl` | `KCLayout \| None` | Optional `KCLayout` override for this instance. | `None` |

Returns:

| Type | Description |
| --- | --- |
| `SchematicInstance[T]` | Schematic instance representing the args. |

### create\_pin

```
create_pin(name: str, ports: list[str], pin_type: str = 'DC', info: dict[str, JSONSerializable] | None = None) -> Pin
```

Create a schematic-level pin grouping existing schematic ports.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `name` | `str` | Pin name. Must be unique within the schematic. | *required* |
| `ports` | `list[str]` | Names of schematic ports (entries of `self.ports`) that belong to this pin. Each name must already be registered as a schematic port. | *required* |
| `pin_type` | `str` | Pin type (default `"DC"`). | `'DC'` |
| `info` | `dict[str, JSONSerializable] \| None` | Optional info dict attached to the pin. | `None` |

Returns:

| Type | Description |
| --- | --- |
| `Pin` | The created `Pin`, also stored in `self.pins`. |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If a pin with `name` already exists, `ports` is empty, or any port name is not present in `self.ports`. |

### create\_port

```
create_port(name: str, cross_section: str, x: PortRef | PortArrayRef | T, y: PortRef | PortArrayRef | T, dx: T = 0, dy: T = 0, orientation: Literal[0, 90, 180, 270] = 0) -> Port[T]
```

Create a schematic-level, placeable port.

Returns:

| Type | Description |
| --- | --- |
| `Port[T]` | The created `Port`, also stored in `self.ports`. |

### from\_pic\_yml

```
from_pic_yml(data: dict[str, Any], *, strict: bool | None = None) -> TSchematic[T]
```

Load a schematic from a `pic.yml`-style dictionary.

The dictionary is run through :func:`sanitize_pic_yml` before validation so that legacy keys (`connections`, `port`-based placements, etc.) are translated to the current schema.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `data` | `dict[str, Any]` | The dict to validate. | *required* |
| `strict` | `bool \| None` | Whether to enforce types strictly. | `None` |

### netlist

```
netlist(add_defaults: bool = True, factories: dict[str, Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]] | None = None, external_factories: dict[str, dict[str, Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]]] | None = None) -> Netlist
```

Compile the schematic into a `Netlist`.

Includes nets from `connections`, `routes`, and exposed `ports`. Instances are serialized with their `kcl`, component, and settings. The resulting netlist is sorted for stable output.

### place\_port

```
place_port(name: str, cell: KCell, cross_sections: Mapping[str, CrossSection | DCrossSection | AsymmetricCrossSection | DAsymmetricCrossSection], instances: Mapping[str, Instance | VInstance] | None = None) -> BasePort
```

Materialize a schematic-level port on `cell`.

Looks up `self.ports[name]` and dispatches by port type:

- `PortArrayRef` / `PortRef`: forwards an instance port through `cell.add_port` (using `cell.vinsts` for virtual instances).
- `Port[T]`: resolves `(x, y, orientation)` (which may themselves be references), then creates the port via `cell.create_port`.

## read\_schematic

```
read_schematic(file: Path | str, unit: Literal['dbu'] = 'dbu') -> Schematic
```

```
read_schematic(file: Path | str, unit: Literal['um']) -> DSchematic
```

```
read_schematic(file: Path | str, unit: Literal['dbu', 'um'] = 'dbu') -> Schematic | DSchematic
```

Read a schematic from a YAML file.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `file` | `Path \| str` | Path to a YAML file. | *required* |
| `unit` | `Literal['dbu', 'um']` | Target coordinate unit; controls which subclass is constructed. | `'dbu'` |

Returns:

| Type | Description |
| --- | --- |
| `Schematic \| DSchematic` | `Schematic` when `unit="dbu"`, else `DSchematic`. |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If `file` does not exist or is not a file. |

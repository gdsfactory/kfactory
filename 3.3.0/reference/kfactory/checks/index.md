# checks

Standalone connectivity / overlap checks producing klayout ReportDatabases.

Each check answers a single conceptual question and writes its findings to an `rdb.ReportDatabase`. They are composed by `ProtoTKCell.connectivity_check` for the all-in-one pass-or-fail verification, but can be called individually for narrower checks.

## dangling\_ports\_check

```
dangling_ports_check(cell: ProtoTKCell[Any], *, port_types: list[str] | None = None, layers: list[int] | None = None, db: ReportDatabase | None = None, recursive: bool = True, equivalent_ports: dict[str, list[list[str]]] | None = None) -> rdb.ReportDatabase
```

Report dangling instance ports — ports with no matching counterpart.

A dangling port is an instance port at a coord where no other instance port and no cell port appears. Emitted under the `DanglingPort` category.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `ProtoTKCell[Any]` | Cell to verify. | *required* |
| `port_types` | `list[str] \| None` | If given, only ports whose `port_type` is in this list are considered. | `None` |
| `layers` | `list[int] \| None` | If given, only ports on these layers are considered. | `None` |
| `db` | `ReportDatabase \| None` | Reuse an existing report database. A new one is created otherwise. | `None` |
| `recursive` | `bool` | Run the same check on every called child cell as well. | `True` |
| `equivalent_ports` | `dict[str, list[list[str]]] \| None` | Per-cell groups of electrically-equivalent port names (same shape as `Netlist.lvs_equivalent`'s argument). When provided, an instance port is **not** reported as dangling if any other port in its group on the same instance is connected. Typical use is multi-contact pads where `e1`, `e2`, `e3`, `e4` and `pad` are the same electrical node. | `None` |

## instance\_overlap\_check

```
instance_overlap_check(cell: ProtoTKCell[Any], *, layers: list[int] | None = None, db: ReportDatabase | None = None, recursive: bool = True) -> rdb.ReportDatabase
```

Report instance shapes overlapping shapes of other instances.

For each candidate layer, polygons of one instance that overlap polygons of another instance are reported under `InstanceOverlap`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `ProtoTKCell[Any]` | Cell to verify. | *required* |
| `layers` | `list[int] \| None` | If given, only check these layers. | `None` |
| `db` | `ReportDatabase \| None` | Reuse an existing report database. A new one is created otherwise. | `None` |
| `recursive` | `bool` | Run the same check on every called child cell as well. | `True` |

## port\_mismatch\_check

```
port_mismatch_check(cell: ProtoTKCell[Any], *, port_types: list[str] | None = None, layers: list[int] | None = None, db: ReportDatabase | None = None, recursive: bool = True, add_cell_ports: bool = False, check_width: bool = True, check_angle: bool = True, check_type: bool = True, check_port_overlap: bool = True, check_missing_physical_shape: bool = True, check_partial_physical_shape: bool = True, width_mismatch_ignore_layers: list[int | LayerInfo | str] | None = None) -> rdb.ReportDatabase
```

Report port-pair / port-shape mismatches as one logical check.

Aggregates width / angle / port-type mismatches between coincident ports,

> 2-port overlaps, and missing/partial physical layer shapes under the port region. Individual sub-rules can be toggled, but this is one connectivity check producing one pass/fail outcome for the cell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `ProtoTKCell[Any]` | Cell to verify. | *required* |
| `port_types` | `list[str] \| None` | If given, only ports whose `port_type` is in this list are considered. | `None` |
| `layers` | `list[int] \| None` | If given, only ports on these layers are considered. | `None` |
| `db` | `ReportDatabase \| None` | Reuse an existing report database. A new one is created otherwise. | `None` |
| `recursive` | `bool` | Run the same check on every called child cell as well. | `True` |
| `add_cell_ports` | `bool` | Add a `CellPorts` category listing the cell's own (filtered) ports for visual inspection in the report. | `False` |
| `check_width` | `bool` | Emit `WidthMismatch` items. | `True` |
| `check_angle` | `bool` | Emit `AngleMismatch` items. | `True` |
| `check_type` | `bool` | Emit `TypeMismatch` items. | `True` |
| `check_port_overlap` | `bool` | Emit `PortOverlap` items when 2+ instance ports share a coord (and either differ from a cell port or pile up \>2). | `True` |
| `check_missing_physical_shape` | `bool` | Emit `MissingPhysicalShape` items. | `True` |
| `check_partial_physical_shape` | `bool` | Emit `PartialPhysicalShape` items. | `True` |
| `width_mismatch_ignore_layers` | `list[int \| LayerInfo \| str] \| None` | Layers (specified by int index, `kdb.LayerInfo` or name) on which `WidthMismatch` items should be suppressed. Useful for metal stacks where mismatched widths at a via stack are intentional. | `None` |

## shape\_instance\_overlap\_check

```
shape_instance_overlap_check(cell: ProtoTKCell[Any], *, layers: list[int] | None = None, db: ReportDatabase | None = None, recursive: bool = True) -> rdb.ReportDatabase
```

Report top-level cell shapes overlapping with shapes of instances.

Polygons drawn directly into the cell that touch polygons from any of its instances are reported under `CellShapeInstanceOverlap`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `ProtoTKCell[Any]` | Cell to verify. | *required* |
| `layers` | `list[int] \| None` | If given, only check these layers. | `None` |
| `db` | `ReportDatabase \| None` | Reuse an existing report database. A new one is created otherwise. | `None` |
| `recursive` | `bool` | Run the same check on every called child cell as well. | `True` |

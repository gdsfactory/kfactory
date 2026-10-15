# kcell

Core module of kfactory.

Defines the KCell providing klayout Cells with Ports and other convenience functions.

Instance are the kfactory instances used to also acquire ports and other inf from instances.

## BaseKCell

Bases: `BaseModel`, `ABC`

KLayout cell and change its class to KCell.

A KCell is a dynamic proxy for kdb.Cell. It has all the attributes of the official KLayout class. Some attributes have been adjusted to return KCell specific sub classes. If the function is listed here in the docs, they have been adjusted for KFactory specifically. This object will transparently proxy to kdb.Cell. Meaning any attribute not directly defined in this class that are available from the KLayout counter part can still be accessed. The pure KLayout object can be accessed with `kdb_cell`.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `yaml_tag` |  | Tag for yaml serialization. |
| `ports` | `list[BasePort]` | Manages the ports of the cell. |
| `settings` | `KCellSettings` | A dictionary containing settings populated by the cell decorator. |
| `info` | `Info` | Dictionary for storing additional info if necessary. This is not passed to the GDS and therefore not reversible. |
| `d` | `Info` | UMKCell object for easy access to the KCell in um units. |
| `kcl` | `KCLayout` | Library object that is the manager of the KLayout |
| `boundary` | `KCLayout` | Boundary of the cell. |
| `insts` | `KCLayout` | List of instances in the cell. |
| `vinsts` | `VInstances` | List of virtual instances in the cell. |
| `size_info` | `VInstances` | Size information of the cell. |
| `function_name` | `str \| None` | Name of the function that created the cell. |

Fields:

- `ports` (`list[BasePort]`)
- `pins` (`list[BasePin]`)
- `settings` (`KCellSettings`)
- `settings_units` (`KCellSettingsUnits`)
- `vinsts` (`VInstances`)
- `info` (`Info`)
- `kcl` (`KCLayout`)
- `function_name` (`str | None`)
- `basename` (`str | None`)

### locked

```
locked: bool
```

If set the cell shouldn't be modified anymore.

### lock

```
lock() -> None
```

Lock the cell.

## DKCell

Bases: `ProtoTKCell[float]`, `UMGeometricObject`, `DCreatePort`

Cell with floating point units.

### insts

```
insts: DInstances
```

Instances associated with the cell.

### pins

```
pins: DPins
```

Pins associated with the cell.

### ports

```
ports: DPorts
```

Ports associated with the cell.

### \_\_getitem\_\_

```
__getitem__(key: int | str | None) -> DPort
```

Returns port from instance.

### \_\_init\_\_

```
__init__(*, base: TKCell) -> None
```

```
__init__(name: str | None = None, kcl: KCLayout | None = None, kdb_cell: Cell | None = None, ports: Iterable[ProtoPort[Any]] | None = None, info: dict[str, Any] | None = None, settings: dict[str, Any] | None = None, pins: Iterable[ProtoPin[Any]] | None = None) -> None
```

```
__init__(name: str | None = None, kcl: KCLayout | None = None, kdb_cell: Cell | None = None, ports: Iterable[ProtoPort[Any]] | None = None, info: dict[str, Any] | None = None, settings: dict[str, Any] | None = None, pins: Iterable[ProtoPin[Any]] | None = None, *, base: TKCell | None = None) -> None
```

Constructor of KCell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `base` | `TKCell \| None` | If not `None`, a KCell will be created from and existing KLayout Cell | `None` |
| `name` | `str \| None` | Name of the cell, if None will autogenerate name to "Unnamed\_". | `None` |
| `kcl` | `KCLayout \| None` | KCLayout the cell should be attached to. | `None` |
| `kdb_cell` | `Cell \| None` | If not `None`, a KCell will be created from and existing KLayout Cell | `None` |
| `ports` | `Iterable[ProtoPort[Any]] \| None` | Attach an existing Ports object to the KCell, if `None` create an empty one. | `None` |
| `info` | `dict[str, Any] \| None` | Info object to attach to the KCell. | `None` |
| `settings` | `dict[str, Any] \| None` | KCellSettings object to attach to the KCell. | `None` |

### \_\_lshift\_\_

```
__lshift__(cell: AnyTKCell) -> DInstance
```

Convenience function for `DKCell.create_inst`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `AnyTKCell` | The cell to be added as an instance | *required* |

### add\_port

```
add_port(*, port: ProtoPort[Any], name: str | None = None, keep_mirror: bool = False) -> DPort
```

Create a port in the cell.

### create\_pin

```
create_pin(*, name: str, ports: Iterable[ProtoPort[Any]], pin_type: str = 'DC', info: dict[str, MetaData] | None = None) -> DPin
```

Create a pin in the cell.

## DKCells

Bases: `ProtoCells[DKCell]`

## KCell

Bases: `ProtoTKCell[int]`, `DBUGeometricObject`, `ICreatePort`

Cell with integer units.

### insts

```
insts: Instances
```

Instances associated with the cell.

### pins

```
pins: Pins
```

Pins associated with the cell.

### ports

```
ports: Ports
```

Ports associated with the cell.

### \_\_getattr\_\_

```
__getattr__(name: str) -> Any
```

If KCell doesn't have an attribute, look in the KLayout Cell.

### \_\_getitem\_\_

```
__getitem__(key: int | str | None) -> Port
```

Returns port from instance.

### \_\_init\_\_

```
__init__(*, base: TKCell) -> None
```

```
__init__(name: str | None = None, kcl: KCLayout | None = None, kdb_cell: Cell | None = None, ports: Iterable[ProtoPort[Any]] | None = None, info: dict[str, Any] | None = None, settings: dict[str, Any] | None = None, pins: Iterable[ProtoPin[Any]] | None = None) -> None
```

```
__init__(name: str | None = None, kcl: KCLayout | None = None, kdb_cell: Cell | None = None, ports: Iterable[ProtoPort[Any]] | None = None, info: dict[str, Any] | None = None, settings: dict[str, Any] | None = None, pins: Iterable[ProtoPin[Any]] | None = None, *, base: TKCell | None = None) -> None
```

Constructor of KCell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `base` | `TKCell \| None` | If not `None`, a KCell will be created from and existing KLayout Cell | `None` |
| `name` | `str \| None` | Name of the cell, if None will autogenerate name to "Unnamed\_". | `None` |
| `kcl` | `KCLayout \| None` | KCLayout the cell should be attached to. | `None` |
| `kdb_cell` | `Cell \| None` | If not `None`, a KCell will be created from and existing KLayout Cell | `None` |
| `ports` | `Iterable[ProtoPort[Any]] \| None` | Attach an existing Ports object to the KCell, if `None` create an empty one. | `None` |
| `info` | `dict[str, Any] \| None` | Info object to attach to the KCell. | `None` |
| `settings` | `dict[str, Any] \| None` | KCellSettings object to attach to the KCell. | `None` |

### \_\_lshift\_\_

```
__lshift__(cell: AnyTKCell) -> Instance
```

Convenience function for `KCell.create_inst`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `AnyTKCell` | The cell to be added as an instance | *required* |

### add\_port

```
add_port(*, port: ProtoPort[Any], name: str | None = None, keep_mirror: bool = False) -> Port
```

Create a port in the cell.

### create\_pin

```
create_pin(*, name: str, ports: Iterable[ProtoPort[Any]], pin_type: str = 'DC', info: dict[str, MetaData] | None = None) -> Pin
```

Create a pin in the cell.

### from\_yaml

```
from_yaml(constructor: SafeConstructor, node: Any, verbose: bool = False) -> Self
```

Internal function used by the placer to convert yaml to a KCell.

### to\_yaml

```
to_yaml(representer: BaseRepresenter, node: Self) -> MappingNode
```

Internal function to convert the cell to yaml.

## KCells

Bases: `ProtoCells[KCell]`

## ProtoCells

Bases: `Mapping[int, KC_co]`, `ABC`

### \_\_delitem\_\_

```
__delitem__(key: int | str) -> None
```

Delete a cell by key (name or index).

## ProtoKCell

Bases: `GeometricObject[T]`, `ABC`

### factory\_name

```
factory_name: str
```

Return the name under which the factory was registered.

### settings

```
settings: KCellSettings
```

Settings dictionary set by the `kfactory.layout.KCLayout.vcell` decorator.

### settings\_units

```
settings_units: KCellSettingsUnits
```

Dictionary containing the units of the settings.

Set by the @cell decorator.

### \_\_repr\_\_

```
__repr__() -> str
```

Return a string representation of the Cell.

### add\_port

```
add_port(*, port: ProtoPort[Any], name: str | None = None, keep_mirror: bool = False) -> ProtoPort[T]
```

Add an existing port. E.g. from an instance to propagate the port.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port` | `ProtoPort[Any]` | The port to add. | *required* |
| `name` | `str \| None` | Overwrite the name of the port | `None` |
| `keep_mirror` | `bool` | Keep the mirror part of the transformation of a port if `True`, else set the mirror flag to `False`. Ports with an asymmetric cross section always keep their mirror flag. | `False` |

### add\_ports

```
add_ports(ports: Iterable[ProtoPort[Any]], prefix: str = '', suffix: str = '', keep_mirror: bool = False) -> None
```

Add a sequence of ports to the cell.

Can be useful to add all ports of a instance for example.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `ports` | `Iterable[ProtoPort[Any]]` | list/tuple (anything iterable) of ports. | *required* |
| `prefix` | `str` | string to add in front of all the port names | `''` |
| `suffix` | `str` | string to add at the end of all the port names | `''` |
| `keep_mirror` | `bool` | Keep the mirror part of the transformation of a port if `True`, else set the mirror flag to `False`. Ports with an asymmetric cross section always keep their mirror flag. | `False` |

### create\_vinst

```
create_vinst(cell: AnyKCell, *, a: DVector = kdb.DVector(0, 0), b: DVector = kdb.DVector(0, 0), na: int = 1, nb: int = 1) -> VInstance
```

Insert the KCell as a VInstance into a VKCell or KCell.

### layer

```
layer(*args: Any, **kwargs: Any) -> int
```

Get the layer info, convenience for `klayout.db.Layout.layer`.

## ProtoTKCell

Bases: `ProtoKCell[T, TKCell]`, `ABC`

### ghost\_cell

```
ghost_cell: bool
```

Returns a value indicating whether the cell is a "ghost cell".

### instance\_infos

```
instance_infos: dict[str, Info]
```

Per-instance metadata, keyed by explicit instance names.

Access through `inst.info` and rename through `inst.name` to keep the mapping in sync. Instance wrappers are transient; their parent cell owns this mapping and serializes it as native KLayout metadata.

### prop\_id

```
prop_id: int
```

Gets the properties ID associated with the cell.

### \_\_copy\_\_

```
__copy__() -> Self
```

Enables use of `copy.copy` and `copy.deep_copy`.

### \_\_getattr\_\_

```
__getattr__(name: str) -> Any
```

If KCell doesn't have an attribute, look in the KLayout Cell.

### \_\_getitem\_\_

```
__getitem__(key: int | str | None) -> ProtoPort[T]
```

Returns port from instance.

### \_\_hash\_\_

```
__hash__() -> int
```

Hash the KCell.

### add\_port

```
add_port(*, port: ProtoPort[Any], name: str | None = None, keep_mirror: bool = False) -> ProtoPort[Any]
```

Add an existing port. E.g. from an instance to propagate the port.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port` | `ProtoPort[Any]` | The port to add. | *required* |
| `name` | `str \| None` | Overwrite the name of the port | `None` |
| `keep_mirror` | `bool` | Keep the mirror part of the transformation of a port if `True`, else set the mirror flag to `False`. Ports with an asymmetric cross section always keep their mirror flag. | `False` |

### auto\_rename\_ports

```
auto_rename_ports(rename_func: Callable[..., None] | None = None) -> None
```

Rename the ports with the schema angle -\> "NSWE" and sort by x and y.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `rename_func` | `Callable[..., None] \| None` | Function that takes Iterable\[Port\] and renames them. This can of course contain a filter and only rename some of the ports | `None` |

### called\_cells

```
called_cells() -> list[int]
```

Cell indices for every cell transitively instantiated inside this cell.

### cell\_index

```
cell_index() -> int
```

Gets the cell index.

### circuit

```
circuit(l2n: LayoutToNetlist, port_types: Iterable[str] = ('optical',), ignore_unnamed: bool = False, exclude_purposes: list[str] | None = None, allow_width_mismatch: bool = False) -> None
```

Create the (optical type) circuit of the KCell in the given netlist.

This is NOT recommended though.

### connectivity\_check

```
connectivity_check(port_types: list[str] | None = None, layers: list[int] | None = None, db: ReportDatabase | None = None, recursive: bool = True, add_cell_ports: bool = False, check_layer_connectivity: bool = True) -> rdb.ReportDatabase
```

Create a ReportDatabase aggregating all standalone connectivity checks.

This is the all-in-one pass/fail entry point. It runs `port_mismatch_check`, `dangling_ports_check`, and (when `check_layer_connectivity=True`) `instance_overlap_check` + `shape_instance_overlap_check` into a single report. Call those functions directly to run a narrower check.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port_types` | `list[str] \| None` | Filter for certain port types. | `None` |
| `layers` | `list[int] \| None` | Only create the report for certain layers. | `None` |
| `db` | `ReportDatabase \| None` | Use an existing ReportDatabase instead of creating a new one. | `None` |
| `recursive` | `bool` | Create the report not only for this cell, but all child cells as well. | `True` |
| `add_cell_ports` | `bool` | Also add a category "CellPorts" which contains all the cell's selected ports. | `False` |
| `check_layer_connectivity` | `bool` | Run the shape/instance overlap checks. | `True` |

### convert\_to\_static

```
convert_to_static(recursive: bool = True) -> None
```

Convert the KCell to a static cell if it is pdk KCell.

### dbbox

```
dbbox(layer: int | None = None) -> kdb.DBox
```

Bounds in micrometers, including pending virtual instances.

With pending vinsts, warn that bounds may be inaccurate until insert\_vinsts() materializes their geometry.

### dcreate\_inst

```
dcreate_inst(cell: ProtoTKCell[Any] | int, trans: DTrans | DVector | DCplxTrans | None = None, *, a: DVector | None = None, b: DVector | None = None, na: int = 1, nb: int = 1, libcell_as_static: bool = False, static_name_separator: str = '__') -> DInstance
```

Add an instance of another KCell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `ProtoTKCell[Any] \| int` | The cell to be added | *required* |
| `trans` | `DTrans \| DVector \| DCplxTrans \| None` | The integer transformation applied to the reference | `None` |
| `a` | `DVector \| None` | Vector for the array. Needs to be in positive X-direction. Usually this is only a Vector in x-direction. Some foundries won't allow other Vectors. | `None` |
| `b` | `DVector \| None` | Vector for the array. Needs to be in positive Y-direction. Usually this is only a Vector in x-direction. Some foundries won't allow other Vectors. | `None` |
| `na` | `int` | Number of elements in direction of `a` | `1` |
| `nb` | `int` | Number of elements in direction of `b` | `1` |
| `libcell_as_static` | `bool` | If the cell is a Library cell (different KCLayout object), convert it to a static cell. This can cause name collisions that are automatically resolved by appending $1\[..n\] on the newly created cell. | `False` |
| `static_name_separator` | `str` | Stringt to separate the KCLayout name from the cell name when converting library cells (other KCLayout object than the one of this KCell) to static cells (copy them into this KCell's KCLayout). | `'__'` |

Returns:

| Type | Description |
| --- | --- |
| `DInstance` | The created instance |

### delete

```
delete(*, delete_parents: bool = False) -> None
```

Delete the cell.

### draw\_ports

```
draw_ports() -> None
```

Draw all the ports on their respective layer.

### dup

```
dup(new_name: str | None = None) -> Self
```

Copy the full cell.

Sets `_locked` to `False`

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `cell` | `Self` | Exact copy of the current cell. The name will have `$1` as duplicate names are not allowed |

### each\_inst

```
each_inst() -> Iterator[Instance]
```

Iterates over all child instances (which may actually be instance arrays).

### each\_overlapping\_inst

```
each_overlapping_inst(b: Box | DBox) -> Iterator[Instance]
```

Gets the instances overlapping the given rectangle.

### each\_touching\_inst

```
each_touching_inst(b: Box | DBox) -> Iterator[Instance]
```

Gets the instances overlapping the given rectangle.

### flatten

```
flatten(merge: bool = True) -> None
```

Flatten the cell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `merge` | `bool` | Merge the shapes on all layers. | `True` |

### get\_meta\_data

```
get_meta_data(meta_format: Literal['v1', 'v2', 'v3'] | None = None) -> None
```

Read metadata from the KLayout Layout object.

### get\_optical\_nets

```
get_optical_nets(port_types: Sequence[str] = ('optical',), allow_width_mismatch: bool = False) -> list[Net]
```

Extract geometric port-adjacency nets for the given port types.

### ibbox

```
ibbox(layer: int | None = None) -> kdb.Box
```

Bounds in dbu, including approximate bounds of pending virtual instances.

With pending vinsts, warn that bounds may be inaccurate until insert\_vinsts() materializes their geometry.

### icreate\_inst

```
icreate_inst(cell: ProtoTKCell[Any] | int, trans: Trans | Vector | ICplxTrans | None = None, *, a: Vector | None = None, b: Vector | None = None, na: int = 1, nb: int = 1, libcell_as_static: bool = False, static_name_separator: str = '__') -> Instance
```

Add an instance of another KCell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `ProtoTKCell[Any] \| int` | The cell to be added | *required* |
| `trans` | `Trans \| Vector \| ICplxTrans \| None` | The integer transformation applied to the reference | `None` |
| `a` | `Vector \| None` | Vector for the array. Needs to be in positive X-direction. Usually this is only a Vector in x-direction. Some foundries won't allow other Vectors. | `None` |
| `b` | `Vector \| None` | Vector for the array. Needs to be in positive Y-direction. Usually this is only a Vector in x-direction. Some foundries won't allow other Vectors. | `None` |
| `na` | `int` | Number of elements in direction of `a` | `1` |
| `nb` | `int` | Number of elements in direction of `b` | `1` |
| `libcell_as_static` | `bool` | If the cell is a Library cell (different KCLayout object), convert it to a static cell. This can cause name collisions that are automatically resolved by appending $1\[..n\] on the newly created cell. | `False` |
| `static_name_separator` | `str` | Stringt to separate the KCLayout name from the cell name when converting library cells (other KCLayout object than the one of this KCell) to static cells (copy them into this KCell's KCLayout). | `'__'` |

Returns:

| Type | Description |
| --- | --- |
| `Instance` | The created instance |

### insert

```
insert(inst: Instance | CellInstArray | DCellInstArray) -> Instance
```

```
insert(inst: CellInstArray | DCellInstArray, property_id: int) -> Instance
```

```
insert(inst: Instance | CellInstArray | DCellInstArray, property_id: int | None = None) -> Instance
```

Inserts a cell instance given by another reference.

### insert\_vinsts

```
insert_vinsts(recursive: bool = True) -> None
```

Insert all virtual instances and create Instances of real KCells.

### is\_library\_cell

```
is_library_cell() -> bool
```

True if this cell is imported from a klayout library.

### l2n\_elec

```
l2n_elec(mark_port_types: Iterable[str] = ('electrical', 'RF', 'DC'), connectivity: Sequence[tuple[LayerInfo] | tuple[LayerInfo, LayerInfo] | tuple[LayerInfo, LayerInfo, LayerInfo],] | None = None, port_mapping: dict[str, dict[str, str]] | None = None) -> kdb.LayoutToNetlist
```

Generate a LayoutToNetlist object from electrical connectivity.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `mark_port_types` | `Iterable[str]` | The port types to consider for the netlist extraction. | `('electrical', 'RF', 'DC')` |
| `connectivity` | `Sequence[tuple[LayerInfo] \| tuple[LayerInfo, LayerInfo] \| tuple[LayerInfo, LayerInfo, LayerInfo],] \| None` | Define connectivity between layers. These can be single layers (just consider this layer as metal), two layers (two metals which touch each other), or three layers (two metals with a via) | `None` |
| `port_mapping` | `dict[str, dict[str, str]] \| None` | Remap ports of cells to others. This allows to define equivalent ports in the lvs. | `None` |

### l2n\_ports

```
l2n_ports(port_types: Iterable[str] = ('optical',), exclude_purposes: list[str] | None = None, ignore_unnamed: bool = False, allow_width_mismatch: bool = False) -> kdb.LayoutToNetlist
```

Generate a LayoutToNetlist object from the port types.

Uses kfactory ports as a basis for extraction.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port_types` | `Iterable[str]` | The port types to consider for the netlist extraction. | `('optical',)` |
| `exclude_purposes` | `list[str] \| None` | List of purposes, if an instance has that purpose, it will be ignored. | `None` |
| `ignore_unnamed` | `bool` | Ignore any instance without `.name` set. | `False` |

Returns: LayoutToNetlist extracted from instance and cell port positions.

### plot

```
plot(lyrdb: Path | str | None = None, display_type: Literal['image', 'widget'] | None = None) -> None
```

Display cell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `lyrdb` | `Path \| str \| None` | Path to the lyrdb file. | `None` |
| `display_type` | `Literal['image', 'widget'] \| None` | Type of display. Options are "widget" or "image". | `None` |

### read

```
read(filename: str | Path, options: LoadLayoutOptions | None = None, register_cells: bool = False, test_merge: bool = True, update_kcl_meta_data: Literal['overwrite', 'skip', 'drop'] = 'drop', meta_format: Literal['v1', 'v2', 'v3'] | None = None) -> list[int]
```

Read a GDS file into the existing KCell.

Any existing meta info (KCell.info and KCell.settings) will be overwritten if a KCell already exists. Instead of overwriting the cells, they can also be loaded into new cells by using the corresponding cell\_conflict\_resolution.

Layout meta infos are ignored from the loaded layout.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `filename` | `str \| Path` | Path of the GDS file. | *required* |
| `options` | `LoadLayoutOptions \| None` | KLayout options to load from the GDS. Can determine how merge conflicts are handled for example. See https://www.klayout.de/doc-qt5/code/class\_LoadLayoutOptions.html | `None` |
| `register_cells` | `bool` | If `True` create KCells for all cells in the GDS. | `False` |
| `test_merge` | `bool` | Check the layouts first whether they are compatible (no differences). | `True` |
| `update_kcl_meta_data` | `Literal['overwrite', 'skip', 'drop']` | How to treat loaded KCLayout info. overwrite: overwrite existing info entries skip: keep existing info values drop: don't add any new info | `'drop'` |
| `meta_format` | `Literal['v1', 'v2', 'v3'] \| None` | How to read KCell metainfo from the gds. `v1` had stored port transformations as strings, never versions have them stored and loaded in their native KLayout formats. | `None` |

### set\_meta\_data

```
set_meta_data() -> None
```

Set metadata of the Cell.

Currently, ports, settings and info will be set.

### show

```
show(lyrdb: ReportDatabase | Path | str | None = None, l2n: LayoutToNetlist | Path | str | None = None, keep_position: bool = True, save_options: SaveLayoutOptions | None = None, use_libraries: bool = True, library_save_options: SaveLayoutOptions | None = None, technology: str | None = None, markers: list[tuple[DShapeLike, MarkerConfig]] | None = None) -> None
```

Stream the gds to klive.

Will create a temporary file of the gds and load it in KLayout via klive

### to\_dtype

```
to_dtype() -> DKCell
```

Convert the kcell to a um kcell.

### to\_itype

```
to_itype() -> KCell
```

Convert the kcell to a dbu kcell.

### transform

```
transform(inst: Instance, trans: Trans | DTrans | ICplxTrans | DCplxTrans, /, *, transform_ports: bool = True) -> Instance
```

```
transform(trans: Trans | DTrans | ICplxTrans | DCplxTrans, /, *, transform_ports: bool = True) -> None
```

```
transform(inst_or_trans: Instance | Trans | DTrans | ICplxTrans | DCplxTrans, trans: Trans | DTrans | ICplxTrans | DCplxTrans | None = None, /, *, transform_ports: bool = True) -> Instance | None
```

Transforms the instance or cell with the transformation given.

### write

```
write(filename: str | Path, save_options: SaveLayoutOptions | None = None, convert_external_cells: bool = False, set_meta_data: bool = True, autoformat_from_file_extension: bool = True, deduplicate_cell_names: bool = False, clear_existing_meta: bool = True) -> None
```

Write a KCell to a GDS.

See KCLayout.write for more info.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `deduplicate_cell_names` | `bool` | If True, auto-rename duplicate cells with `$1`, `$2`, … suffixes before writing. If False (the default), raise :class:`~kfactory.exceptions.DuplicateCellNameError` when duplicates are detected. | `False` |

### write\_bytes

```
write_bytes(save_options: SaveLayoutOptions | None = None, convert_external_cells: bool = False, set_meta_data: bool = True, deduplicate_cell_names: bool = False, clear_existing_meta: bool = True) -> bytes
```

Write a KCell to a binary format as oasis.

See KCLayout.write for more info.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `deduplicate_cell_names` | `bool` | If True, auto-rename duplicate cells with `$1`, `$2`, … suffixes before writing. If False (the default), raise :class:`~kfactory.exceptions.DuplicateCellNameError` when duplicates are detected. | `False` |

## TKCell

Bases: `BaseKCell`

KLayout cell and change its class to KCell.

A KCell is a dynamic proxy for kdb.Cell. It has all the attributes of the official KLayout class. Some attributes have been adjusted to return KCell specific sub classes. If the function is listed here in the docs, they have been adjusted for KFactory specifically. This object will transparently proxy to kdb.Cell. Meaning any attribute not directly defined in this class that are available from the KLayout counter part can still be accessed. The pure KLayout object can be accessed with `kdb_cell`.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `kdb_cell` | `Cell` | Pure KLayout cell object. |
| `locked` | `bool` | If set the cell shouldn't be modified anymore. |
| `function_name` | `str \| None` | Name of the function that created the cell. |
| `virtual` | `bool` | If true, the Cell came from a VKCell. |
| `vtrans` | `DCplxTrans \| None` | If not None, the cell came from an instance which cannot be snapped lossless to the grid. This happens if a was used and the VInstance cannot be mapped to the grid without information loss. |

Fields:

- `ports` (`list[BasePort]`)
- `pins` (`list[BasePin]`)
- `settings` (`KCellSettings`)
- `settings_units` (`KCellSettingsUnits`)
- `vinsts` (`VInstances`)
- `info` (`Info`)
- `kcl` (`KCLayout`)
- `function_name` (`str | None`)
- `basename` (`str | None`)
- `kdb_cell` (`Cell`)
- `boundary` (`DPolygon | None`)
- `lvs_equivalent_ports` (`list[list[str]] | None`)
- `virtual` (`bool`)
- `vtrans` (`DCplxTrans | None`)
- `instance_infos` (`dict[str, Info]`)

### locked

```
locked: bool
```

If set the cell shouldn't be modified anymore.

### \_\_getattr\_\_

```
__getattr__(name: str) -> Any
```

If KCell doesn't have an attribute, look in the KLayout Cell.

## TVCell

Bases: `BaseKCell`

Fields:

- `ports` (`list[BasePort]`)
- `pins` (`list[BasePin]`)
- `settings` (`KCellSettings`)
- `settings_units` (`KCellSettingsUnits`)
- `vinsts` (`VInstances`)
- `info` (`Info`)
- `kcl` (`KCLayout`)
- `function_name` (`str | None`)
- `basename` (`str | None`)
- `shapes` (`dict[int, VShapes]`)

### locked

```
locked: bool
```

If set the cell shouldn't be modified anymore.

## VKCell

Bases: `ProtoKCell[float, TVCell]`, `UMGeometricObject`, `DCreatePort`

Emulate `[klayout.db.Cell][klayout.db.Cell]`.

### pins

```
pins: DPins
```

Ports associated with the cell.

### ports

```
ports: DPorts
```

Ports associated with the cell.

### \_\_getitem\_\_

```
__getitem__(key: int | str | None) -> DPort
```

Returns port from instance.

### \_\_repr\_\_

```
__repr__() -> str
```

Return a string representation of the Cell.

### add\_port

```
add_port(*, port: ProtoPort[Any], name: str | None = None, keep_mirror: bool = False) -> DPort
```

Proxy for Ports.create\_port.

### auto\_rename\_ports

```
auto_rename_ports(rename_func: Callable[..., None] | None = None) -> None
```

Rename the ports with the schema angle -\> "NSWE" and sort by x and y.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `rename_func` | `Callable[..., None] \| None` | Function that takes Iterable\[Port\] and renames them. This can of course contain a filter and only rename some of the ports | `None` |

### draw\_ports

```
draw_ports() -> None
```

Draw all the ports on their respective layer.

### dup

```
dup(new_name: str | None = None) -> Self
```

Copy the full cell.

Removes lock if the original cell was locked.

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `cell` | `Self` | Exact copy of the current cell. The name will have `$1` as duplicate names are not allowed |

### l2n

```
l2n(port_types: Iterable[str] = ('optical',)) -> tuple[KCell, kdb.LayoutToNetlist]
```

Generate a LayoutToNetlist object from the port types.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port_types` | `Iterable[str]` | The port types to consider for the netlist extraction. | `('optical',)` |

### plot

```
plot() -> None
```

Display cell.

Usage: Pass the vkcell variable as an argument in the cell at the end

### show

```
show(lyrdb: ReportDatabase | Path | str | None = None, l2n: LayoutToNetlist | Path | str | None = None, keep_position: bool = True, save_options: SaveLayoutOptions | None = None, use_libraries: bool = True, library_save_options: SaveLayoutOptions | None = None, technology: str | None = None) -> None
```

Stream the gds to klive.

Will create a temporary file of the gds and load it in KLayout via klive

### write

```
write(filename: str | Path, save_options: SaveLayoutOptions | None = None, convert_external_cells: bool = False, set_meta_data: bool = True, autoformat_from_file_extension: bool = True, deduplicate_cell_names: bool = False, clear_existing_meta: bool = True) -> None
```

Write a KCell to a GDS.

See KCLayout.write for more info.

## get\_cells

```
get_cells(modules: Iterable[ModuleType], verbose: bool = False) -> dict[str, Callable[..., KCell]]
```

Returns KCells (KCell functions) from a module or list of modules.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `modules` | `Iterable[ModuleType]` | module or iterable of modules. | *required* |
| `verbose` | `bool` | prints in case any errors occur. | `False` |

## show

```
show(layout: KCLayout | AnyKCell | Path | str, lyrdb: ReportDatabase | Path | str | None = None, l2n: LayoutToNetlist | Path | str | None = None, technology: str | None = None, keep_position: bool = True, save_options: SaveLayoutOptions | None = None, use_libraries: bool = True, library_save_options: SaveLayoutOptions | None = None, set_technology: bool = True, file_format: Literal['oas', 'gds'] = 'oas', markers: list[tuple[DShapeLike, MarkerConfig]] | None = None) -> None
```

Show GDS in klayout.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `layout` | `KCLayout \| AnyKCell \| Path \| str` | The object to show. This can be a KCell, KCLayout, Path, or string. | *required* |
| `lyrdb` | `ReportDatabase \| Path \| str \| None` | A KLayout report database (.lyrdb/.rdb) file or object to show with the layout. | `None` |
| `l2n` | `LayoutToNetlist \| Path \| str \| None` | A KLayout LayoutToNetlist object or file (.l2n) to show with the layout. | `None` |
| `keep_position` | `bool` | Keep the current KLayout position if a view is already open. | `True` |
| `save_options` | `SaveLayoutOptions \| None` | Custom options for saving the gds/oas. | `None` |
| `use_libraries` | `bool` | Save other KCLayouts as libraries on write. | `True` |
| `library_save_options` | `SaveLayoutOptions \| None` | Specific saving options for Cells which are in a library and not the main KCLayout. | `None` |
| `markers` | `list[tuple[DShapeLike, MarkerConfig]] \| None` | lay.Marker list | `None` |

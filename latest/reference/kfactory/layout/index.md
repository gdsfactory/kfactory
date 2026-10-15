# layout

## cell

```
cell = kcl.cell
```

Default kcl @cell decorator.

## kcl

```
kcl: KCLayout = KCLayout('DEFAULT')
```

Default library object.

Any KCell uses this object unless another one is specified in the constructor.

## vcell

```
vcell = kcl.vcell
```

Default kcl @vcell decorator.

## Constants

Bases: `BaseModel`

Constant Model class.

Config:

- `arbitrary_types_allowed`: `True`

## ExtrudeConfig

Bases: `BaseModel`

Default extrusion settings of a cross section.

Registered per cross section with `KCLayout.set_extrude_config`. Per-strip settings are keyed by the strip's index in the cross section's `get_sections()` (main strip first).

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `ports` | `dict[int, tuple[str \| None, str \| None, str]] \| None` | `(start_name, end_name, port_type)` per strip. `None` leaves the port naming to the extruder's convention, `{}` creates no ports. |
| `insets` | `dict[int, tuple[dbu, dbu]]` | `(start, end)` distances by which a strip is shortened at the path ends \[dbu\]. Negative values extend the strip along the end tangents. |
| `simplify` | `dbu \| dict[int, dbu] \| None` | Polygon simplification tolerance for all strips, or per strip \[dbu\]. |
| `hidden` | `frozenset[int]` | Strips that are not drawn. |
| `add_bbox` | `bool` | Whether to draw the cross section's bbox sections. |

Fields:

- `ports` (`dict[int, tuple[str | None, str | None, str]] | None`)
- `insets` (`dict[int, tuple[dbu, dbu]]`)
- `simplify` (`dbu | dict[int, dbu] | None`)
- `hidden` (`frozenset[int]`)
- `add_bbox` (`bool`)

Validators:

- `_check_values`

### section\_indices

```
section_indices() -> set[int]
```

Strip indices referenced by this config.

## Factories

Bases: `Mapping[str, F]`

### locked

```
locked: bool
```

Whether this collection rejects new factories via `add`.

### lock

```
lock() -> None
```

Prevent further additions through `add`. This is irreversible.

## KCLayout

Bases: `BaseModel`

Small extension to the klayout.db.Layout.

It adds tracking for the KCell objects instead of only the `klayout.db.Cell` objects. Additionally it allows creation and registration through `create_cell`

All attributes of `klayout.db.Layout` are transparently accessible

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `editable` |  | Whether the layout should be opened in editable mode (default: True) |
| `rename_function` | `Callable[..., None]` | function that takes an iterable object of ports and renames them |
| `extrude_configs` | `dict[str, ExtrudeConfig]` | Default extrusion settings per cross section, keyed by the cross section's `auto_name()`. Use `set_extrude_config` and `get_extrude_config` to access them. |

Fields:

- `name` (`str`)
- `layout` (`Layout`)
- `layer_enclosures` (`LayerEnclosureModel`)
- `cross_sections` (`CrossSectionModel`)
- `extrude_configs` (`dict[str, ExtrudeConfig]`)
- `enclosure` (`KCellEnclosure`)
- `library` (`Library`)
- `factories` (`Factories[WrappedKCellFunc[Any, ProtoTKCell[Any]]]`)
- `virtual_factories` (`Factories[WrappedVKCellFunc[Any, VKCell]]`)
- `generic_factories` (`dict[str, Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]]`)
- `tkcells` (`dict[int, TKCell]`)
- `infos` (`LayerInfos`)
- `layer_stack` (`LayerStack`)
- `netlist_layer_mapping` (`dict[LayerEnum | int, LayerEnum | int]`)
- `sparameters_path` (`Path | str | None`)
- `interconnect_cml_path` (`Path | str | None`)
- `constants` (`Constants`)
- `rename_function` (`Callable[..., None]`)
- `_registered_functions` (`dict[int, Callable[..., TKCell]]`)
- `thread_lock` (`RLock`)
- `info` (`Info`)
- `settings` (`KCellSettings`)
- `decorators` (`Decorators`)
- `default_cell_output_type` (`type[KCell | DKCell]`)
- `default_vcell_output_type` (`type[VKCell]`)
- `connectivity` (`list[tuple[LayerInfo, LayerInfo] | tuple[LayerInfo, LayerInfo, LayerInfo]]`)
- `routing_strategies` (`dict[str, Callable[Concatenate[ProtoTKCell[Any], Sequence[Sequence[ProtoPort[Any]]], ...], list[ManhattanRoute]]]`)
- `technology_file` (`Path | None`)

Validators:

- `_validate_infos` → `infos`

### dbu

```
dbu: float
```

Get the database unit.

### dkcells

```
dkcells: DKCells
```

DKCells is a mapping of int to DKCell.

### factories\_locked

```
factories_locked: bool
```

Whether both the real and virtual factory collections are locked.

### kcells

```
kcells: KCells
```

KCells is a mapping of int to KCell.

### layers

```
layers: type[LayerEnum]
```

LayerEnum derived from `infos`. Cached; invalidated when `infos` is set.

### \_\_getattr\_\_

```
__getattr__(name: str) -> Any
```

If KCLayout doesn't have an attribute, look in the KLayout Cell.

### \_\_getitem\_\_

```
__getitem__(obj: str | int) -> KCell
```

Retrieve a cell by name(str) or index(int).

**Attrs**

obj: name of cell or cell\_index

### \_\_init\_\_

```
__init__(name: str, layer_enclosures: dict[str, LayerEnclosure] | LayerEnclosureModel | None = None, enclosure: KCellEnclosure | None = None, infos: type[LayerInfos] | None = None, sparameters_path: Path | str | None = None, interconnect_cml_path: Path | str | None = None, layer_stack: LayerStack | None = None, constants: type[Constants] | None = None, base_kcl: KCLayout | None = None, port_rename_function: Callable[..., None] = rename_clockwise_multi, copy_base_kcl_layers: bool = True, info: dict[str, MetaData] | None = None, default_cell_output_type: type[KCell | DKCell] = KCell, connectivity: Sequence[tuple[LayerInfo, LayerInfo] | tuple[LayerInfo, LayerInfo, LayerInfo]] | None = None, technology_file: Path | str | None = None) -> None
```

Create a new KCLayout (PDK). Can be based on an old KCLayout.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `name` | `str` | Name of the PDK. | *required* |
| `layer_enclosures` | `dict[str, LayerEnclosure] \| LayerEnclosureModel \| None` | Additional KCellEnclosures that should be available except the KCellEnclosure | `None` |
| `enclosure` | `KCellEnclosure \| None` | The standard KCellEnclosure of the PDK. | `None` |
| `infos` | `type[LayerInfos] \| None` | A LayerInfos describing the layerstack of the PDK. | `None` |
| `sparameters_path` | `Path \| str \| None` | Path to the sparameters config file. | `None` |
| `interconnect_cml_path` | `Path \| str \| None` | Path to the interconnect file. | `None` |
| `layer_stack` | `LayerStack \| None` | maps name to layer numbers, thickness, zmin, sidewall\_angle. if can also contain material properties (refractive index, nonlinear coefficient, sheet resistance ...). | `None` |
| `constants` | `type[Constants] \| None` | A model containing all the constants related to the PDK. | `None` |
| `base_kcl` | `KCLayout \| None` | an optional basis of the PDK. | `None` |
| `port_rename_function` | `Callable[..., None]` | Which function to use for renaming kcell ports. | `rename_clockwise_multi` |
| `copy_base_kcl_layers` | `bool` | Copy all known layers from the base if any are defined. | `True` |
| `info` | `dict[str, MetaData] \| None` | Additional metadata to put into info attribute. | `None` |

### \_\_setattr\_\_

```
__setattr__(name: str, value: Any) -> None
```

Use a custom setter to automatically set attributes.

If the attribute is not in this object, set it on the Layout object.

### assign

```
assign(layout: Layout) -> None
```

Assign a new Layout object to the KCLayout object.

### cell

```
cell(_func: Callable[KCellParams, KC]) -> Callable[KCellParams, KC]
```

```
cell(*, set_settings: bool = ..., set_name: bool = ..., check_ports: bool = ..., check_pins: bool = ..., check_instances: CheckInstances | None = ..., check_unnamed_cells: CheckUnnamedCells = ..., snap_ports: bool = ..., add_port_layers: bool = ..., cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ..., basename: str | None = ..., drop_params: list[str] = ..., register_factory: bool = ..., overwrite_existing: bool | None = ..., layout_cache: bool | None = ..., info: dict[str, MetaData] | None = ..., debug_names: bool | None = ..., tags: list[str] | None = ..., lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None, schematic_function: Callable[KCellParams, TSchematic[Any]]) -> Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]
```

```
cell(*, set_settings: bool = ..., set_name: bool = ..., check_ports: bool = ..., check_pins: bool = ..., check_instances: CheckInstances | None = ..., check_unnamed_cells: CheckUnnamedCells = ..., snap_ports: bool = ..., add_port_layers: bool = ..., cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ..., basename: str | None = ..., drop_params: list[str] = ..., register_factory: bool = ..., overwrite_existing: bool | None = ..., layout_cache: bool | None = ..., info: dict[str, MetaData] | None = ..., debug_names: bool | None = ..., tags: list[str] | None = ..., lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None, schematic_function: None = None) -> Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]
```

```
cell(*, set_settings: bool = ..., set_name: bool = ..., check_ports: bool = ..., check_pins: bool = ..., check_instances: CheckInstances | None = ..., check_unnamed_cells: CheckUnnamedCells = ..., snap_ports: bool = ..., add_port_layers: bool = ..., cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ..., basename: str | None = ..., drop_params: list[str] = ..., register_factory: bool = ..., overwrite_existing: bool | None = ..., layout_cache: bool | None = ..., info: dict[str, MetaData] | None = ..., post_process: Iterable[Callable[[KC], None]], debug_names: bool | None = ..., tags: list[str] | None = ..., lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None, schematic_function: Callable[KCellParams, TSchematic[Any]]) -> Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]
```

```
cell(*, set_settings: bool = ..., set_name: bool = ..., check_ports: bool = ..., check_pins: bool = ..., check_instances: CheckInstances | None = ..., check_unnamed_cells: CheckUnnamedCells = ..., snap_ports: bool = ..., add_port_layers: bool = ..., cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ..., basename: str | None = ..., drop_params: list[str] = ..., register_factory: bool = ..., overwrite_existing: bool | None = ..., layout_cache: bool | None = ..., info: dict[str, MetaData] | None = ..., post_process: Iterable[Callable[[KC], None]], debug_names: bool | None = ..., tags: list[str] | None = ..., lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None, schematic_function: None = None) -> Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]
```

```
cell(*, output_type: type[KC], set_settings: bool = ..., set_name: bool = ..., check_ports: bool = ..., check_pins: bool = ..., check_instances: CheckInstances | None = ..., check_unnamed_cells: CheckUnnamedCells = ..., snap_ports: bool = ..., add_port_layers: bool = ..., cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ..., basename: str | None = ..., drop_params: list[str] = ..., register_factory: bool = ..., overwrite_existing: bool | None = ..., layout_cache: bool | None = ..., info: dict[str, MetaData] | None = ..., post_process: Iterable[Callable[[KC], None]], debug_names: bool | None = ..., tags: list[str] | None = ..., lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None, schematic_function: Callable[KCellParams, TSchematic[Any]]) -> Callable[[Callable[KCellParams, ProtoTKCell[Any]]], Callable[KCellParams, KC]]
```

```
cell(*, output_type: type[KC], set_settings: bool = ..., set_name: bool = ..., check_ports: bool = ..., check_pins: bool = ..., check_instances: CheckInstances | None = ..., check_unnamed_cells: CheckUnnamedCells = ..., snap_ports: bool = ..., add_port_layers: bool = ..., cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ..., basename: str | None = ..., drop_params: list[str] = ..., register_factory: bool = ..., overwrite_existing: bool | None = ..., layout_cache: bool | None = ..., info: dict[str, MetaData] | None = ..., post_process: Iterable[Callable[[KC], None]], debug_names: bool | None = ..., tags: list[str] | None = ..., lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None, schematic_function: None = None) -> Callable[[Callable[KCellParams, ProtoTKCell[Any]]], Callable[KCellParams, KC]]
```

```
cell(*, output_type: type[KC], set_settings: bool = ..., set_name: bool = ..., check_ports: bool = ..., check_pins: bool = ..., check_instances: CheckInstances | None = ..., check_unnamed_cells: CheckUnnamedCells = ..., snap_ports: bool = ..., add_port_layers: bool = ..., cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ..., basename: str | None = ..., drop_params: list[str] = ..., register_factory: bool = ..., overwrite_existing: bool | None = ..., layout_cache: bool | None = ..., info: dict[str, MetaData] | None = ..., debug_names: bool | None = ..., tags: list[str] | None = ..., lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None, schematic_function: Callable[KCellParams, TSchematic[Any]]) -> Callable[[Callable[KCellParams, ProtoTKCell[Any]]], Callable[KCellParams, KC]]
```

```
cell(*, output_type: type[KC], set_settings: bool = ..., set_name: bool = ..., check_ports: bool = ..., check_pins: bool = ..., check_instances: CheckInstances | None = ..., check_unnamed_cells: CheckUnnamedCells = ..., snap_ports: bool = ..., add_port_layers: bool = ..., cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ..., basename: str | None = ..., drop_params: list[str] = ..., register_factory: bool = ..., overwrite_existing: bool | None = ..., layout_cache: bool | None = ..., info: dict[str, MetaData] | None = ..., debug_names: bool | None = ..., tags: list[str] | None = ..., lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None, schematic_function: None = None) -> Callable[[Callable[KCellParams, ProtoTKCell[Any]]], Callable[KCellParams, KC]]
```

```
cell(_func: Callable[KCellParams, ProtoTKCell[Any]] | None = None, /, *, output_type: type[KC] | None = None, set_settings: bool = True, set_name: bool = True, check_ports: bool = True, check_pins: bool = True, check_instances: CheckInstances | None = None, check_unnamed_cells: CheckUnnamedCells | None = None, snap_ports: bool = True, add_port_layers: bool = True, cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None, basename: str | None = None, drop_params: Sequence[str] = ('self', 'cls'), register_factory: bool = True, overwrite_existing: bool | None = None, layout_cache: bool | None = None, info: dict[str, MetaData] | None = None, post_process: Iterable[Callable[[KC], None]] | None = None, debug_names: bool | None = None, tags: list[str] | None = None, lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None, schematic_function: Callable[KCellParams, TSchematic[Any]] | None = None) -> Callable[KCellParams, KC] | Callable[[Callable[KCellParams, ProtoTKCell[Any]]], Callable[KCellParams, KC]]
```

Decorator to cache and auto name the cell.

This will use `functools.cache` to cache the function call. Additionally, if enabled this will set the name and from the args/kwargs of the function and also paste them into a settings dictionary of the KCell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `output_type` | `type[KC] \| None` | The type of the cell to return. | `None` |
| `set_settings` | `bool` | Copy the args &amp; kwargs into the settings dictionary | `True` |
| `set_name` | `bool` | Auto create the name of the cell to the functionname plus a string created from the args/kwargs | `True` |
| `check_ports` | `bool` | Check uniqueness of port names. | `True` |
| `check_pins` | `bool` | Check uniqueness of pin names. | `True` |
| `check_instances` | `CheckInstances \| None` | Check for any complex instances. A complex instance is a an instance that has a magnification != 1 or non-90° rotation. Depending on the setting, an error is raised, the cell is flattened, a VInstance is created instead of a regular instance, or they are ignored. | `None` |
| `check_unnamed_cells` | `CheckUnnamedCells \| None` | Check for unnamed child cells (matching `Unnamed_\d+`). `"error"` raises, `"warning"` logs a warning, `"ignore"` skips the check. | `None` |
| `snap_ports` | `bool` | Snap the centers of the ports onto the grid (only x/y, not angle). | `True` |
| `add_port_layers` | `bool` | Add special layers of `KCLayout.netlist_layer_mapping` to the ports if the port layer is in the mapping. | `True` |
| `cache` | `Cache[Hashable, Any] \| dict[Hashable, Any] \| None` | Provide a user defined cache instead of an internal one. This can be used for example to clear the cache. expensive if the cell is called often). | `None` |
| `basename` | `str \| None` | Overwrite the name normally inferred from the function or class name. | `None` |
| `drop_params` | `Sequence[str]` | Drop these parameters before writing the settings | `('self', 'cls')` |
| `register_factory` | `bool` | Register the resulting KCell-function to the `KCLayout.factories` | `True` |
| `layout_cache` | `bool \| None` | If true, treat the layout like a cache, if a cell with the same name exists already, pick that one instead of using running the function. This only works if `set_name` is true. Can be globally configured through `config.cell_layout_cache`. | `None` |
| `overwrite_existing` | `bool \| None` | If cells were created with the same name, delete other cells with the same name. Can be globally configured through `config.cell_overwrite_existing`. | `None` |
| `info` | `dict[str, MetaData] \| None` | Additional metadata to put into info attribute. | `None` |
| `post_process` | `Iterable[Callable[[KC], None]] \| None` | List of functions to call after the cell has been created. | `None` |
| `debug_names` | `bool \| None` | Check on setting the name whether a cell with this name already exists. | `None` |
| `tags` | `list[str] \| None` | Tag cell functions with user defined tags. | `None` |

Returns: A wrapped cell function which caches responses and modifies the cell according to settings.

### clear

```
clear(keep_layers: bool = True) -> None
```

Clear the Layout.

If the layout is cleared, all the LayerEnums and

### clear\_kcells

```
clear_kcells() -> None
```

Clears all cells in the Layout object.

### create\_cell

```
create_cell(name: str, *args: str, allow_duplicate: bool = False) -> kdb.Cell
```

Create a new cell in the library.

This shouldn't be called manually. The constructor of KCell will call this method.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `name` | `str` | The (initial) name of the cell. | *required* |
| `allow_duplicate` | `bool` | Allow the creation of a cell with the same name which already is registered in the Layout. This will create a cell with the name `name` + `$1` or `2..n` increasing by the number of existing duplicates | `False` |
| `args` | `str` | additional arguments passed to `klayout.db.Layout.create_cell` | `()` |

Returns:

| Type | Description |
| --- | --- |
| `Cell` | klayout.db.Cell: klayout.db.Cell object created in the Layout |

### create\_layer\_enclosure

```
create_layer_enclosure(sections: Sequence[tuple[LayerInfo, int] | tuple[LayerInfo, int, int]] = [], name: str | None = None, main_layer: LayerInfo | None = None, dsections: Sequence[tuple[LayerInfo, float] | tuple[LayerInfo, float, float]] | None = None, bbox_sections: Sequence[tuple[LayerInfo, int]] = [], dbbox_sections: Sequence[tuple[LayerInfo, float]] | None = None) -> LayerEnclosure
```

Create a new LayerEnclosure in the KCLayout.

### delete\_cell

```
delete_cell(cell: AnyTKCell | int, *, delete_parents: bool = False) -> None
```

Delete a cell in the kcl object.

If `delete_parents` is false, the deletion might fail with a locked error from KLayout. KLayout will refuse to delete a cell if any of its callers are locked (i.e. parents or further ancestors).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `AnyTKCell \| int` | cell or its index to delete. | *required* |
| `delete_parents` | `bool` | Also delete any parent (and its ancestor) cell. This makes sense if we assume the parents and their parents are cached. | `False` |

### delete\_cell\_rec

```
delete_cell_rec(cell_index: int, *, delete_parents: bool = False) -> None
```

Deletes a KCell plus all subcells.

If `delete_parents` is false, the deletion might fail with a locked error from KLayout. KLayout will refuse to delete a cell if any of its callers are locked (i.e. parents or further ancestors).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell_index` | `int` | Cell index to delete. | *required* |
| `delete_parents` | `bool` | Also delete any parent (and its ancestor) cell. This makes sense if we assume the parents and their parents are cached. | `False` |

### delete\_cells

```
delete_cells(cell_index_list: Sequence[int], *, delete_parents: bool = False) -> None
```

Delete a sequence of cell by indexes.

If `delete_parents` is false, the deletion might fail with a locked error from KLayout. KLayout will refuse to delete a cell if any of its callers are locked (i.e. parents or further ancestors).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell_index_list` | `Sequence[int]` | List of cell indexes to delete. | *required* |
| `delete_parents` | `bool` | Also delete any parent (and its ancestor) cell. This makes sense if we assume the parents and their parents are cached. | `False` |

### device\_type\_for

```
device_type_for(target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any], provider: Callable[..., Any] | None = None, *, replace: bool = False) -> Callable[..., Any]
```

Register a device-type provider for a cell factory.

### display\_for

```
display_for(target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any], provider: Callable[..., Any] | None = None, *, replace: bool = False) -> Callable[..., Any]
```

Register a display-hint provider for a cell factory.

### dkcell

```
dkcell(name: str | None = None, ports: DPorts | None = None) -> DKCell
```

Create a new cell based ont he pdk's layout object.

### dup

```
dup(init_cells: bool = True) -> KCLayout
```

Create a duplication of the `~KCLayout` object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `init_cells` | `bool` | initialize the all cells in the new KCLayout object | `True` |

Returns:

| Type | Description |
| --- | --- |
| `KCLayout` | Copy of itself |

### find\_layer

```
find_layer(name: str) -> LayerEnum
```

```
find_layer(info: LayerInfo) -> LayerEnum
```

```
find_layer(layer: int, datatype: int) -> LayerEnum
```

```
find_layer(layer: int, dataytpe: int, name: str) -> LayerEnum
```

```
find_layer(name: str, *, allow_undefined_layers: Literal[True] = True) -> LayerEnum | int
```

```
find_layer(info: LayerInfo, *, allow_undefined_layers: Literal[True] = True) -> LayerEnum | int
```

```
find_layer(layer: int, datatype: int, *, allow_undefined_layers: Literal[True] = True) -> LayerEnum | int
```

```
find_layer(layer: int, dataytpe: int, name: str, allow_undefined_layers: Literal[True] = True) -> LayerEnum | int
```

```
find_layer(*args: int | str | LayerInfo, **kwargs: int | str | LayerInfo | bool) -> LayerEnum | int
```

Try to find a registered layer. Throws a KeyError if it cannot find it.

Can find a layer either by name, layer and datatype (two args), LayerInfo, or all three of layer, datatype, and name.

### generic\_factory

```
generic_factory(f: F, *, name: str | None = None) -> F
```

```
generic_factory(*, name: str | None = None) -> Callable[[F], F]
```

```
generic_factory(f: F | None = None, *, name: str | None = None) -> F | Callable[[F], F]
```

Register an arbitrary cell-producing function as a generic factory.

Generic factories are stored in `KCLayout.generic_factories`, separate from the `factories` / `virtual_factories` registries. They are expected to delegate to one of the real (cached) factories, so they need no cache of their own. On every call the returned cell's `kcl` is checked against this layout.

Can be used bare (`@kcl.generic_factory`), with a custom name (`@kcl.generic_factory(name="...")`), or as a direct call (`kcl.generic_factory(func, name="...")`).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `f` | `F \| None` | A callable returning a `(D)KCell` or `VKCell`. | `None` |
| `name` | `str \| None` | Name to register under. Defaults to the function's name. | `None` |

Returns:

| Type | Description |
| --- | --- |
| `F \| Callable[[F], F]` | The wrapped function (guardrail-checked) registered under `name`. |

### get\_asymmetrical\_cross\_section

```
get_asymmetrical_cross_section(cross_section: str | AsymmetricalCrossSection | DAsymmetricalCrossSection | TAsymmetricCrossSection[Any]) -> AsymmetricalCrossSection
```

Get an asymmetrical cross section by name or instance.

### get\_base\_cross\_section

```
get_base_cross_section(cross_section: str | SymmetricalCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict | DSymmetricalCrossSection | TCrossSection[Any], symmetrical: Literal[True]) -> SymmetricalCrossSection
```

```
get_base_cross_section(cross_section: str | AsymmetricalCrossSection | DAsymmetricalCrossSection | TAsymmetricCrossSection[Any], symmetrical: Literal[False]) -> AsymmetricalCrossSection
```

```
get_base_cross_section(cross_section: Any, symmetrical: None = None) -> SymmetricalCrossSection | AsymmetricalCrossSection
```

```
get_base_cross_section(cross_section: Any, symmetrical: bool | None = None) -> SymmetricalCrossSection | AsymmetricalCrossSection
```

Get a cross section by name or instance.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cross_section` | `Any` | name, spec, or instance. | *required* |
| `symmetrical` | `bool \| None` | kind filter. `None` (default) returns either kind, dispatching by input type (string names are looked up directly). `True` returns a symmetric cross section and raises if the resolved one is asymmetric. `False` returns an asymmetric cross section and raises if the resolved one is symmetric. | `None` |

### get\_cell

```
get_cell(obj: str | int, cell_type: type[KC] = KCell, error_search_limit: int | None = 10) -> KC
```

Retrieve a cell by name(str) or index(int).

**Attrs**

obj: name of cell or cell\_index cell\_type: type of cell to return

### get\_dasymmetric\_cross\_section

```
get_dasymmetric_cross_section(cross_section: str | AsymmetricalCrossSection | DAsymmetricalCrossSection | TAsymmetricCrossSection[Any]) -> DAsymmetricCrossSection
```

Get a um-flavored asymmetric cross section wrapper.

### get\_dcross\_section

```
get_dcross_section(cross_section: str | SymmetricalCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict | DSymmetricalCrossSection | CrossSection | DCrossSection, symmetrical: Literal[True]) -> DCrossSection
```

```
get_dcross_section(cross_section: str | AsymmetricalCrossSection | DAsymmetricalCrossSection | TAsymmetricCrossSection[Any], symmetrical: Literal[False]) -> DAsymmetricCrossSection
```

```
get_dcross_section(cross_section: Any, symmetrical: None = None) -> DCrossSection | DAsymmetricCrossSection
```

```
get_dcross_section(cross_section: Any, symmetrical: bool | None = None) -> DCrossSection | DAsymmetricCrossSection
```

Get a um cross section wrapper (symmetric or asymmetric, see kwarg).

### get\_enclosure

```
get_enclosure(enclosure: str | LayerEnclosure | LayerEnclosureSpec) -> LayerEnclosure
```

Gets a layer enclosure by name specification or the layerenclosure itself.

### get\_extrude\_config

```
get_extrude_config(cross_section: str | AnyCrossSectionInput) -> ExtrudeConfig | None
```

Get the default extrusion settings of a cross section, if any.

### get\_iasymmetric\_cross\_section

```
get_iasymmetric_cross_section(cross_section: str | AsymmetricalCrossSection | DAsymmetricalCrossSection | TAsymmetricCrossSection[Any]) -> AsymmetricCrossSection
```

Get a dbu-flavored asymmetric cross section wrapper.

### get\_icross\_section

```
get_icross_section(cross_section: str | SymmetricalCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict | DCrossSection | DSymmetricalCrossSection | CrossSection, symmetrical: Literal[True]) -> CrossSection
```

```
get_icross_section(cross_section: str | AsymmetricalCrossSection | DAsymmetricalCrossSection | TAsymmetricCrossSection[Any], symmetrical: Literal[False]) -> AsymmetricCrossSection
```

```
get_icross_section(cross_section: Any, symmetrical: None = None) -> CrossSection | AsymmetricCrossSection
```

```
get_icross_section(cross_section: Any, symmetrical: bool | None = None) -> CrossSection | AsymmetricCrossSection
```

Get a dbu cross section wrapper (symmetric or asymmetric, see kwarg).

### get\_meta\_data

```
get_meta_data() -> tuple[dict[str, Any], dict[str, Any]]
```

Read KCLayout meta info from the KLayout object.

### get\_symmetrical\_cross\_section

```
get_symmetrical_cross_section(cross_section: str | SymmetricalCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict | DSymmetricalCrossSection) -> SymmetricalCrossSection
```

Get a cross section by name or specification.

### info\_for

```
info_for(target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any], provider: Callable[..., Any] | None = None) -> Callable[..., Any]
```

Register a free-form info provider for a cell factory.

### kcell

```
kcell(name: str | None = None, ports: Ports | None = None) -> KCell
```

Create a new cell based ont he pdk's layout object.

### layerenum\_from\_dict

```
layerenum_from_dict(name: str = 'LAYER', *, layers: LayerInfos) -> type[LayerEnum]
```

Create a new LayerEnum from this KCLayout.

### layout\_cell

```
layout_cell(name: str | int) -> kdb.Cell | None
```

Get a cell by name or index from the Layout object.

### lock\_factories

```
lock_factories() -> None
```

Prevent further factories (real and virtual) from being registered.

This is irreversible: once locked, a `KCLayout` will reject any new factory registrations (e.g. via `@kcl.cell` / `@kcl.vcell` or direct `factories.add` calls). Use this to seal a PDK after registering all of its pcell functions.

### metadata\_for

```
metadata_for(target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any], provider: Callable[..., Any] | None = None, *, replace: bool = False) -> Callable[..., Any]
```

Register a full metadata provider for a cell factory.

The provider should return a `FactoryMetadata` or a dict with any subset of its fields. Use the field-specific decorators (`device_type_for`, `ports_for`, etc.) when only one aspect is being provided.

### metadata\_providers\_for

```
metadata_providers_for(factory: WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any]) -> tuple[_FactoryMetadataProviderRecord, ...]
```

Return all metadata provider records registered for a factory.

### model\_for

```
model_for(target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any], provider: Callable[..., Any] | None = None, *, position: Literal['append', 'prepend'] = 'append') -> Callable[..., Any]
```

Register a model provider for a cell factory.

Multiple model providers are concatenated. Use `position="prepend"` to insert before existing models.

### ports\_for

```
ports_for(target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any], provider: Callable[..., Any] | None = None, *, replace: bool = False) -> Callable[..., Any]
```

Register a port-spec provider for a cell factory.

The provider should return a list of `PortSpec` dicts. Port providers can be parametric — they may accept any subset of the cell factory's parameters.

### read

```
read(filename: str | Path, options: LoadLayoutOptions | None = None, register_cells: bool | None = None, test_merge: bool = True, update_kcl_meta_data: Literal['overwrite', 'skip', 'drop'] = 'skip', meta_format: Literal['v1', 'v2', 'v3'] | None = None) -> kdb.LayerMap
```

Read a GDS file into the existing Layout.

Any existing meta info (KCell.info and KCell.settings) will be overwritten if a KCell already exists. Instead of overwriting the cells, they can also be loaded into new cells by using the corresponding cell\_conflict\_resolution.

This will fail if any of the read cells try to load into a locked KCell.

Layout meta infos are ignored from the loaded layout.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `filename` | `str \| Path` | Path of the GDS file. | *required* |
| `options` | `LoadLayoutOptions \| None` | KLayout options to load from the GDS. Can determine how merge conflicts are handled for example. See https://www.klayout.de/doc-qt5/code/class\_LoadLayoutOptions.html | `None` |
| `register_cells` | `bool \| None` | If `True` create KCells for all cells in the GDS. | `None` |
| `test_merge` | `bool` | Check the layouts first whether they are compatible (no differences). | `True` |
| `update_kcl_meta_data` | `Literal['overwrite', 'skip', 'drop']` | How to treat loaded KCLayout info. overwrite: overwrite existing info entries skip: keep existing info values drop: don't add any new info | `'skip'` |
| `meta_format` | `Literal['v1', 'v2', 'v3'] \| None` | How to read KCell metainfo from the gds. `v1` had stored port transformations as strings, never versions have them stored and loaded in their native KLayout formats. | `None` |

### rebuild

```
rebuild() -> None
```

Rebuild cell tracking and remove destroyed cells from registered caches.

### register\_cell

```
register_cell(kcell: AnyTKCell, allow_reregister: bool = False) -> None
```

Register an existing cell in the KCLayout object.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcell` | `AnyTKCell` | KCell 56 be registered in the KCLayout | *required* |
| `allow_reregister` | `bool` | Overwrite the existing KCell registration with this one. Doesn't allow name duplication. | `False` |

### schematic\_for

```
schematic_for(target: str | WrappedKCellFunc[Any, Any], provider: Callable[..., Any] | None = None) -> Callable[..., Any]
```

Attach a schematic function to a cell factory after registration.

### set\_extrude\_config

```
set_extrude_config(cross_section: str | AnyCrossSectionInput, config: ExtrudeConfig, *, on_conflict: Literal['replace', 'raise'] = 'replace') -> None
```

Set the default extrusion settings of a cross section.

The cross section is registered if necessary. The config is stored under the cross section's `auto_name()`, so it applies to the cross section whether it is referenced by its name or by its structure.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cross_section` | `str \| AnyCrossSectionInput` | name or instance of the cross section. | *required* |
| `config` | `ExtrudeConfig` | extrusion settings. | *required* |
| `on_conflict` | `Literal['replace', 'raise']` | what to do if the cross section already has a different config. `"replace"` overwrites it, `"raise"` raises an `ExtrudeConfigConflictError`. Setting an equal config is always allowed. | `'replace'` |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | if the config references strips the cross section doesn't have. |
| `ExtrudeConfigConflictError` | if `on_conflict="raise"` and the cross section already has a different config. |

### set\_layers\_from\_infos

```
set_layers_from_infos(name: str, layers: LayerInfos) -> type[LayerEnum]
```

Create a new LAYER enum based on the pdk's kcl.

### set\_meta\_data

```
set_meta_data() -> None
```

Set the info/settings of the KCLayout.

### tags\_for

```
tags_for(target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any], provider: Callable[..., Any] | None = None) -> Callable[..., Any]
```

Register a tags provider for a cell factory.

### to\_dbu

```
to_dbu(other: None) -> None
```

```
to_dbu(other: float) -> int
```

```
to_dbu(other: DPoint) -> kdb.Point
```

```
to_dbu(other: DVector) -> kdb.Vector
```

```
to_dbu(other: DBox) -> kdb.Box
```

```
to_dbu(other: DPolygon) -> kdb.Polygon
```

```
to_dbu(other: DPath) -> kdb.Path
```

```
to_dbu(other: DText) -> kdb.Text
```

```
to_dbu(other: float | DPoint | DVector | DBox | DPolygon | DPath | DText | None) -> int | kdb.Point | kdb.Vector | kdb.Box | kdb.Polygon | kdb.Path | kdb.Text | None
```

Convert Shapes or values in dbu to DShapes or floats in um.

### to\_um

```
to_um(other: None) -> None
```

```
to_um(other: int) -> float
```

```
to_um(other: Point) -> kdb.DPoint
```

```
to_um(other: Vector) -> kdb.DVector
```

```
to_um(other: Box) -> kdb.DBox
```

```
to_um(other: Polygon) -> kdb.DPolygon
```

```
to_um(other: Path) -> kdb.DPath
```

```
to_um(other: Text) -> kdb.DText
```

```
to_um(other: int | Point | Vector | Box | Polygon | Path | Text | None) -> float | kdb.DPoint | kdb.DVector | kdb.DBox | kdb.DPolygon | kdb.DPath | kdb.DText | None
```

Convert Shapes or values in dbu to DShapes or floats in um.

### top\_kcell

```
top_kcell() -> KCell
```

Return the top KCell if there is a single one.

### top\_kcells

```
top_kcells() -> list[KCell]
```

Return the top KCells.

### vcell

```
vcell(_func: Callable[KCellParams, VK]) -> Callable[KCellParams, VK]
```

```
vcell(*, set_settings: bool = True, set_name: bool = True, add_port_layers: bool = True, cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None, basename: str | None = None, drop_params: Sequence[str] = ('self', 'cls'), register_factory: bool = True, info: dict[str, MetaData] | None = None, check_ports: bool = True, check_pins: bool = True, check_unnamed_cells: CheckUnnamedCells = ..., tags: list[str] | None = None, lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None) -> Callable[[Callable[KCellParams, VK]], Callable[KCellParams, VK]]
```

```
vcell(*, set_settings: bool = True, set_name: bool = True, add_port_layers: bool = True, cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None, basename: str | None = None, drop_params: Sequence[str] = ('self', 'cls'), register_factory: bool = True, post_process: Iterable[Callable[[VKCell], None]], info: dict[str, MetaData] | None = None, check_ports: bool = True, check_pins: bool = True, check_unnamed_cells: CheckUnnamedCells = ..., tags: list[str] | None = None, lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None) -> Callable[[Callable[KCellParams, VK]], Callable[KCellParams, VK]]
```

```
vcell(*, output_type: type[VK], set_settings: bool = True, set_name: bool = True, add_port_layers: bool = True, cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None, basename: str | None = None, drop_params: Sequence[str] = ('self', 'cls'), register_factory: bool = True, info: dict[str, MetaData] | None = None, check_ports: bool = True, check_pins: bool = True, check_unnamed_cells: CheckUnnamedCells = ..., tags: list[str] | None = None, lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None) -> Callable[[Callable[KCellParams, VKCell]], Callable[KCellParams, VK]]
```

```
vcell(*, output_type: type[VK], set_settings: bool = True, set_name: bool = True, add_port_layers: bool = True, cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None, basename: str | None = None, drop_params: Sequence[str] = ('self', 'cls'), register_factory: bool = True, post_process: Iterable[Callable[[VKCell], None]], info: dict[str, MetaData] | None = None, check_ports: bool = True, check_pins: bool = True, check_unnamed_cells: CheckUnnamedCells = ..., tags: list[str] | None = None, lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None) -> Callable[[Callable[KCellParams, VKCell]], Callable[KCellParams, VK]]
```

```
vcell(_func: Callable[KCellParams, VKCell] | None = None, /, *, output_type: type[VK] | None = None, set_settings: bool = True, set_name: bool = True, add_port_layers: bool = True, cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None, basename: str | None = None, drop_params: Sequence[str] = ('self', 'cls'), register_factory: bool = True, post_process: Iterable[Callable[[VKCell], None]] | None = None, info: dict[str, MetaData] | None = None, check_ports: bool = True, check_pins: bool = True, check_unnamed_cells: CheckUnnamedCells = CheckUnnamedCells.WARNING, tags: list[str] | None = None, lvs_equivalent_ports: list[list[str]] | None = None, ports: PortsDefinition | None = None) -> Callable[KCellParams, VK] | Callable[[Callable[KCellParams, VK]], Callable[KCellParams, VK]]
```

Decorator to cache and auto name the cell.

This will use `functools.cache` to cache the function call. Additionally, if enabled this will set the name and from the args/kwargs of the function and also paste them into a settings dictionary of the KCell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `set_settings` | `bool` | Copy the args &amp; kwargs into the settings dictionary | `True` |
| `set_name` | `bool` | Auto create the name of the cell to the functionname plus a string created from the args/kwargs | `True` |
| `check_ports` | `bool` | Check uniqueness of port names. | `True` |
| `check_pins` | `bool` | Check uniqueness of pin names. | `True` |
| `check_unnamed_cells` | `CheckUnnamedCells` | Check for unnamed child cells (matching `Unnamed_\d+`). `"error"` raises, `"warning"` logs a warning, `"ignore"` skips the check. | `WARNING` |
| `add_port_layers` | `bool` | Add special layers of `KCLayout.netlist_layer_mapping` to the ports if the port layer is in the mapping. | `True` |
| `cache` | `Cache[Hashable, Any] \| dict[Hashable, Any] \| None` | Provide a user defined cache instead of an internal one. This can be used for example to clear the cache. | `None` |
| `basename` | `str \| None` | Overwrite the name normally inferred from the function or class name. | `None` |
| `drop_params` | `Sequence[str]` | Drop these parameters before writing the settings | `('self', 'cls')` |
| `register_factory` | `bool` | Register the resulting KCell-function to the `KCLayout.factories` | `True` |
| `info` | `dict[str, MetaData] \| None` | Additional metadata to put into info attribute. | `None` |
| `post_process` | `Iterable[Callable[[VKCell], None]] \| None` | List of functions to call after the cell has been created. | `None` |

Returns: A wrapped vcell function which caches responses and modifies the VKCell according to settings.

### vkcell

```
vkcell(name: str | None = None) -> VKCell
```

Create a new cell based ont he pdk's layout object.

### write

```
write(filename: str | Path, options: SaveLayoutOptions | None = None, set_meta_data: bool = True, convert_external_cells: bool = False, autoformat_from_file_extension: bool = True, deduplicate_cell_names: bool = False, clear_existing_meta: bool = True) -> None
```

Write a GDS file into the existing Layout.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `filename` | `str \| Path` | Path of the GDS file. | *required* |
| `options` | `SaveLayoutOptions \| None` | KLayout options to load from the GDS. Can determine how merge conflicts are handled for example. See https://www.klayout.de/doc-qt5/code/class\_LoadLayoutOptions.html | `None` |
| `set_meta_data` | `bool` | Make sure all the cells have their metadata set | `True` |
| `convert_external_cells` | `bool` | Whether to make KCells not in this KCLayout to | `False` |
| `autoformat_from_file_extension` | `bool` | Set the format of the output file automatically from the file extension of `filename`. This is necessary for the options. If not set, this will default to `GDSII`. | `True` |
| `deduplicate_cell_names` | `bool` | If True, auto-rename duplicate cells with `$1`, `$2`, … suffixes before writing. If False (the default), raise :class:`~kfactory.exceptions.DuplicateCellNameError` when duplicates are detected. | `False` |
| `clear_existing_meta` | `bool` | Remove the layout's existing meta info before setting it, so the file only contains the current state of the KCLayout. Only used if `set_meta_data` is True. | `True` |

## get\_default\_kcl

```
get_default_kcl() -> KCLayout
```

Utility function to get the default kcl object.

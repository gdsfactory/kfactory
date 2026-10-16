# enclosure

Enclosure module.

Enclosures allow to calculate slab/excludes and similar concepts to an arbitrary shape located on a main\_layer or reference layer or region.

## DLayerEnclosure

Bases: `BaseModel`

um based version of LayerEnclosure.

Fields:

- `sections` (`list[tuple[LayerInfo, float] | tuple[LayerInfo, float, float]]`)
- `name` (`str | None`)
- `main_layer` (`LayerInfo`)
- `bbox_sections` (`list[tuple[LayerInfo, float]]`)

## Direction

Bases: `IntEnum`

Direction for applying standard minkowski sums.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `X` |  | Only apply in x-direction. |
| `Y` |  | Only apply in y-direction. |
| `BOTH` |  | Apply in both x/y-direction. Equivalent to a minkowski sum with a square. |

## KCellEnclosure

Bases: `BaseModel`

Collection of enclosures for cells.

Fields:

- `enclosures` (`LayerEnclosureCollection`)

### \_\_hash\_\_

```
__hash__() -> int
```

Hash of the KCellEnclosure.

### \_\_init\_\_

```
__init__(enclosures: Iterable[LayerEnclosure]) -> None
```

Init. Allow usage of an iterable object instead of a collection.

### apply\_minkowski\_custom

```
apply_minkowski_custom(c: KCell, shape: Callable[[int], Edge | Polygon | Box]) -> None
```

Apply an enclosure with a custom shape.

This can be used for tapers/ waveguides or similar that are straight.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Cell to apply the enclosure to. | *required* |
| `shape` | `Callable[[int], Edge \| Polygon \| Box]` | A function that will return a shape which takes one argument the size of the section in dbu. | *required* |
| `shape` | `Callable[[int], Edge \| Polygon \| Box]` | Reference to use as a base for the enclosure. | *required* |

### apply\_minkowski\_enc

```
apply_minkowski_enc(c: KCell, direction: Direction = Direction.BOTH) -> None
```

Apply an enclosure with a vector in y-direction.

This can be used for tapers/ waveguides or similar that are straight.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Cell to apply the enclosure to. | *required* |
| `direction` | `Direction` | X/Y or both directions, see \[kfactory.enclosure.DIRECTION\]. Uses a box if both directions are selected. | `BOTH` |

### apply\_minkowski\_tiled

```
apply_minkowski_tiled(c: KCell, tile_size: float | None = None, n_pts: int = 64, n_threads: int | None = None, carve_out_ports: bool = True) -> None
```

Minkowski regions with tiling processor.

Useful if the target is a big or complicated enclosure. Will split target ref into tiles and calculate them in parallel. Uses a circle as a shape for the minkowski sum.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Target KCell to apply the enclosures into. | *required* |
| `tile_size` | `float \| None` | Tile size. This should be in the order off 10+ maximum size of the maximum size of sections. \[um\] If None is set, the minimum size is set to 10xmax(d\_max) of all sections or 200um whichever is bigger. | `None` |
| `n_pts` | `int` | Number of points in the circle. \< 3 will create a triangle. 4 a diamond, etc. | `64` |
| `n_threads` | `int \| None` | Number o threads to use. By default (`None`) it will use as many threads as are set to the process (usually all cores of the machine). | `None` |
| `carve_out_ports` | `bool` | Carves out a box of port\_width + | `True` |

### apply\_minkowski\_x

```
apply_minkowski_x(c: KCell) -> None
```

Apply an enclosure with a vector in x-direction.

This can be used for tapers/ waveguides or similar that are straight.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Cell to apply the enclosure to. | *required* |

### apply\_minkowski\_y

```
apply_minkowski_y(c: KCell) -> None
```

Apply an enclosure with a vector in y-direction.

This can be used for tapers/ waveguides or similar that are straight.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Cell to apply the enclosure to. | *required* |

### minkowski\_region

```
minkowski_region(r: Region, d: int | None, shape: Callable[[int], list[Point] | Box | Edge | Polygon]) -> kdb.Region
```

Calculaste a region from a minkowski sum.

If the distance is negative, the function will take the inverse region and apply the minkowski and take the inverse again.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `r` | `Region` | Target region. | *required* |
| `d` | `int \| None` | Distance to pass to the shape. Can be any integer. \[dbu\] | *required* |
| `shape` | `Callable[[int], list[Point] \| Box \| Edge \| Polygon]` | Function returning a shape for the minkowski region. | *required* |

## KCellLayerEnclosures

Bases: `BaseModel`

Collection of LayerEnclosures.

Fields:

- `enclosures` (`list[LayerEnclosure]`)

Validators:

- `enclosures_must_have_main_layer` → `enclosures`

### \_\_getitem\_\_

```
__getitem__(key: str | int) -> LayerEnclosure
```

Retrieve enclosure by main layer.

### enclosures\_must\_have\_main\_layer

```
enclosures_must_have_main_layer(v: list[LayerEnclosure]) -> list[LayerEnclosure]
```

The PDK Enclosure must have main layers defined for each Enclosure.

The PDK Enclosure uses this to automatically apply enclosures.

## LayerEnclosure

Bases: `BaseModel`

Definitions for calculation of enclosing (or smaller) shapes of a reference.

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `layer_sections` | `dict[LayerInfo, LayerSection]` | Mapping of layers to their layer sections. |
| `main_layer` | `LayerInfo \| None` | Layer which to use unless specified otherwise. |
| `bbox_sections` | `dict[LayerInfo, int]` | Mapping of layers to their bbox offset. Sorted by layer on construction, so iteration order is deterministic (the enclosure is frozen). |

Fields:

- `layer_sections` (`dict[LayerInfo, LayerSection]`)
- `_name` (`str | None`)
- `main_layer` (`LayerInfo | None`)
- `bbox_sections` (`dict[LayerInfo, int]`)

### is\_named

```
is_named: bool
```

Whether an explicit name was given (vs. a derived structural name).

### name

```
name: str
```

Get name of the Enclosure.

### unnamed\_key

```
unnamed_key: str
```

Deterministic structural key, independent of the explicit name.

This is the same hash an unnamed enclosure is named after. Exposing it on named enclosures as well lets the registry alias the structural signature to a named enclosure.

### \_\_hash\_\_

```
__hash__() -> int
```

Calculate a unique hash of the enclosure.

### \_\_init\_\_

```
__init__(sections: Sequence[tuple[LayerInfo, int] | tuple[LayerInfo, int, int]] = [], name: str | None = None, main_layer: LayerInfo | None = None, dsections: Sequence[tuple[LayerInfo, float] | tuple[LayerInfo, float, float]] | None = None, bbox_sections: Sequence[tuple[LayerInfo, int]] = [], dbbox_sections: Sequence[tuple[LayerInfo, float]] | None = None, kcl: KCLayout | None = None) -> None
```

Constructor of new enclosure.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `sections` | `Sequence[tuple[LayerInfo, int] \| tuple[LayerInfo, int, int]]` | tuples containing info for the enclosure. Elements must be of the form (layer, max) or (layer, min, max) | `[]` |
| `name` | `str \| None` | Optional name of the enclosure. If a name is given in the cell name this name will be used for enclosure arguments. | `None` |
| `main_layer` | `LayerInfo \| None` | Main layer used if the functions don't get an explicit layer. | `None` |
| `dsections` | `Sequence[tuple[LayerInfo, float] \| tuple[LayerInfo, float, float]] \| None` | Same as sections but min/max defined in um | `None` |
| `bbox_sections` | `Sequence[tuple[LayerInfo, int]]` | tuples of (layer, offset) to grow the bounding box of the reference by `offset` on `layer`. | `[]` |
| `dbbox_sections` | `Sequence[tuple[LayerInfo, float]] \| None` | Same as `bbox_sections` but the offset defined in um. | `None` |
| `kcl` | `KCLayout \| None` | `KCLayout` Used for conversion dbu -\> um or when copying. Must be specified if `dsections` or `dbbox_sections` is not `None`. Also necessary if copying to another layout and not all layers used are LayerInfos. | `None` |

### \_\_str\_\_

```
__str__() -> str
```

String representation of an enclosure.

Use name if available. Use a hash of the sections and main\_layer if the name is `None`.

### apply\_bbox

```
apply_bbox(c: KCell, ref: LayerInfo | Region | None = None) -> None
```

Apply an enclosure based on a bounding box.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Target cell. | *required* |
| `ref` | `LayerInfo \| Region \| None` | Reference layer or region (the bounding box). If `None` use the `main_layer` of the enclosure if defined, else throw an error. | `None` |

### apply\_custom

```
apply_custom(c: KCell, shape: Callable[[int, int | None], Edge | Polygon | Box | Region]) -> None
```

Apply a custom shape based on the section size.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | The cell to apply the enclosure to. | *required* |
| `shape` | `Callable[[int, int \| None], Edge \| Polygon \| Box \| Region]` | A function taking the section size in dbu to calculate the full enclosure. | *required* |

### apply\_minkowski\_custom

```
apply_minkowski_custom(c: KCell, shape: Callable[[int], Edge | Polygon | Box], ref: LayerInfo | Region | None = None) -> None
```

Apply an enclosure with a custom shape.

This can be used for tapers/ waveguides or similar that are straight.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Cell to apply the enclosure to. | *required* |
| `shape` | `Callable[[int], Edge \| Polygon \| Box]` | A function that will return a shape which takes one argument the size of the section in dbu. | *required* |
| `ref` | `LayerInfo \| Region \| None` | Reference to use as a base for the enclosure. | `None` |

### apply\_minkowski\_enc

```
apply_minkowski_enc(c: KCell, ref: LayerInfo | Region | None, direction: Direction = Direction.BOTH) -> None
```

Apply an enclosure with a vector in y-direction.

This can be used for tapers/ waveguides or similar that are straight.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Cell to apply the enclosure to. | *required* |
| `ref` | `LayerInfo \| Region \| None` | Reference to use as a base for the enclosure. | *required* |
| `direction` | `Direction` | X/Y or both directions. Uses a box if both directions are selected. | `BOTH` |

### apply\_minkowski\_tiled

```
apply_minkowski_tiled(c: KCell, ref: LayerInfo | Region | None = None, tile_size: float | None = None, n_pts: int = 64, n_threads: int | None = None, carve_out_ports: Sequence[Port] = []) -> None
```

Minkowski regions with tiling processor.

Useful if the target is a big or complicated enclosure. Will split target ref into tiles and calculate them in parallel. Uses a circle as a shape for the minkowski sum.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Target KCell to apply the enclosures into. | *required* |
| `ref` | `LayerInfo \| Region \| None` | The reference shapes to apply the enclosures to. Can be a layer or a region. If `None`, it will try to use the `main_layer` of the enclosure. | `None` |
| `tile_size` | `float \| None` | Tile size. This should be in the order off 10+ maximum size of the maximum size of sections. | `None` |
| `n_pts` | `int` | Number of points in the circle. \< 3 will create a triangle. 4 a diamond, etc. | `64` |
| `n_threads` | `int \| None` | Number o threads to use. By default (`None`) it will use as many threads as are set to the process (usually all cores of the machine). | `None` |
| `carve_out_ports` | `Sequence[Port]` | Carves out a box of port\_width + | `[]` |

### apply\_minkowski\_x

```
apply_minkowski_x(c: KCell, ref: LayerInfo | Region | None) -> None
```

Apply an enclosure with a vector in x-direction.

This can be used for tapers/ waveguides or similar that are straight.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Cell to apply the enclosure to. | *required* |
| `ref` | `LayerInfo \| Region \| None` | Reference to use as a base for the enclosure. | *required* |

### apply\_minkowski\_y

```
apply_minkowski_y(c: KCell, ref: LayerInfo | Region | None = None) -> None
```

Apply an enclosure with a vector in y-direction.

This can be used for tapers/ waveguides or similar that are straight.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Cell to apply the enclosure to. | *required* |
| `ref` | `LayerInfo \| Region \| None` | Reference to use as a base for the enclosure. | `None` |

### extrude\_path

```
extrude_path(c: KCell, path: list[DPoint], main_layer: LayerInfo | None, width: float, start_angle: float | None = None, end_angle: float | None = None) -> None
```

Extrude a path and add it to a main layer.

Start and end angle should be set in relation to the orientation of the path. If the path for example is starting E-\>W, the start angle should be 0 (if that that is the desired angle). End angle is the same if the end piece is stopping 2nd-last -\> last in E-\>W.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | The cell where to insert the path to | *required* |
| `path` | `list[DPoint]` | Backbone of the path. \[um\] | *required* |
| `main_layer` | `LayerInfo \| None` | Layer index where to put the main part of the path. | *required* |
| `width` | `float` | Width of the core of the path | *required* |
| `start_angle` | `float \| None` | angle of the start piece | `None` |
| `end_angle` | `float \| None` | angle of the end piece | `None` |

### extrude\_path\_dynamic

```
extrude_path_dynamic(c: KCell, path: list[DPoint], main_layer: LayerInfo | None, widths: Callable[[float], float] | list[float]) -> None
```

Extrude a path and add it to a main layer.

Supports a dynamic width of the path defined by a function returning the width for the interval \[0,1\], or as a list of widths of the same lengths as the points.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | The cell where to insert the path to | *required* |
| `path` | `list[DPoint]` | Backbone of the path. \[um\] | *required* |
| `main_layer` | `LayerInfo \| None` | Layer index where to put the main part of the path. | *required* |
| `widths` | `Callable[[float], float] \| list[float]` | Width of the core of the path | *required* |

### minkowski\_region

```
minkowski_region(r: Region, d: int | None, shape: Callable[[int], list[Point] | Box | Edge | Polygon]) -> kdb.Region
```

Calculaste a region from a minkowski sum.

If the distance is negative, the function will take the inverse region and apply the minkowski and take the inverse again.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `r` | `Region` | Target region. | *required* |
| `d` | `int \| None` | Distance to pass to the shape. Can be any integer. \[dbu\] | *required* |
| `shape` | `Callable[[int], list[Point] \| Box \| Edge \| Polygon]` | Function returning a shape for the minkowski region. | *required* |

### to\_dtype

```
to_dtype(kcl: KCLayout) -> DLayerEnclosure
```

Convert the enclosure to a um based enclosure.

## LayerEnclosureCollection

Bases: `BaseModel`

Collection of LayerEnclosures.

Fields:

- `enclosures` (`list[LayerEnclosure]`)

### \_\_getitem\_\_

```
__getitem__(key: str | int) -> LayerEnclosure
```

Retrieve enclosure by main layer.

## LayerEnclosureModel

Bases: `RootModel[dict[str, LayerEnclosure]]`

PDK access model for LayerEnclsoures.

### \_\_getattr\_\_

```
__getattr__(__key: str) -> LayerEnclosure
```

Retrieve attribute by key.

### \_\_getitem\_\_

```
__getitem__(__key: str) -> LayerEnclosure
```

Retrieve element by string key.

### \_\_setattr\_\_

```
__setattr__(__key: str, /, __val: LayerEnclosure) -> None
```

Add a new LayerEnclosure.

### \_\_setitem\_\_

```
__setitem__(__key: str, /, __val: LayerEnclosure) -> None
```

Add a new LayerEnclosure.

## LayerSection

Bases: `BaseModel`

A collection of sections intended for a layer.

Adding a section will trigger an evaluation to merge touching or overlapping sections.

Fields:

- `sections` (`list[Section]`)

### \_\_hash\_\_

```
__hash__() -> int
```

Unique hash of LayerSection.

### add\_section

```
add_section(sec: Section) -> int
```

Add a new section.

Checks for overlaps after.

### max\_size

```
max_size() -> int
```

Maximum size of the sections in this layer section.

## RegionOperator

Bases: `TileOutputReceiver`

Region collector. Just getst the tile and inserts it into the target cell.

### \_\_init\_\_

```
__init__(cell: KCell, layer: LayerInfo) -> None
```

Initialization.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `KCell` | Target cell. | *required* |
| `layer` | `LayerInfo` | Target layer. | *required* |

### insert

```
insert() -> None
```

```
insert(port_holes: Region) -> None
```

```
insert(port_holes: Region | None = None) -> None
```

Insert the finished region into the cell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port_holes` | `Region \| None` | Carve out holes around the ports. | `None` |

### put

```
put(ix: int, iy: int, tile: Box, region: Region, dbu: float, clip: bool) -> None
```

Tiling Processor output call.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `ix` | `int` | x-axis index of tile. | *required* |
| `iy` | `int` | y\_axis index of tile. | *required* |
| `tile` | `Box` | The bounding box of the tile. | *required* |
| `region` | `Region` | The target object of the `klayout.db.TilingProcessor` | *required* |
| `dbu` | `float` | dbu used by the processor. | *required* |
| `clip` | `bool` | Whether the target was clipped to the tile or not. | *required* |

## RegionTilesOperator

Bases: `TileOutputReceiver`

Region collector. Just getst the tile and inserts it into the target cell.

As it can be used multiple times for the same tile, it needs to merge when inserting.

### \_\_init\_\_

```
__init__(cell: KCell, layers: list[LayerInfo]) -> None
```

Initialization.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `cell` | `KCell` | Target cell. | *required* |
| `layers` | `list[LayerInfo]` | Target layers. | *required* |

### insert

```
insert() -> None
```

```
insert(port_hole_map: dict[LayerInfo, Region]) -> None
```

```
insert(port_hole_map: dict[LayerInfo, Region] | None = None) -> None
```

Insert the finished region into the cell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port_hole_map` | `dict[LayerInfo, Region] \| None` | Carve out holes around the ports. | `None` |

### merge\_region

```
merge_region() -> None
```

Create one region from the individual tiles.

### put

```
put(ix: int, iy: int, tile: Box, region: Region, dbu: float, clip: bool) -> None
```

Tiling Processor output call.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `ix` | `int` | x-axis index of tile. | *required* |
| `iy` | `int` | y\_axis index of tile. | *required* |
| `tile` | `Box` | The bounding box of the tile. | *required* |
| `region` | `Region` | The target object of the `klayout.db.TilingProcessor` | *required* |
| `dbu` | `float` | dbu used by the processor. | *required* |
| `clip` | `bool` | Whether the target was clipped to the tile or not. | *required* |

## Section

Bases: `BaseModel`

Section of an Enclosure.

```
Maximum only Section:
    ┌────────────────────────┐  ▲
    │                        │  │
    │  ┌──────────────────┐  │  │
    │  │                  │  │  │
    │  │    Reference     │  │  │ Section
    │  │                  │  │  │ (d_max only)
    │  └─────────────┬────┘  │  │
    │                │d_max  │  │
    └────────────────▼───────┘  ▼


Minimum & Maximum Section:
    ┌─────────────────┐
    │     Section     │
    │  ┌───────────┐  │
    │  │           │  │
    │  │  ┌─────┐  │◄─┼──d_min
    │  │  │ Ref │  │  │
    │  │  └─────┘  │  │
    │  │           │  │◄─d_max
    │  └───────────┘  │
    │                 │
    └─────────────────┘
```

Attributes:

| Name | Type | Description |
| --- | --- | --- |
| `d_min` | `int \| None` | Start of the section. If `None`, the section will span all the way between the maxes. |
| `d_max` | `int` | the maximum extent of the section from the reference. |

Fields:

- `d_min` (`int | None`)
- `d_max` (`int`)

### \_\_hash\_\_

```
__hash__() -> int
```

Hash of the section.

## extrude\_path

```
extrude_path(target: KCell, layer: LayerInfo, path: list[DPoint], width: float, enclosure: LayerEnclosure | None = None, start_angle: float | None = None, end_angle: float | None = None) -> kdb.DPolygon
```

Extrude a path from a list of points and a static width.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `target` | `KCell` | the cell where to insert the shapes to (and get the database unit from) | *required* |
| `layer` | `LayerInfo` | the main layer that should be extruded | *required* |
| `path` | `list[DPoint]` | list of floating-points points | *required* |
| `width` | `float` | width in um | *required* |
| `enclosure` | `LayerEnclosure \| None` | optional enclosure object, specifying necessary layers.this will extrude around the `layer` | `None` |
| `start_angle` | `float \| None` | optionally specify a custom starting angle if `None` will be autocalculated from the first two elements | `None` |
| `end_angle` | `float \| None` | optionally specify a custom ending angle if `None` will be autocalculated from the last two elements | `None` |

## extrude\_path\_cross\_section

```
extrude_path_cross_section(target: KCell, path: list[DPoint], cross_section: AnyCrossSection, start_angle: float | None = None, end_angle: float | None = None) -> None
```

Extrude a (symmetric or asymmetric) cross section along a path.

The standard static-width extrusion that takes a cross section instead of a `(layer, width, enclosure)` triple. Symmetric cross sections are extruded exactly as `extrude_path` (centered `width` + enclosure sections — byte-identical output). Asymmetric cross sections are extruded as one signed band `[section_min, section_max]` per strip (the main strip plus each aux section), so the profile keeps its left/right offsets; strips sharing a layer are merged.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `target` | `KCell` | the cell where to insert the shapes to (and get the database unit from) | *required* |
| `path` | `list[DPoint]` | list of floating-points points (in um) | *required* |
| `cross_section` | `AnyCrossSection` | the cross section to extrude | *required* |
| `start_angle` | `float \| None` | optionally specify a custom starting angle if `None` will be autocalculated from the first two elements | `None` |
| `end_angle` | `float \| None` | optionally specify a custom ending angle if `None` will be autocalculated from the last two elements | `None` |

## extrude\_path\_dynamic

```
extrude_path_dynamic(target: KCell, layer: LayerInfo, path: list[DPoint], widths: Callable[[float], float] | list[float], enclosure: LayerEnclosure | None = None, start_angle: float | None = None, end_angle: float | None = None) -> None
```

Extrude a path with dynamic width.

Extrude from a list of points and a list of widths and add an enclosure if specified.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `target` | `KCell` | the cell where to insert the shapes to (and get the database unit from) | *required* |
| `layer` | `LayerInfo` | the main layer that should be extruded | *required* |
| `path` | `list[DPoint]` | list of floating-points points | *required* |
| `widths` | `Callable[[float], float] \| list[float]` | function (from t==0 to t==1) defining a width profile for the path \| list with width for the profile (needs same length as path) | *required* |
| `enclosure` | `LayerEnclosure \| None` | optional enclosure object, specifying necessary layers.this will extrude around the `layer` | `None` |
| `start_angle` | `float \| None` | optionally specify a custom starting angle if `None` will be autocalculated from the first two elements | `None` |
| `end_angle` | `float \| None` | optionally specify a custom ending angle if `None` will be autocalculated from the last two elements | `None` |

## extrude\_path\_dynamic\_points

```
extrude_path_dynamic_points(path: list[DPoint], widths: Callable[[float], float] | list[float], start_angle: float | None = None, end_angle: float | None = None) -> tuple[list[kdb.DPoint], list[kdb.DPoint]]
```

Extrude a profile with a list of points and a list of widths.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `path` | `list[DPoint]` | list of floating-points points | *required* |
| `widths` | `Callable[[float], float] \| list[float]` | function (from t==0 to t==1) defining a width profile for the path \| list with width for the profile (needs same length as path) | *required* |
| `start_angle` | `float \| None` | optionally specify a custom starting angle if `None` will be autocalculated from the first two elements | `None` |
| `end_angle` | `float \| None` | optionally specify a custom ending angle if `None` will be autocalculated from the last two elements | `None` |

## extrude\_path\_points

```
extrude_path_points(path: Sequence[DPoint], width: float, start_angle: float | None = None, end_angle: float | None = None) -> tuple[list[kdb.DPoint], list[kdb.DPoint]]
```

Extrude a path from a list of points and a static width.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `path` | `Sequence[DPoint]` | list of floating-points points | *required* |
| `width` | `float` | width in um | *required* |
| `start_angle` | `float \| None` | optionally specify a custom starting angle if `None` will be autocalculated from the first two elements | `None` |
| `end_angle` | `float \| None` | optionally specify a custom ending angle if `None` will be autocalculated from the last two elements | `None` |

## is\_callable\_widths

```
is_callable_widths(widths: Callable[[float], float] | list[float]) -> TypeGuard[Callable[[float], float]]
```

Determines whether a width object is callable or a list.

## path\_pts\_to\_polygon

```
path_pts_to_polygon(pts_top: list[DPoint], pts_bot: list[DPoint]) -> kdb.DPolygon
```

Convert a list of points to a polygon.

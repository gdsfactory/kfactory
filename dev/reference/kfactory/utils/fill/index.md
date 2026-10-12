# fill

ill Utilities.

Filling empty regions in KCells with filling cells.

## FillOperator

Bases: `TileOutputReceiver`

Output Receiver of the TilingProcessor.

### \_\_init\_\_

```
__init__(kcl: KCLayout, top_cell: KCell, fill_cell_index: int, fc_bbox: Box, origin: Point, row_step: Vector, column_step: Vector, fill_margin: Vector | None = None, remaining_polygons: Region | None = None, multi: bool = False) -> None
```

Initialize the receiver.

### insert\_fill

```
insert_fill() -> None
```

Insert fill cell into the regions.

### put

```
put(ix: int, iy: int, tile: Box, region: Region, dbu: float, clip: bool) -> None
```

Called by the TilingProcessor.

## SparseFillOperator

Bases: `TileOutputReceiver`

Output Receiver of the TilingProcessor.

### \_\_init\_\_

```
__init__() -> None
```

Initialize the receiver.

### put

```
put(ix: int, iy: int, tile: Box, region: Region, dbu: float, clip: bool) -> None
```

Called by the TilingProcessor.

## add\_coverage

```
add_coverage(c: ProtoTKCell[Any], max_distance: um, coverage_cell: ProtoTKCell[Any], coverage_layers: Iterable[tuple[LayerInfo, um]] = [], coverage_regions: Iterable[tuple[Region, um]] = [], avoid_layers: Iterable[tuple[LayerInfo, um]] = [], avoid_regions: Iterable[tuple[Region, um]] = [], n_threads: int | None = None, tile_size: tuple[um, um] = (500, 500), fill_box_sizing: tuple[um, um] = (50, 25)) -> None
```

Cover a Cell with metrology or similar structures.

These structures usually don't require the same

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `ProtoTKCell[Any]` | Target cell. | *required* |
| `coverage_cell` | `ProtoTKCell[Any]` | The cell used as a cell to fill the regions. | *required* |
| `coverage_layers` | `Iterable[tuple[LayerInfo, um]]` | Tuples of layer and keepout w.r.t. the regions. | `[]` |
| `coverage_regions` | `Iterable[tuple[Region, um]]` | Specific regions to fill. Also tuples like the layers. | `[]` |
| `avoid_layers` | `Iterable[tuple[LayerInfo, um]]` | Layers to ignore. Tuples like the coverage layers | `[]` |
| `avoid_regions` | `Iterable[tuple[Region, um]]` | Specific regions to ignore. Tuples like the fill layers. | `[]` |
| `n_threads` | `int \| None` | Max number of threads used. Defaults to number of cores of the machine. | `None` |
| `tile_size` | `tuple[um, um]` | Size of the tiles in um. | `(500, 500)` |

## cover

```
cover(top_cell: KCell, fill_cell: KCell, margin: int, placement_region: Region, cover_region: Region, fc_bbox_sizing: tuple[int, int]) -> None
```

Insert sparse cell into the regions.

## fill\_tiled

```
fill_tiled(c: ProtoTKCell[Any], fill_cell: ProtoTKCell[Any], fill_layers: Iterable[tuple[LayerInfo, um]] = [], fill_regions: Iterable[tuple[Region, um]] = [], exclude_layers: Iterable[tuple[LayerInfo, um]] = [], exclude_regions: Iterable[tuple[Region, um]] = [], n_threads: int | None = None, tile_size: tuple[um, um] | None = None, row_step: DVector | None = None, col_step: DVector | None = None, x_space: um = 0, y_space: um = 0, tile_border: tuple[um, um] = (20, 20), multi: bool = False) -> None
```

Fill a KCell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `ProtoTKCell[Any]` | Target cell. | *required* |
| `fill_cell` | `ProtoTKCell[Any]` | The cell used as a cell to fill the regions. | *required* |
| `fill_layers` | `Iterable[tuple[LayerInfo, um]]` | Tuples of layer and keepout w.r.t. the regions. | `[]` |
| `fill_regions` | `Iterable[tuple[Region, um]]` | Specific regions to fill. Also tuples like the layers. | `[]` |
| `exclude_layers` | `Iterable[tuple[LayerInfo, um]]` | Layers to ignore. Tuples like the fill layers | `[]` |
| `exclude_regions` | `Iterable[tuple[Region, um]]` | Specific regions to ignore. Tuples like the fill layers. | `[]` |
| `n_threads` | `int \| None` | Max number of threads used. Defaults to number of cores of the machine. | `None` |
| `tile_size` | `tuple[um, um] \| None` | Size of the tiles in um. | `None` |
| `row_step` | `DVector \| None` | DVector for steping to the next instance position in the row. x-coordinate must be \>= 0. | `None` |
| `col_step` | `DVector \| None` | DVector for steping to the next instance position in the column. y-coordinate must be \>= 0. | `None` |
| `x_space` | `um` | Spacing between the fill cell bounding boxes in x-direction. | `0` |
| `y_space` | `um` | Spacing between the fill cell bounding boxes in y-direction. | `0` |
| `tile_border` | `tuple[um, um]` | The tile border to consider for excludes | `(20, 20)` |
| `multi` | `bool` | Use the region\_fill\_multi strategy instead of single fill. | `False` |

# violations

Utilities to fix DRC violations.

`fix_spacing_tiled` uses `kdb.Region.space_check` to detect minimum space violations and then applies a fix.

## RegionOperator

Bases: `TileOutputReceiver`

Region collector. Just getst the tile and inserts it into the target cell.

### \_\_init\_\_

```
__init__() -> None
```

Initialization.

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

## fix\_spacing\_minkowski\_tiled

```
fix_spacing_minkowski_tiled(c: ProtoTKCell[Any], min_space: dbu, ref: LayerInfo | Region, n_threads: int | None = None, tile_size: tuple[um, um] | None = None, overlap: float = 2.2, smooth: dbu | None = None) -> kdb.Region
```

Fix min space issues by using a dilation &amp; erosion with a box.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `ProtoTKCell[Any]` | Input cell | *required* |
| `min_space` | `dbu` | Minimum space rule \[dbu\] | *required* |
| `ref` | `LayerInfo \| Region` | Input layer index or region | *required* |
| `n_threads` | `int \| None` | on how many threads to run the check simultaneously | `None` |
| `tile_size` | `tuple[um, um] \| None` | tuple determining the size of each sub tile (in um), should be big compared to the violation size. By default this will be at minimum 250 um or 25 times the violation size, whichever is bigger. | `None` |
| `overlap` | `float` | how many times bigger to make the tile border in relation to the violation size. Smaller than 1 can lead to errors | `2.2` |
| `smooth` | `dbu \| None` | Apply smoothening (simplifying) at the end if \> 0 | `None` |

Returns:

| Type | Description |
| --- | --- |
| `Region` | kdb.Region: Region containing the fixes for the violations |

## fix\_spacing\_sizing\_tiled

```
fix_spacing_sizing_tiled(c: ProtoTKCell[Any], min_space: dbu, layer: LayerInfo, n_threads: int | None = None, tile_size: tuple[um, um] | None = None, overlap: float = 2.2) -> kdb.Region
```

Fix min space issues by using a dilation &amp; erosion.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `ProtoTKCell[Any]` | Input cell | *required* |
| `min_space` | `dbu` | Minimum space rule \[dbu\] | *required* |
| `layer` | `LayerInfo` | Input layer | *required* |
| `n_threads` | `int \| None` | on how many threads to run the check simultaneously | `None` |
| `tile_size` | `tuple[um, um] \| None` | tuple determining the size of each sub tile (in um), should be big compared to the violation size. By default this will be at minimum 250 um or 25 times the violation size, whichever is bigger. | `None` |
| `overlap` | `float` | how many times bigger to make the tile border in relation to the violation size. Smaller than 1 can lead to errors | `2.2` |

Returns:

| Type | Description |
| --- | --- |
| `Region` | kdb.Region: Region containing the fixes for the violations |

## fix\_spacing\_tiled

```
fix_spacing_tiled(c: ProtoTKCell[Any], min_space: dbu, layer: LayerInfo, metrics: Metrics = kdb.Metrics.Euclidian, ignore_angle: float = 80, size_space_check: int = 5, n_threads: int = 4, tile_size: tuple[um, um] | None = None, overlap: float = 2.2, smooth_factor: float = 0.05) -> kdb.Region
```

```
fix_spacing_tiled(c: ProtoTKCell[Any], min_space: dbu, layer: LayerInfo, metrics: Metrics = kdb.Metrics.Euclidian, ignore_angle: float = 80, size_space_check: int = 5, n_threads: int = 4, tile_size: tuple[um, um] | None = None, overlap: float = 2.2, *, smooth_absolute: dbu) -> kdb.Region
```

```
fix_spacing_tiled(c: ProtoTKCell[Any], min_space: dbu, layer: LayerInfo, metrics: Metrics = kdb.Metrics.Euclidian, ignore_angle: float = 80, size_space_check: int = 5, n_threads: int | None = None, tile_size: tuple[um, um] | None = None, overlap: float = 2.2, smooth_factor: float = 0.05, smooth_absolute: dbu | None = None, smooth_keep_hv: bool = True) -> kdb.Region
```

Fix minimum space violations.

Fix min space issues by running a drc check on the input region and merging it with the affcted polygons.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `ProtoTKCell[Any]` | Input cell | *required* |
| `min_space` | `dbu` | Minimum space rule \[dbu\] | *required* |
| `layer` | `LayerInfo` | Input layer index | *required* |
| `metrics` | `Metrics` | The metrics to use to determine the violation edges | `Euclidian` |
| `ignore_angle` | `float` | ignore angles greater or equal to this angle | `80` |
| `size_space_check` | `int` | Sizing in dbu of the offending edges towards the polygons | `5` |
| `n_threads` | `int \| None` | on how many threads to run the check simultaneously | `None` |
| `tile_size` | `tuple[um, um] \| None` | tuple determining the size of each sub tile (in um), should be big compared to the violation size. By default this will be at minimum 250 um or 25 times the violation size, whichever is bigger. | `None` |
| `overlap` | `float` | how many times bigger to make the tile border in relation to the violation size. Smaller than 1 can lead to errors | `2.2` |
| `smooth_factor` | `float` | how big to smooth the resulting region in relation to the violation. 1 == the violation size. Set to 0 to disable | `0.05` |
| `smooth_absolute` | `dbu \| None` | If set will overwrite smooth with an an absolute value, not relative to the violation size. If set, this will disable smooth\_factor. \[dbu\] | `None` |
| `smooth_keep_hv` | `bool` | Keep horizontal and vertical vertices when smoothing. | `True` |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `fix` | `Region` | Region containing the fixes for the violations |

## fix\_width\_and\_spacing\_minkowski\_tiled

```
fix_width_and_spacing_minkowski_tiled(c: ProtoTKCell[Any], min_space: int, min_width: int, ref: LayerInfo | Region, n_threads: int | None = None, tile_size: tuple[um, um] | None = None, overlap: float = 2.2, smooth: dbu | None = None) -> kdb.Region
```

Fix min space and width issues by using a dilation &amp; erosion with a box.

The algorithm will dilate by min\_space, erode by min\_width + min\_space, and finally dilate by min\_width

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `ProtoTKCell[Any]` | Input cell | *required* |
| `min_space` | `int` | Minimum space rule \[dbu\] | *required* |
| `min_width` | `int` | Minimum width rule \[dbu\] | *required* |
| `ref` | `LayerInfo \| Region` | Input layer index or region | *required* |
| `n_threads` | `int \| None` | on how many threads to run the check simultaneously | `None` |
| `tile_size` | `tuple[um, um] \| None` | tuple determining the size of each sub tile (in um), should be big compared to the violation size. By default this will be at minimum 250 um or 25 times the violation size, whichever is bigger. | `None` |
| `overlap` | `float` | how many times bigger to make the tile border in relation to the violation size. Smaller than 1 can lead to errors (overlap\*min\_space) | `2.2` |
| `smooth` | `dbu \| None` | Apply smoothening (simplifying) at the end if \> 0 | `None` |

Returns:

| Type | Description |
| --- | --- |
| `Region` | kdb.Region: Region containing the fixes for the violations |

## fix\_width\_minkowski\_tiled

```
fix_width_minkowski_tiled(c: ProtoTKCell[Any], min_width: dbu, ref: LayerInfo | Region, n_threads: int | None = None, tile_size: tuple[um, um] | None = None, overlap: float = 2.2, smooth: dbu | None = None) -> kdb.Region
```

Fix min space issues by using a dilation &amp; erosion with a box.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `ProtoTKCell[Any]` | Input cell | *required* |
| `min_width` | `dbu` | Minimum width rule \[dbu\] | *required* |
| `ref` | `LayerInfo \| Region` | Input layer index or region | *required* |
| `n_threads` | `int \| None` | on how many threads to run the check simultaneously | `None` |
| `tile_size` | `tuple[um, um] \| None` | tuple determining the size of each sub tile (in um), should be big compared to the violation size. By default this will be at minimum 250 um or 25 times the violation size, whichever is bigger. | `None` |
| `overlap` | `float` | how many times bigger to make the tile border in relation to the violation size. Smaller than 1 can lead to errors | `2.2` |
| `smooth` | `dbu \| None` | Apply smoothening (simplifying) at the end if \> 0 | `None` |

Returns:

| Type | Description |
| --- | --- |
| `Region` | kdb.Region: Region containing the fixes for the violations |

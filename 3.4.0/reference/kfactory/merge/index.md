# merge

## MergeDiff

Dataclass to hold geometric info about the layout diff.

### loglevel

```
loglevel: LogLevel | int = field(default=LogLevel.CRITICAL)
```

Log level at which to log polygon errors.

### \_\_post\_init\_\_

```
__post_init__() -> None
```

Initialize the DiffInfo.

### compare

```
compare() -> bool
```

Run the comparing.

Returns: True if there are differences, nothing otherwise

### on\_begin\_cell

```
on_begin_cell(cell_a: Cell, cell_b: Cell) -> None
```

Set the cells to the new cell.

### on\_begin\_layer

```
on_begin_layer(layer: LayerInfo, layer_a: int, layer_b: int) -> None
```

Set the layers to the new layer.

### on\_cell\_meta\_info\_differs

```
on_cell_meta_info_differs(name: str, meta_a: LayoutMetaInfo | None, meta_b: LayoutMetaInfo | None) -> None
```

Called when there is a difference in meta infos of cells.

### on\_dbu\_differs

```
on_dbu_differs(dbu_a: float, dbu_b: float) -> None
```

Called when the DBU differs between the two layouts.

### on\_end\_layer

```
on_end_layer() -> None
```

Before switching to a new layer, copy the xor to the xor layout.

### on\_instance\_in\_a\_only

```
on_instance_in_a_only(instance: CellInstArray, propid: int) -> None
```

Called when there is only an instance in the cell\_a.

### on\_instance\_in\_b\_only

```
on_instance_in_b_only(instance: CellInstArray, propid: int) -> None
```

Called when there is only an instance in the cell\_b.

### on\_polygon\_in\_a\_only

```
on_polygon_in_a_only(poly: Polygon, propid: int) -> None
```

Called when there is only a polygon in the cell\_a.

### on\_polygon\_in\_b\_only

```
on_polygon_in_b_only(poly: Polygon, propid: int) -> None
```

Called when there is only a polygon in the cell\_b.

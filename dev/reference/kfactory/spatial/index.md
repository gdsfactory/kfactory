# spatial

Shared spatial-query helpers for bbox pruning and cached region extraction.

## collect\_instance\_region

```
collect_instance_region(cell: ProtoTKCell[Any] | Cell, layer: int, inst: ProtoTInstance[Any]) -> kdb.Region
```

Collect the actual geometry region for one instance on one layer.

Shapes without a polygon (e.g. texts) are skipped.

## iter\_overlapping\_bbox\_pairs

```
iter_overlapping_bbox_pairs(boxes: Sequence[Box]) -> Iterator[tuple[int, int]]
```

Yield index pairs whose bounding boxes overlap.

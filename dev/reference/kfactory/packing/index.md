# packing

Utilities for packing KCells and Instances.

## pack\_instances

```
pack_instances(target: KCell, instances: Sequence[Instance], max_width: int | None = None, max_height: int | None = None, spacing: int = 0) -> InstanceGroup
```

Pack KCells.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `target` | `KCell` | KCell to place the packed instances in. | *required* |
| `instances` | `Sequence[Instance]` | Sequence of Instances to pack. | *required* |
| `max_width` | `int \| None` | Maximum width of the packed rectangle | `None` |
| `max_height` | `int \| None` | Maximum height of the packed rectangle | `None` |
| `spacing` | `int` | Spacing between the instance bboxes | `0` |

## pack\_kcells

```
pack_kcells(target: KCell, kcells: Sequence[KCell], max_width: int | None = None, max_height: int | None = None, spacing: int = 0) -> InstanceGroup
```

Pack KCells.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `target` | `KCell` | KCell to place the packed instances in. | *required* |
| `kcells` | `Sequence[KCell]` | Sequence of KCells from which to create instances. | *required* |
| `max_width` | `int \| None` | Maximum width of the packed rectangle | `None` |
| `max_height` | `int \| None` | Maximum height of the packed rectangle | `None` |
| `spacing` | `int` | Spacing between the instance bboxes | `0` |

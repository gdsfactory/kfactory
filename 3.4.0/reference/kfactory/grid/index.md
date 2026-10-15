# grid

Create 1D or 2D (flex) grids in KCells.

## flexgrid

```
flexgrid(target: ProtoTKCell[Any], kcells: Sequence[DKCell | None] | Sequence[Sequence[DKCell | None]], spacing: float | tuple[float, float], target_trans: DCplxTrans | None = None, shape: tuple[int, int] | None = None, align_x: Literal['origin', 'xmin', 'xmax', 'center'] = 'center', align_y: Literal['origin', 'ymin', 'ymax', 'center'] = 'center', rotation: float = 0, mirror: bool = False) -> DInstanceGroup
```

Create a grid of instances.

A grid uses the bounding box of the biggest width per column and biggest height per row of any bounding boxes inserted into the grid. To this bounding box a spacing is applied in x and y.

```
                     spacing[0] or spacing
                    ◄─►
 ┌──────────────────┐ ┌──┬─────┬──┐ ┌──────────┐ ┌──────────┐▲
 │                  │ │  │     │  │ │          │ │          ││
 │   ┌────┐         │ │  │     │  │ │          │ │   ┌──────┼│
 │   │    │         │ │  │     │  │ │          │ │   │      ││
 │   │    │         │ │  │ big │  │ │  ┌───────┤ │   │      ││
 │   │ ▼  │         │ │  │ comp│  │ │  │       │ │   │      ││
 │   │    │         │ │  │ y   │  │ │  │       │ │   │  ▼   ││
 │   │    │         │ │  │     │  │ │  │  ▼    │ │   │      ││ y[1]
 │   └────┘         │ │  │ ▼   │  │ │  │       │ │   │      ││
 │                  │ │  │     │  │ │  │       │ │   │      ││
 │                  │ │  │     │  │ │  │       │ │   └──────┼│
 │                  │ │  │     │  │ │  │       │ │          ││
 │                  │ │  │     │  │ │  └───────┤ │          ││
 │                  │ │  │     │  │ │          │ │          ││
▲└──────────────────┘ └──┴─────┴──┘ └──────────┘ └──────────┘▼
│spacing[1] or spacing
▼┌──────────────────┐ ┌───────────┐ ┌────┬─────┐ ┌───┬──────┐▲
 ├──────────────────┤ ├───────────┤ │    │     │ │   │      ││
 │                  │ │           │ │    │     │ │   │      ││
 │              ▼   │ │           │ │    │     │ │   │      ││
 │   big comp x     │ │           │ │    │     │ │   │      ││
 │                  │ │    ▼      │ │  ▼ │     │ │ ▼ │      ││ y[0]
 ├──────────────────┤ │           │ │    │     │ │   │      ││
 │                  │ │           │ │    │     │ │   │      ││
 │                  │ │           │ │    │     │ │   │      ││
 │                  │ │           │ │    │     │ │   │      ││
 └──────────────────┴─┴───────────┴─┴────┼─────┴─┴───┼──────┘►
 ►──────────────────► ►───────────► ►──────────► ►──────────►
         x[0]               x[1]        x[2]         x[3]
```

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `target` | `ProtoTKCell[Any]` | Target DKCell. | *required* |
| `kcells` | `Sequence[DKCell \| None] \| Sequence[Sequence[DKCell \| None]]` | Sequence or sequence of sequence of DKCells to add to the grid | *required* |
| `spacing` | `float \| tuple[float, float]` | Value or tuple of value (different x/y) for spacing of the grid. | *required* |
| `target_trans` | `DCplxTrans \| None` | Apply a transformation to the whole grid before placing it. | `None` |
| `shape` | `tuple[int, int] \| None` | Respace the input of kcells into an array and fill as many positions (first x then y). | `None` |
| `align_x` | `Literal['origin', 'xmin', 'xmax', 'center']` | Align all the instance on the x-coordinate. | `'center'` |
| `align_y` | `Literal['origin', 'ymin', 'ymax', 'center']` | Align all the instance on the y-coordinate. | `'center'` |
| `rotation` | `float` | Apply a rotation to each kcells instance before adding it to the grid. | `0` |
| `mirror` | `bool` | Mirror the instances before placing them in the grid | `False` |

## flexgrid\_dbu

```
flexgrid_dbu(target: ProtoTKCell[Any], kcells: Sequence[KCell | None] | Sequence[Sequence[KCell | None]], spacing: int | tuple[int, int], target_trans: Trans | None = None, shape: tuple[int, int] | None = None, align_x: Literal['origin', 'xmin', 'xmax', 'center'] = 'center', align_y: Literal['origin', 'ymin', 'ymax', 'center'] = 'center', rotation: Literal[0, 1, 2, 3] = 0, mirror: bool = False) -> InstanceGroup
```

Create a grid of instances.

A grid uses the bounding box of the biggest width per column and biggest height per row of any bounding boxes inserted into the grid. To this bounding box a spacing is applied in x and y.

```
                     spacing[0] or spacing
                    ◄─►
 ┌──────────────────┐ ┌──┬─────┬──┐ ┌──────────┐ ┌──────────┐▲
 │                  │ │  │     │  │ │          │ │          ││
 │   ┌────┐         │ │  │     │  │ │          │ │   ┌──────┼│
 │   │    │         │ │  │     │  │ │          │ │   │      ││
 │   │    │         │ │  │ big │  │ │  ┌───────┤ │   │      ││
 │   │ ▼  │         │ │  │ comp│  │ │  │       │ │   │      ││
 │   │    │         │ │  │ y   │  │ │  │       │ │   │  ▼   ││
 │   │    │         │ │  │     │  │ │  │  ▼    │ │   │      ││ y[1]
 │   └────┘         │ │  │ ▼   │  │ │  │       │ │   │      ││
 │                  │ │  │     │  │ │  │       │ │   │      ││
 │                  │ │  │     │  │ │  │       │ │   └──────┼│
 │                  │ │  │     │  │ │  │       │ │          ││
 │                  │ │  │     │  │ │  └───────┤ │          ││
 │                  │ │  │     │  │ │          │ │          ││
▲└──────────────────┘ └──┴─────┴──┘ └──────────┘ └──────────┘▼
│spacing[1] or spacing
▼┌──────────────────┐ ┌───────────┐ ┌────┬─────┐ ┌───┬──────┐▲
 ├──────────────────┤ ├───────────┤ │    │     │ │   │      ││
 │                  │ │           │ │    │     │ │   │      ││
 │              ▼   │ │           │ │    │     │ │   │      ││
 │   big comp x     │ │           │ │    │     │ │   │      ││
 │                  │ │    ▼      │ │  ▼ │     │ │ ▼ │      ││ y[0]
 ├──────────────────┤ │           │ │    │     │ │   │      ││
 │                  │ │           │ │    │     │ │   │      ││
 │                  │ │           │ │    │     │ │   │      ││
 │                  │ │           │ │    │     │ │   │      ││
 └──────────────────┴─┴───────────┴─┴────┼─────┴─┴───┼──────┘►
 ►──────────────────► ►───────────► ►──────────► ►──────────►
         x[0]               x[1]        x[2]         x[3]
```

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `target` | `ProtoTKCell[Any]` | Target KCell. | *required* |
| `kcells` | `Sequence[KCell \| None] \| Sequence[Sequence[KCell \| None]]` | Sequence or sequence of sequence of KCells to add to the grid | *required* |
| `spacing` | `int \| tuple[int, int]` | Value or tuple of value (different x/y) for spacing of the grid. \[dbu\] | *required* |
| `target_trans` | `Trans \| None` | Apply a transformation to the whole grid before placing it. | `None` |
| `shape` | `tuple[int, int] \| None` | Respace the input of kcells into an array and fill as many positions (first x then y). | `None` |
| `align_x` | `Literal['origin', 'xmin', 'xmax', 'center']` | Align all the instance on the x-coordinate. | `'center'` |
| `align_y` | `Literal['origin', 'ymin', 'ymax', 'center']` | Align all the instance on the y-coordinate. | `'center'` |
| `rotation` | `Literal[0, 1, 2, 3]` | Apply a rotation to each kcells instance before adding it to the grid. | `0` |
| `mirror` | `bool` | Mirror the instances before placing them in the grid | `False` |

## grid

```
grid(target: ProtoTKCell[Any], kcells: Sequence[DKCell | None] | Sequence[Sequence[DKCell | None]], spacing: float | tuple[float, float], target_trans: DCplxTrans | None = None, shape: tuple[int, int] | None = None, align_x: Literal['origin', 'xmin', 'xmax', 'center'] = 'center', align_y: Literal['origin', 'ymin', 'ymax', 'center'] = 'center', rotation: float = 0, mirror: bool = False) -> DInstanceGroup
```

Create a grid of instances.

A grid uses the bounding box of the biggest width and biggest height of any bounding boxes inserted into the grid. to this bounding box a spacing is applied in x and y.

```
                      spacing[0] or spacing
                     ◄─►
  ┌──────────────────┐ ┌────┬─────┬─────┐ ┌────────────────┐ ┌──────────────────┐ ▲
  │                  │ │    │     │     │ │                │ │                  │ │
  │   ┌────┐         │ │    │     │     │ │                │ │      ┌──────┐    │ │
  │   │    │         │ │    │     │     │ │                │ │      │      │    │ │
  │   │    │         │ │    │ big │     │ │    ┌───────┐   │ │      │      │    │ │
  │   │    │         │ │    │ comp│     │ │    │       │   │ │      │      │    │ │
  │   │    │         │ │    │ y   │     │ │    │       │   │ │      │      │    │ │
  │   │    │         │ │    │     │     │ │    │       │   │ │      │     max bbox y
  │   └────┘         │ │    │     │     │ │    │       │   │ │      │      │    │ │
  │                  │ │    │     │     │ │    │       │   │ │      │      │    │ │
  │                  │ │    │     │     │ │    │       │   │ │      └──────┘    │ │
  │                  │ │    │     │     │ │    │       │   │ │                  │ │
  │                  │ │    │     │     │ │    └───────┘   │ │                  │ │
  │                  │ │    │     │     │ │                │ │                  │ │
 ▲└──────────────────┘ └────┴─────┴─────┘ └────────────────┘ └──────────────────┘ ▼
 │spacing[1] or spacing
 ▼┌──────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────────┐
  │                  │ │                │ │                │ │                  │
  │                  │ │                │ │ ┌────┐         │ │  ┌───┐           │
  ├──────────────────┤ │ ┌───────────┐  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │   big comp x     │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  ├──────────────────┤ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ └───────────┘  │ │ └────┘         │ │  └───┘           │
  │                  │ │                │ │                │ │                  │
  └──────────────────┘ └────────────────┘ └────────────────┘ └──────────────────┘

                                                             ◄──────────────────►
                                                                max bbox x
```

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `target` | `ProtoTKCell[Any]` | Target DKCell. | *required* |
| `kcells` | `Sequence[DKCell \| None] \| Sequence[Sequence[DKCell \| None]]` | Sequence or sequence of sequence of DKCells to add to the grid | *required* |
| `spacing` | `float \| tuple[float, float]` | Value or tuple of value (different x/y) for spacing of the grid. \[um\] | *required* |
| `target_trans` | `DCplxTrans \| None` | Apply a transformation to the whole grid before placing it. | `None` |
| `shape` | `tuple[int, int] \| None` | Respace the input of kcells into an array and fill as many positions (first x then y). | `None` |
| `align_x` | `Literal['origin', 'xmin', 'xmax', 'center']` | Align all the instance on the x-coordinate. | `'center'` |
| `align_y` | `Literal['origin', 'ymin', 'ymax', 'center']` | Align all the instance on the y-coordinate. | `'center'` |
| `rotation` | `float` | Apply a rotation to each kcells instance before adding it to the grid. | `0` |
| `mirror` | `bool` | Mirror the instances before placing them in the grid | `False` |

## grid\_dbu

```
grid_dbu(target: ProtoTKCell[Any], kcells: Sequence[KCell | None] | Sequence[Sequence[KCell | None]], spacing: int | tuple[int, int], target_trans: Trans | None = None, shape: tuple[int, int] | None = None, align_x: Literal['origin', 'xmin', 'xmax', 'center'] = 'center', align_y: Literal['origin', 'ymin', 'ymax', 'center'] = 'center', rotation: Literal[0, 1, 2, 3] = 0, mirror: bool = False) -> InstanceGroup
```

Create a grid of instances.

A grid uses the bounding box of the biggest width and biggest height of any bounding boxes inserted into the grid. to this bounding box a spacing is applied in x and y.

```
                      spacing[0] or spacing
                     ◄─►
  ┌──────────────────┐ ┌────┬─────┬─────┐ ┌────────────────┐ ┌──────────────────┐ ▲
  │                  │ │    │     │     │ │                │ │                  │ │
  │   ┌────┐         │ │    │     │     │ │                │ │      ┌──────┐    │ │
  │   │    │         │ │    │     │     │ │                │ │      │      │    │ │
  │   │    │         │ │    │ big │     │ │    ┌───────┐   │ │      │      │    │ │
  │   │    │         │ │    │ comp│     │ │    │       │   │ │      │      │    │ │
  │   │    │         │ │    │ y   │     │ │    │       │   │ │      │      │    │ │
  │   │    │         │ │    │     │     │ │    │       │   │ │      │     max bbox y
  │   └────┘         │ │    │     │     │ │    │       │   │ │      │      │    │ │
  │                  │ │    │     │     │ │    │       │   │ │      │      │    │ │
  │                  │ │    │     │     │ │    │       │   │ │      └──────┘    │ │
  │                  │ │    │     │     │ │    │       │   │ │                  │ │
  │                  │ │    │     │     │ │    └───────┘   │ │                  │ │
  │                  │ │    │     │     │ │                │ │                  │ │
 ▲└──────────────────┘ └────┴─────┴─────┘ └────────────────┘ └──────────────────┘ ▼
 │spacing[1] or spacing
 ▼┌──────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────────┐
  │                  │ │                │ │                │ │                  │
  │                  │ │                │ │ ┌────┐         │ │  ┌───┐           │
  ├──────────────────┤ │ ┌───────────┐  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │   big comp x     │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  ├──────────────────┤ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ │           │  │ │ │    │         │ │  │   │           │
  │                  │ │ └───────────┘  │ │ └────┘         │ │  └───┘           │
  │                  │ │                │ │                │ │                  │
  └──────────────────┘ └────────────────┘ └────────────────┘ └──────────────────┘

                                                             ◄──────────────────►
                                                                max bbox x
```

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `target` | `ProtoTKCell[Any]` | Target KCell. | *required* |
| `kcells` | `Sequence[KCell \| None] \| Sequence[Sequence[KCell \| None]]` | Sequence or sequence of sequence of KCells to add to the grid | *required* |
| `spacing` | `int \| tuple[int, int]` | Value or tuple of value (different x/y) for spacing of the grid. \[dbu\] | *required* |
| `target_trans` | `Trans \| None` | Apply a transformation to the whole grid before placing it. | `None` |
| `shape` | `tuple[int, int] \| None` | Respace the input of kcells into an array and fill as many positions (first x then y). | `None` |
| `align_x` | `Literal['origin', 'xmin', 'xmax', 'center']` | Align all the instance on the x-coordinate. | `'center'` |
| `align_y` | `Literal['origin', 'ymin', 'ymax', 'center']` | Align all the instance on the y-coordinate. | `'center'` |
| `rotation` | `Literal[0, 1, 2, 3]` | Apply a rotation to each kcells instance before adding it to the grid. | `0` |
| `mirror` | `bool` | Mirror the instances before placing them in the grid | `False` |

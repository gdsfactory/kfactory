# bezier

Bezier curve based bends and functions.

## BezierFactory

Bases: `Protocol[KC_co]`

### \_\_call\_\_

```
__call__(*, height: um, length: um, nb_points: int = 99, t_start: float = 0, t_stop: float = 1, cross_section: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width: um | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> KC_co
```

Create a bezier bend.

Either pass a `cross_section` or the legacy `width`/`layer`/`enclosure`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `height` | `um` | height difference of left/right. \[um\] | *required* |
| `length` | `um` | Length of the bend. \[um\] | *required* |
| `nb_points` | `int` | Number of points of the backbone. | `99` |
| `t_start` | `float` | start | `0` |
| `t_stop` | `float` | end | `1` |
| `cross_section` | `str \| AnyCrossSectionInput \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the bend. | `None` |
| `width` | `um \| None` | Width of the core. \[um\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Layer index of the core. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Slab/Exclude definition. (legacy) | `None` |

## bend\_s\_bezier\_factory

```
bend_s_bezier_factory(kcl: KCLayout, *, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BezierFactory[KCell]
```

```
bend_s_bezier_factory(kcl: KCLayout, *, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, output_type: type[KC], port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BezierFactory[KC]
```

```
bend_s_bezier_factory(kcl: KCLayout, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, output_type: type[KC] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BezierFactory[KC]
```

Returns a function generating bezier s-bends (generic interface).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout which will be owned | *required* |
| `additional_info` | `Callable[..., dict[str, MetaData]] \| dict[str, MetaData] \| None` | Add additional key/values to the `KCell.info`. Can be a static dict mapping info name to info value. Or can a callable which takes the bend functions' parameters as kwargs and returns a dict with the mapping. | `None` |
| `cell_kwargs` | `Unpack[CellKWargs]` | Additional arguments passed as `@kcl.cell(**cell_kwargs)`. | `{}` |

## bezier\_curve

```
bezier_curve(t: NDArray[floating[Any]], control_points: Sequence[tuple[float64 | float, float64 | float]]) -> list[kdb.DPoint]
```

Calculates the backbone of a bezier bend.

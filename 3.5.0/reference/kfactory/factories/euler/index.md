# euler

Euler bends.

Euler bends are bends with a constantly changing radius from zero to a maximum radius and back to 0 at the other end.

There are two kinds of euler bends. One that snaps the ports and one that doesn't. All the default bends use snapping. To use no snapping make an instance of BendEulerCustom(KCell.kcl) and use that one.

## BendEulerFactory

Bases: `Protocol[KC_co]`

### \_\_call\_\_

```
__call__(*, radius: um, angle: deg = 90, resolution: float = 150, cross_section: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width: um | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> KC_co
```

Create a euler bend.

Either pass a `cross_section` or the legacy `width`/`layer`/`enclosure`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `radius` | `um` | Radius off the backbone. \[um\] | *required* |
| `angle` | `deg` | Angle of the bend. | `90` |
| `resolution` | `float` | Angle resolution for the backbone. | `150` |
| `cross_section` | `str \| AnyCrossSectionInput \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the bend. | `None` |
| `width` | `um \| None` | Width of the core. \[um\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Main layer of the bend. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Slab/exclude definition. (legacy) | `None` |

## BendSEulerFactory

Bases: `Protocol[KC_co]`

### \_\_call\_\_

```
__call__(*, offset: um, radius: um, resolution: float = 150, cross_section: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width: um | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> KC_co
```

Create a euler s-bend.

Either pass a `cross_section` or the legacy `width`/`layer`/`enclosure`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `offset` | `um` | Offset between left/right. \[um\] | *required* |
| `radius` | `um` | Radius off the backbone. \[um\] | *required* |
| `resolution` | `float` | Angle resolution for the backbone. | `150` |
| `cross_section` | `str \| AnyCrossSectionInput \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the bend. | `None` |
| `width` | `um \| None` | Width of the core. \[um\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Main layer of the bend. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Slab/exclude definition. (legacy) | `None` |

## bend\_euler\_factory

```
bend_euler_factory(kcl: KCLayout, *, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BendEulerFactory[KCell]
```

```
bend_euler_factory(kcl: KCLayout, *, output_type: type[KC], additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BendEulerFactory[KC]
```

```
bend_euler_factory(kcl: KCLayout, *, output_type: type[KC] | None = None, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BendEulerFactory[KC]
```

Returns a function generating euler bends.

The returned function is the generic interface (`cross_section` or the legacy `width`/`layer`/`enclosure`). Will snap ports by default.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout which will be owned | *required* |
| `additional_info` | `Callable[..., dict[str, MetaData]] \| dict[str, MetaData] \| None` | Add additional key/values to the `KCell.info`. Can be a static dict mapping info name to info value. Or can a callable which takes the bend functions' parameters as kwargs and returns a dict with the mapping. | `None` |
| `cell_kwargs` | `Unpack[CellKWargs]` | Additional arguments passed as `@kcl.cell(**cell_kwargs)`. | `{}` |

## bend\_s\_euler\_factory

```
bend_s_euler_factory(kcl: KCLayout, *, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BendSEulerFactory[KCell]
```

```
bend_s_euler_factory(kcl: KCLayout, *, output_type: type[KC], additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BendSEulerFactory[KC]
```

```
bend_s_euler_factory(kcl: KCLayout, output_type: type[KC] | None = None, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BendSEulerFactory[KC]
```

Returns a function generating euler s-bends (generic interface).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout which will be owned | *required* |
| `additional_info` | `Callable[..., dict[str, MetaData]] \| dict[str, MetaData] \| None` | Add additional key/values to the `KCell.info`. Can be a static dict mapping info name to info value. Or can a callable which takes the bend functions' parameters as kwargs and returns a dict with the mapping. | `None` |
| `cell_kwargs` | `Unpack[CellKWargs]` | Additional arguments passed as `@kcl.cell(**cell_kwargs)`. | `{}` |

## euler\_bend\_points

```
euler_bend_points(angle_amount: deg = 90, radius: um = 100, resolution: float = 150) -> list[kdb.DPoint]
```

Base euler bend, no transformation, emerging from the origin.

## euler\_endpoint

```
euler_endpoint(start_point: tuple[float, float] = (0.0, 0.0), radius: um = 10.0, input_angle: deg = 0.0, angle_amount: deg = 90.0) -> tuple[float, float]
```

Gives the end point of a simple Euler bend as a i3.Coord2.

## euler\_sbend\_points

```
euler_sbend_points(offset: um = 5.0, radius: um = 1e-05, resolution: float = 150) -> list[kdb.DPoint]
```

An Euler s-bend with parallel input and output, separated by an offset.

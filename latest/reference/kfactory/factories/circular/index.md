# circular

Circular bends.

A circular bend has a constant radius.

## BendCircularFactory

Bases: `Protocol[KC_co]`

### \_\_call\_\_

```
__call__(*, radius: um, angle: deg = 90, angle_step: deg = 1, cross_section: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width: um | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> KC_co
```

Circular radius bend \[um\].

Either pass a `cross_section` (name, spec, or instance) or the legacy `width`/`layer`/`enclosure` which is normalized into a cross section.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `radius` | `um` | Radius of the backbone. \[um\] | *required* |
| `angle` | `deg` | Angle amount of the bend. | `90` |
| `angle_step` | `deg` | Angle amount per backbone point of the bend. | `1` |
| `cross_section` | `str \| AnyCrossSectionInput \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the bend. | `None` |
| `width` | `um \| None` | Width of the core. \[um\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Main layer of the bend. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Optional enclosure. (legacy) | `None` |

## bend\_circular\_factory

```
bend_circular_factory(kcl: KCLayout, *, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BendCircularFactory[KCell]
```

```
bend_circular_factory(kcl: KCLayout, *, output_type: type[KC], additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BendCircularFactory[KC]
```

```
bend_circular_factory(kcl: KCLayout, *, output_type: type[KC] | None = None, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> BendCircularFactory[KC]
```

Returns a function generating circular bends.

The returned function is the generic interface: it accepts either a `cross_section` or the legacy `width`/`layer`/`enclosure` (normalized into a symmetric cross section). Will snap ports by default.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout which will be owned | *required* |
| `additional_info` | `Callable[..., dict[str, MetaData]] \| dict[str, MetaData] \| None` | Add additional key/values to the `KCell.info`. Can be a static dict mapping info name to info value. Or can a callable which takes the bend functions' parameters as kwargs and returns a dict with the mapping. | `None` |
| `cell_kwargs` | `Unpack[CellKWargs]` | Additional arguments passed as `@kcl.cell(**cell_kwargs)`. | `{}` |

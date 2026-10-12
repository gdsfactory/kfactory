# circular

Virtual circular cell factories.

## BendCircularVKCell

Bases: `Protocol`

Factory for virtual circular bend.

### \_\_call\_\_

```
__call__(*, radius: um, angle: deg = 90, angle_step: float = 1, cross_section: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width: um | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> VKCell
```

Create a virtual circular bend.

Either pass a `cross_section` or the legacy `width`/`layer`/`enclosure`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `radius` | `um` | Radius of the backbone. \[um\] | *required* |
| `angle` | `deg` | Angle amount of the bend. | `90` |
| `angle_step` | `float` | Angle amount per backbone point of the bend. | `1` |
| `cross_section` | `str \| AnyCrossSectionInput \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the bend. | `None` |
| `width` | `um \| None` | Width of the core. \[um\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Main layer of the bend. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Optional enclosure. (legacy) | `None` |

## virtual\_bend\_circular\_factory

```
virtual_bend_circular_factory(kcl: KCLayout, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, basename: str | None = None, **cell_kwargs: Any) -> BendCircularVKCell
```

Returns a function generating virtual circular bends.

The returned function is the generic interface (`cross_section` or the legacy `width`/`layer`/`enclosure`).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout which will be owned | *required* |
| `additional_info` | `Callable[..., dict[str, MetaData]] \| dict[str, MetaData] \| None` | Add additional key/values to the `VKCell.info`. Can be a static dict mapping info name to info value. Or can a callable which takes the bend functions' parameters as kwargs and returns a dict with the mapping. | `None` |
| `basename` | `str \| None` | Overwrite the prefix of the resulting VKCell's name. By default the VKCell will be named 'virtual\_bend\_circular\[...\]'. | `None` |
| `cell_kwargs` | `Any` | Additional arguments passed as `@kcl.vcell(**cell_kwargs)`. | `{}` |

# euler

Virtual euler cell factories.

## BendEulerVKCell

Bases: `Protocol`

Factory for virtual euler bends.

### \_\_call\_\_

```
__call__(*, radius: um, angle: deg = 90, resolution: float = 150, cross_section: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width: um | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> VKCell
```

Create a virtual euler bend.

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

## virtual\_bend\_euler\_factory

```
virtual_bend_euler_factory(kcl: KCLayout, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, basename: str | None = None, **cell_kwargs: Any) -> BendEulerVKCell
```

Returns a function generating virtual euler bends.

The returned function is the generic interface (`cross_section` or the legacy `width`/`layer`/`enclosure`).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout which will be owned | *required* |
| `additional_info` | `Callable[..., dict[str, MetaData]] \| dict[str, MetaData] \| None` | Add additional key/values to the `VKCell.info`. Can be a static dict mapping info name to info value. Or can a callable which takes the bend functions' parameters as kwargs and returns a dict with the mapping. | `None` |
| `basename` | `str \| None` | Overwrite the prefix of the resulting VKCell's name. By default the VKCell will be named 'bend\_euler\[...\]'. | `None` |
| `cell_kwargs` | `Any` | Additional arguments passed as `@kcl.vcell(**cell_kwargs)`. | `{}` |

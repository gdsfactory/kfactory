# straight

Straight virtual straight waveguide cell factories.

## StraightVKCell

Bases: `Protocol`

### \_\_call\_\_

```
__call__(*, length: um, cross_section: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width: um | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> VKCell
```

Virtual straight waveguide defined in um.

```
┌──────────────────────────────┐
│         Slab/Exclude         │
├──────────────────────────────┤
│                              │
│             Core             │
│                              │
├──────────────────────────────┤
│         Slab/Exclude         │
└──────────────────────────────┘
```

Either pass a `cross_section` or the legacy `width`/`layer`/`enclosure`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `length` | `um` | Waveguide length. \[um\] | *required* |
| `cross_section` | `str \| AnyCrossSectionInput \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the waveguide. | `None` |
| `width` | `um \| None` | Waveguide width. \[um\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Main layer of the waveguide. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Definition of slab/excludes. (legacy) | `None` |

## virtual\_straight\_factory

```
virtual_straight_factory(kcl: KCLayout, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, basename: str | None = None, **cell_kwargs: Any) -> StraightVKCell
```

Returns a function generating virtual straight waveguides.

The returned function is the generic interface: it accepts either a `cross_section` or the legacy `width`/`layer`/`enclosure` (all um), normalized into a symmetric cross section.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout which will be owned | *required* |
| `additional_info` | `Callable[..., dict[str, MetaData]] \| dict[str, MetaData] \| None` | Add additional key/values to the `VKCell.info`. Can be a static dict mapping info name to info value. Or can a callable which takes the straight functions' parameters as kwargs and returns a dict with the mapping. | `None` |
| `basename` | `str \| None` | Overwrite the prefix of the resulting VKCell's name. By default the VKCell will be named 'virtual\_straight\[...\]'. | `None` |
| `cell_kwargs` | `Any` | Additional arguments passed as `@kcl.vcell(**cell_kwargs)`. | `{}` |

# straight

Straight waveguide in dbu.

A waveguide is a rectangle of material with excludes and/or slab around it::

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

The slabs and excludes are part of the cross section the waveguide is built from.

## StraightFactory

Bases: `Protocol[KC_co]`

### \_\_call\_\_

```
__call__(*, length: dbu, cross_section: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width: dbu | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> KC_co
```

Waveguide defined by a cross section, length in dbu.

Either pass a `cross_section` (name, spec, or instance) or the legacy `width`/`layer`/`enclosure` (all dbu) which is normalized into a cross section.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `length` | `dbu` | Waveguide length. \[dbu\] | *required* |
| `cross_section` | `str \| AnyCrossSectionInput \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the waveguide. | `None` |
| `width` | `dbu \| None` | Waveguide width. \[dbu\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Main layer of the waveguide. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Definition of slab/excludes. \[dbu\] (legacy) | `None` |

## straight\_dbu\_factory

```
straight_dbu_factory(kcl: KCLayout, *, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> StraightFactory[KCell]
```

```
straight_dbu_factory(kcl: KCLayout, *, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, output_type: type[KC], port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> StraightFactory[KC]
```

```
straight_dbu_factory(kcl: KCLayout, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, output_type: type[KC] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> StraightFactory[KC]
```

Returns a function generating straights \[dbu length\].

The returned function is the generic interface: it accepts either a `cross_section` or the legacy `width`/`layer`/`enclosure` (all dbu), normalized into a symmetric cross section.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout which will be owned | *required* |
| `additional_info` | `Callable[..., dict[str, MetaData]] \| dict[str, MetaData] \| None` | Add additional key/values to the `KCell.info`. Can be a static dict mapping info name to info value. Or can a callable which takes the straight functions' parameters as kwargs and returns a dict with the mapping. | `None` |
| `cell_kwargs` | `Unpack[CellKWargs]` | Additional arguments passed as `@kcl.cell(**cell_kwargs)`. | `{}` |

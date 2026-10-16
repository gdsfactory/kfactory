# taper

Taper definitions \[dbu\].

A linear taper transitions between two cross sections (two core widths) over a given length::

```
       __
     _/  │ Slab/Exclude
   _/  __│
 _/  _/  │
│  _/    │
│_/      │
│_       │ Core
│ \_     │
│_  \_   │
  \_  \__│
    \_   │
      \__│ Slab/Exclude
```

The slabs and excludes are part of the cross sections the taper is built from, or can be given for the legacy `(width1, width2, layer, enclosure)` call.

TODO: Non-linear tapers

## TaperFactory

Bases: `Protocol[KC_co]`

### \_\_call\_\_

```
__call__(*, length: dbu, cross_section1: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, cross_section2: str | AnyCrossSectionInput | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width1: dbu | None = None, width2: dbu | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> KC_co
```

Linear Taper \[dbu\].

```
       __
     _/  │ Slab/Exclude
   _/  __│
 _/  _/  │
│  _/    │
│_/      │
│_       │ Core
│ \_     │
│_  \_   │
  \_  \__│
    \_   │
      \__│ Slab/Exclude
```

Either pass two cross sections (`cross_section1`/`cross_section2`) or the legacy `width1`/`width2`/`layer`/`enclosure` (all dbu) which is normalized into a pair of symmetric cross sections.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `length` | `dbu` | Length of the taper. \[dbu\] | *required* |
| `cross_section1` | `str \| AnyCrossSectionInput \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the left side. | `None` |
| `cross_section2` | `str \| AnyCrossSectionInput \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the right side. | `None` |
| `width1` | `dbu \| None` | Width of the core on the left side. \[dbu\] (legacy; requires `layer`) | `None` |
| `width2` | `dbu \| None` | Width of the core on the right side. \[dbu\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Main layer of the taper. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Definition of the slab/exclude. (legacy) | `None` |

## taper\_factory

```
taper_factory(kcl: KCLayout, *, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> TaperFactory[KCell]
```

```
taper_factory(kcl: KCLayout, *, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, output_type: type[KC], port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> TaperFactory[KC]
```

```
taper_factory(kcl: KCLayout, additional_info: Callable[..., dict[str, MetaData]] | dict[str, MetaData] | None = None, output_type: type[KC] | None = None, port_type: str = 'optical', **cell_kwargs: Unpack[CellKWargs]) -> TaperFactory[KC]
```

Returns a function generating linear tapers \[dbu\].

```
       __
     _/  │ Slab/Exclude
   _/  __│
 _/  _/  │
│  _/    │
│_/      │
│_       │ Core
│ \_     │
│_  \_   │
  \_  \__│
    \_   │
      \__│ Slab/Exclude
```

The returned function is the generic interface: it accepts either two cross sections (`cross_section1`/`cross_section2`) or the legacy `width1`/`width2`/`layer`/`enclosure` (all dbu), normalized into a pair of symmetric cross sections.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `kcl` | `KCLayout` | The KCLayout which will be owned | *required* |
| `additional_info` | `Callable[..., dict[str, MetaData]] \| dict[str, MetaData] \| None` | Add additional key/values to the `KCell.info`. Can be a static dict mapping info name to info value. Or can a callable which takes the taper functions' parameters as kwargs and returns a dict with the mapping. | `None` |
| `output_type` | `type[KC] \| None` | The type of the returned cell. | `None` |
| `port_type` | `str` | Type of the ports the taper gets. | `'optical'` |
| `cell_kwargs` | `Unpack[CellKWargs]` | Additional arguments passed as `@kcl.cell(**cell_kwargs)`. | `{}` |

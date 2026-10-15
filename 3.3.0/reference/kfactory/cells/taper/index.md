# taper

Tapers, linear only.

A linear taper transitions between two cross sections (two core widths). The slabs and excludes are part of the cross sections, or can be given for the legacy `(width1, width2, layer, enclosure)` call via a `LayerEnclosure`.

TODO: Non-linear tapers.

## taper\_dbu

```
taper_dbu = taper_factory(kcl=demo)
```

Cross-section-first taper factory on the default KCLayout (length in dbu).

Created by `taper_factory`.

## taper

```
taper(*, width1: um, width2: um, length: um, layer: LayerInfo, enclosure: LayerEnclosure | None = None) -> KCell
```

```
taper(*, cross_section1: str | CrossSection | DCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict, cross_section2: str | CrossSection | DCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict, length: um) -> KCell
```

```
taper(*, length: um, cross_section1: str | CrossSection | DCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, cross_section2: str | CrossSection | DCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width1: um | None = None, width2: um | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> KCell
```

Linear Taper \[um\].

Converts to dbu and calls `taper_dbu`.

Visualization::

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

Either pass two cross sections (`cross_section1`/`cross_section2`) or the legacy `width1`/`width2`/`layer`/`enclosure`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `length` | `um` | Length of the taper. \[um\] | *required* |
| `cross_section1` | `str \| CrossSection \| DCrossSection \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the left side. | `None` |
| `cross_section2` | `str \| CrossSection \| DCrossSection \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the right side. | `None` |
| `width1` | `um \| None` | Width of the core on the left side. \[um\] (legacy; requires `layer`) | `None` |
| `width2` | `um \| None` | Width of the core on the right side. \[um\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Main layer of the taper. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Definition of the slab/exclude. (legacy) | `None` |

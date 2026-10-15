# straight

Provides straight waveguides in dbu and um versions.

A waveguide is a rectangle of material with excludes and/or slab around it::

```
┌─────────────────────────────┐
│        Slab/Exclude         │
├─────────────────────────────┤
│                             │
│            Core             │
│                             │
├─────────────────────────────┤
│        Slab/Exclude         │
└─────────────────────────────┘
```

The slabs and excludes are part of the cross section, or can be given for the legacy `(width, layer, enclosure)` call via a `LayerEnclosure`.

## straight\_dbu

```
straight_dbu = straight_dbu_factory(kcl=demo)
```

Cross-section-first straight factory on the default KCLayout (length in dbu).

Created by `straight_dbu_factory`.

## straight

```
straight(*, width: um, length: um, layer: LayerInfo, enclosure: LayerEnclosure | None = None) -> KCell
```

```
straight(*, cross_section: str | CrossSection | DCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict, length: um) -> KCell
```

```
straight(*, length: um, cross_section: str | CrossSection | DCrossSection | CrossSectionSpecDict | DCrossSectionSpecDict | None = None, width: um | None = None, layer: LayerInfo | None = None, enclosure: LayerEnclosure | None = None) -> KCell
```

Straight waveguide in um.

Converts to dbu and calls `straight_dbu`.

Either pass a `cross_section` (name, spec, or instance) or the legacy `width`/`layer`/`enclosure`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `length` | `um` | Length of the straight. \[um\] | *required* |
| `cross_section` | `str \| CrossSection \| DCrossSection \| CrossSectionSpecDict \| DCrossSectionSpecDict \| None` | Cross section of the straight. | `None` |
| `width` | `um \| None` | Width of the core. \[um\] (legacy; requires `layer`) | `None` |
| `layer` | `LayerInfo \| None` | Main layer of the straight. (legacy) | `None` |
| `enclosure` | `LayerEnclosure \| None` | Definition of slabs/excludes. (legacy) | `None` |

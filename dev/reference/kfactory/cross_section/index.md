# cross\_section

CrossSections for KFactory.

## AsymmetricCrossSection

Bases: `TAsymmetricCrossSection[int]`

dbu-flavored wrapper around an `AsymmetricalCrossSection`.

### add\_bbox

```
add_bbox(c: KCell | DKCell | VKCell, ref: LayerInfo | int | Box | DBox | ProtoInstance[Any] | None = None, *, top: int | None = None, bottom: int | None = None, right: int | None = None, left: int | None = None) -> None
```

Draw bbox\_sections using padding in integer dbu.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell \| DKCell \| VKCell` | Target KCell, DKCell, or VKCell, including subclasses. Must share this cross section's KCLayout, as must any instance reference. | *required* |
| `ref` | `LayerInfo \| int \| Box \| DBox \| ProtoInstance[Any] \| None` | None for the whole target, a layer/index in c, an explicit Box (dbu) or DBox (micrometers), or an instance's transformed bounds in c's coordinate system. Cell references are not accepted. | `None` |
| `top` | `int \| None` | Top padding override for every bbox layer. | `None` |
| `bottom` | `int \| None` | Bottom padding override for every bbox layer. | `None` |
| `right` | `int \| None` | Right padding override for every bbox layer. | `None` |
| `left` | `int \| None` | Left padding override for every bbox layer. | `None` |

None padding uses each layer's stored offset; zero suppresses padding. Real targets use integer geometry; VKCell targets use micrometers. All layers use the same original bounds. Empty references draw nothing; neither the cross section nor the reference box is modified.

> [!WARNING]
>
> Logs a warning when a non-VKCell target has pending virtual instances, even with an explicit reference. Call insert\_vinsts() first to avoid inaccurate geometry. This method does not materialize instances.

Raises:

| Type | Description |
| --- | --- |
| `LockedError` | The target cell is locked. |
| `TypeError` | The target or reference type is unsupported. |
| `ValueError` | The target or instance reference uses another KCLayout. |

### get\_sections

```
get_sections() -> tuple[CrossSectionLayer, ...]
```

Absolute signed dbu strips of the realised profile, main strip first.

## AsymmetricalCrossSection

Bases: `BaseModel`

Cross section composed of independent layer strips at signed bounds.

The main strip (`layer`, `section_min`, `section_max`) is the port reference; `sections` holds any additional strips. All bounds are signed integer dbu relative to the port centerline (`x = 0`). Strip edges are always grid-aligned regardless of width parity.

Fields:

- `layer` (`LayerInfo`)
- `section_min` (`dbu`)
- `section_max` (`dbu`)
- `sections` (`tuple[CrossSectionLayer, ...]`)
- `name` (`str`)
- `radius` (`dbu | None`)
- `radius_min` (`dbu | None`)
- `bbox_sections` (`dict[LayerInfo, dbu]`)

Validators:

- `_normalize`
- `_validate`

### is\_named

```
is_named: bool
```

Whether an explicit name was given (vs. the derived structural name).

### main\_layer

```
main_layer: LayerInfo
```

Main layer of the cross section (parity with SymmetricalCrossSection).

### width

```
width: int
```

Main strip width in dbu (`section_max - section_min`).

### auto\_name

```
auto_name() -> str
```

Deterministic structural name (hash of geometry, excluding radius).

### get\_sections

```
get_sections() -> tuple[CrossSectionLayer, ...]
```

Absolute signed dbu strips of the realised profile, main strip first.

The counterpart of `SymmetricalCrossSection.get_sections`: here the strips are already absolute, so this is the main strip followed by the normalized `sections`.

### is\_symmetric

```
is_symmetric() -> bool
```

Whether this cross section is symmetric.

## CrossSection

Bases: `TCrossSection[int]`

### add\_bbox

```
add_bbox(c: KCell | DKCell | VKCell, ref: LayerInfo | int | Box | DBox | ProtoInstance[Any] | None = None, *, top: int | None = None, bottom: int | None = None, right: int | None = None, left: int | None = None) -> None
```

Draw bbox\_sections using padding in integer dbu.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell \| DKCell \| VKCell` | Target KCell, DKCell, or VKCell, including subclasses. Must share this cross section's KCLayout, as must any instance reference. | *required* |
| `ref` | `LayerInfo \| int \| Box \| DBox \| ProtoInstance[Any] \| None` | None for the whole target, a layer/index in c, an explicit Box (dbu) or DBox (micrometers), or an instance's transformed bounds in c's coordinate system. Cell references are not accepted. | `None` |
| `top` | `int \| None` | Top padding override for every bbox layer. | `None` |
| `bottom` | `int \| None` | Bottom padding override for every bbox layer. | `None` |
| `right` | `int \| None` | Right padding override for every bbox layer. | `None` |
| `left` | `int \| None` | Left padding override for every bbox layer. | `None` |

None padding uses each layer's stored offset; zero suppresses padding. Real targets use integer geometry; VKCell targets use micrometers. All layers use the same original bounds. Empty references draw nothing; neither the cross section nor the reference box is modified.

> [!WARNING]
>
> Logs a warning when a non-VKCell target has pending virtual instances, even with an explicit reference. Call insert\_vinsts() first to avoid inaccurate geometry. This method does not materialize instances.

Raises:

| Type | Description |
| --- | --- |
| `LockedError` | The target cell is locked. |
| `TypeError` | The target or reference type is unsupported. |
| `ValueError` | The target or instance reference uses another KCLayout. |

### get\_sections

```
get_sections() -> tuple[CrossSectionLayer, ...]
```

Absolute signed dbu strips of the realised profile, main strip first.

Unlike `sections`, which returns the enclosure's edge-relative bands, this resolves them against the core width and includes the main strip.

## CrossSectionLayer

Bases: `BaseModel`

Single strip in an asymmetrical cross section.

A strip on `layer` spanning `[section_min, section_max]` in dbu relative to the port centerline (`offset=0`). Both bounds are signed integer dbu, so edges are always grid-aligned. The strip's width is the derived `section_max - section_min`.

Fields:

- `layer` (`LayerInfo`)
- `section_min` (`dbu`)
- `section_max` (`dbu`)

Validators:

- `_validate_bounds`

### width

```
width: int
```

Width of the strip in dbu (`section_max - section_min`).

## CrossSectionModel

Bases: `BaseModel`

Fields:

- `cross_sections` (`dict[str, SymmetricalCrossSection | AsymmetricalCrossSection]`)
- `kcl` (`KCLayout`)

### \_\_getitem\_\_

```
__getitem__(name: str) -> SymmetricalCrossSection | AsymmetricalCrossSection
```

Get a cross section by name.

Auto names of symmetric cross sections from before the `sym_` prefix (e.g. referenced by ports in older GDS files) resolve as well.

## DAsymmetricCrossSection

Bases: `TAsymmetricCrossSection[float]`

um-flavored wrapper around an `AsymmetricalCrossSection`.

### add\_bbox

```
add_bbox(c: KCell | DKCell | VKCell, ref: LayerInfo | int | Box | DBox | ProtoInstance[Any] | None = None, *, top: float | None = None, bottom: float | None = None, right: float | None = None, left: float | None = None) -> None
```

Draw bbox\_sections using padding in micrometers.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell \| DKCell \| VKCell` | Target KCell, DKCell, or VKCell, including subclasses. Must share this cross section's KCLayout, as must any instance reference. | *required* |
| `ref` | `LayerInfo \| int \| Box \| DBox \| ProtoInstance[Any] \| None` | None for the whole target, a layer/index in c, an explicit Box (dbu) or DBox (micrometers), or an instance's transformed bounds in c's coordinate system. Cell references are not accepted. | `None` |
| `top` | `float \| None` | Top padding override for every bbox layer. | `None` |
| `bottom` | `float \| None` | Bottom padding override for every bbox layer. | `None` |
| `right` | `float \| None` | Right padding override for every bbox layer. | `None` |
| `left` | `float \| None` | Left padding override for every bbox layer. | `None` |

None padding uses each layer's stored offset; zero suppresses padding. Real targets use integer geometry; VKCell targets use micrometers. All layers use the same original bounds. Empty references draw nothing; neither the cross section nor the reference box is modified.

> [!WARNING]
>
> Logs a warning when a non-VKCell target has pending virtual instances, even with an explicit reference. Call insert\_vinsts() first to avoid inaccurate geometry. This method does not materialize instances.

Raises:

| Type | Description |
| --- | --- |
| `LockedError` | The target cell is locked. |
| `TypeError` | The target or reference type is unsupported. |
| `ValueError` | The target or instance reference uses another KCLayout. |

### get\_sections

```
get_sections() -> tuple[DCrossSectionLayer, ...]
```

Absolute signed um strips of the realised profile, main strip first.

## DAsymmetricalCrossSection

Bases: `BaseModel`

um based AsymmetricalCrossSection.

Fields:

- `layer` (`LayerInfo`)
- `section_min` (`float`)
- `section_max` (`float`)
- `sections` (`tuple[DCrossSectionLayer, ...]`)
- `name` (`str | None`)
- `radius` (`float | None`)
- `radius_min` (`float | None`)
- `bbox_sections` (`dict[LayerInfo, float]`)

Validators:

- `_validate_bounds`

### width

```
width: float
```

Main strip width in um (`section_max - section_min`).

### is\_symmetric

```
is_symmetric() -> bool
```

Whether this cross section is symmetric.

## DCrossSection

Bases: `TCrossSection[float]`

### add\_bbox

```
add_bbox(c: KCell | DKCell | VKCell, ref: LayerInfo | int | Box | DBox | ProtoInstance[Any] | None = None, *, top: float | None = None, bottom: float | None = None, right: float | None = None, left: float | None = None) -> None
```

Draw bbox\_sections using padding in micrometers.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell \| DKCell \| VKCell` | Target KCell, DKCell, or VKCell, including subclasses. Must share this cross section's KCLayout, as must any instance reference. | *required* |
| `ref` | `LayerInfo \| int \| Box \| DBox \| ProtoInstance[Any] \| None` | None for the whole target, a layer/index in c, an explicit Box (dbu) or DBox (micrometers), or an instance's transformed bounds in c's coordinate system. Cell references are not accepted. | `None` |
| `top` | `float \| None` | Top padding override for every bbox layer. | `None` |
| `bottom` | `float \| None` | Bottom padding override for every bbox layer. | `None` |
| `right` | `float \| None` | Right padding override for every bbox layer. | `None` |
| `left` | `float \| None` | Left padding override for every bbox layer. | `None` |

None padding uses each layer's stored offset; zero suppresses padding. Real targets use integer geometry; VKCell targets use micrometers. All layers use the same original bounds. Empty references draw nothing; neither the cross section nor the reference box is modified.

> [!WARNING]
>
> Logs a warning when a non-VKCell target has pending virtual instances, even with an explicit reference. Call insert\_vinsts() first to avoid inaccurate geometry. This method does not materialize instances.

Raises:

| Type | Description |
| --- | --- |
| `LockedError` | The target cell is locked. |
| `TypeError` | The target or reference type is unsupported. |
| `ValueError` | The target or instance reference uses another KCLayout. |

### get\_sections

```
get_sections() -> tuple[DCrossSectionLayer, ...]
```

Absolute signed um strips of the realised profile, main strip first.

Unlike `sections`, which returns the enclosure's edge-relative bands, this resolves them against the core width and includes the main strip.

## DCrossSectionLayer

Bases: `BaseModel`

um based CrossSectionLayer.

Fields:

- `layer` (`LayerInfo`)
- `section_min` (`float`)
- `section_max` (`float`)

Validators:

- `_validate_bounds`

### width

```
width: float
```

Width of the strip in um (`section_max - section_min`).

## DSymmetricalCrossSection

Bases: `BaseModel`

um based CrossSection.

Fields:

- `width` (`float`)
- `enclosure` (`DLayerEnclosure`)
- `name` (`str | None`)
- `radius` (`float | None`)
- `radius_min` (`float | None`)

Validators:

- `_validate_width`

### is\_symmetric

```
is_symmetric() -> bool
```

Whether this cross section is symmetric.

### to\_itype

```
to_itype(kcl: KCLayout) -> SymmetricalCrossSection
```

Convert to a dbu based CrossSection.

## SymmetricalCrossSection

Bases: `BaseModel`

CrossSection which is symmetrical to its main\_layer/width.

Fields:

- `width` (`dbu`)
- `enclosure` (`LayerEnclosure`)
- `name` (`str`)
- `radius` (`dbu | None`)
- `radius_min` (`dbu | None`)

Validators:

- `_set_name`
- `_validate_enclosure_main_layer`
- `_validate_width`

### bbox\_sections

```
bbox_sections: dict[LayerInfo, dbu]
```

Bounding-box sections (owned by the enclosure).

### is\_named

```
is_named: bool
```

Whether an explicit name was given (vs. the enclosure-derived name).

### main\_layer

```
main_layer: LayerInfo
```

Main Layer of the enclosure and cross section.

### \_\_init\_\_

```
__init__(width: dbu, enclosure: LayerEnclosure, name: str | None = None, radius: dbu | None = None, radius_min: dbu | None = None) -> None
```

Initialized the CrossSection.

`bbox_sections` live on the `enclosure` — build the enclosure with them.

### get\_sections

```
get_sections() -> tuple[CrossSectionLayer, ...]
```

Absolute signed dbu strips of the realised profile, main strip first.

The main strip is `width` centered on the center line; the enclosure's edge-relative bands are resolved against that width, so a 3 µm band sits at ±3.25 µm for a 500 nm core and at ±3.55 µm for an 1100 nm one.

The main strip is always first and is never merged into the others, even when the enclosure carries a band on the main layer. The remaining strips are normalized per layer (touching or overlapping ones are merged) and sorted, matching `AsymmetricalCrossSection.sections`.

### get\_xmax

```
get_xmax() -> int
```

Outer edge of the profile in dbu.

The core always reaches `width // 2`, so the enclosure can only push the extent outwards: a cross section with no bands at all is just its core, and a band that shrinks inwards (negative `d_max`) does not pull the extent inside the core it sits on.

### is\_symmetric

```
is_symmetric() -> bool
```

Whether this cross section is symmetric.

### to\_dtype

```
to_dtype(kcl: KCLayout) -> DSymmetricalCrossSection
```

Convert to a um based CrossSection.

## TAsymmetricCrossSection

Bases: `ABC`

Unit-flavored wrapper around an `AsymmetricalCrossSection` base.

Mirrors `TCrossSection` for the symmetric case: both the dbu wrapper (`AsymmetricCrossSection`) and the um wrapper (`DAsymmetricCrossSection`) hold the same `AsymmetricalCrossSection` as `_base`, so they compare equal across units via `.base`.

### add\_bbox

```
add_bbox(c: KCell | DKCell | VKCell, ref: LayerInfo | int | Box | DBox | ProtoInstance[Any] | None = None, *, top: T | None = None, bottom: T | None = None, right: T | None = None, left: T | None = None) -> None
```

Draw bbox\_sections around a cell, layer, box, or instance.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell \| DKCell \| VKCell` | Target KCell, DKCell, or VKCell (including subclasses), sharing this cross section's KCLayout. Instance references must share it too. | *required* |
| `ref` | `LayerInfo \| int \| Box \| DBox \| ProtoInstance[Any] \| None` | Reference layer/index in c, explicit Box/DBox, or instance. None uses the whole cell. A Box is in c's dbu; a DBox is in micrometers. Instances use their transformed bounds in their parent coordinates, which must match c's coordinate system. | `None` |
| `top` | `T \| None` | Override top padding for every bbox layer. | `None` |
| `bottom` | `T \| None` | Override bottom padding for every bbox layer. | `None` |
| `right` | `T \| None` | Override right padding for every bbox layer. | `None` |
| `left` | `T \| None` | Override left padding for every bbox layer. | `None` |

Padding uses this cross section's units (dbu or micrometers). None uses each layer's stored padding; zero suppresses padding on that edge. All layers share the original reference bounds. Empty references draw nothing. The cross section and reference box are not modified. Real-cell geometry is computed in integer DBU after converting inputs; virtual-cell geometry remains in micrometers without grid snapping. Warns if a real target has pending virtual instances; call insert\_vinsts() before adding bbox layers to avoid inaccurate geometry.

### get\_sections

```
get_sections() -> tuple[CrossSectionLayer, ...] | tuple[DCrossSectionLayer, ...]
```

Absolute strips of the realised profile, main strip first.

### is\_symmetric

```
is_symmetric() -> bool
```

Whether this cross section is symmetric.

## TCrossSection

Bases: `ABC`

### main\_layer

```
main_layer: LayerInfo
```

Main Layer of the enclosure and cross section.

### add\_bbox

```
add_bbox(c: KCell | DKCell | VKCell, ref: LayerInfo | int | Box | DBox | ProtoInstance[Any] | None = None, *, top: T | None = None, bottom: T | None = None, right: T | None = None, left: T | None = None) -> None
```

Draw bbox\_sections around a cell, layer, box, or instance.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell \| DKCell \| VKCell` | Target KCell, DKCell, or VKCell (including subclasses), sharing this cross section's KCLayout. Instance references must share it too. | *required* |
| `ref` | `LayerInfo \| int \| Box \| DBox \| ProtoInstance[Any] \| None` | Reference layer/index in c, explicit Box/DBox, or instance. None uses the whole cell. A Box is in c's dbu; a DBox is in micrometers. Instances use their transformed bounds in their parent coordinates, which must match c's coordinate system. | `None` |
| `top` | `T \| None` | Override top padding for every bbox layer. | `None` |
| `bottom` | `T \| None` | Override bottom padding for every bbox layer. | `None` |
| `right` | `T \| None` | Override right padding for every bbox layer. | `None` |
| `left` | `T \| None` | Override left padding for every bbox layer. | `None` |

Padding uses this cross section's units (dbu or micrometers). None uses each layer's stored padding; zero suppresses padding on that edge. All layers share the original reference bounds. Empty references draw nothing. The cross section and reference box are not modified. Real-cell geometry is computed in integer DBU after converting inputs; virtual-cell geometry remains in micrometers without grid snapping. Warns if a real target has pending virtual instances; call insert\_vinsts() before adding bbox layers to avoid inaccurate geometry.

### get\_sections

```
get_sections() -> tuple[CrossSectionLayer, ...] | tuple[DCrossSectionLayer, ...]
```

Absolute strips of the realised profile, main strip first.

### is\_symmetric

```
is_symmetric() -> bool
```

Whether this cross section is symmetric.

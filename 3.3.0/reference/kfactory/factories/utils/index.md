# utils

Utility functions for cell factories.

## boundary\_from\_shapes

```
boundary_from_shapes(c: KCell) -> kdb.DPolygon | None
```

Build a cell boundary from its drawn shapes.

Collects every shape on every layer, merges them, and returns the first polygon (in um) of the merged region — i.e. the outline of the cell's footprint. Returns `None` if the cell has no shapes.

## cross\_section\_from\_width

```
cross_section_from_width(kcl: KCLayout, width: int, layer: LayerInfo, enclosure: LayerEnclosure | None = None) -> CrossSection
```

Build a (dbu) symmetric cross section from legacy width/layer/enclosure args.

## extrude\_backbone

```
extrude_backbone(c: VKCell, backbone: Sequence[DPoint], width: float, layer: LayerInfo, start_angle: float, end_angle: float, dbu: float, enclosure: LayerEnclosure | None = None) -> None
```

Extrude a backbone into a virtual cell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `VKCell` | target cell | *required* |
| `backbone` | `Sequence[DPoint]` | backbone to extrude | *required* |
| `width` | `float` | width to extrude (main layer) | *required* |
| `layer` | `LayerInfo` | main layer &amp; reference for enclosure | *required* |
| `enclosure` | `LayerEnclosure \| None` | enclosure to apply | `None` |
| `start_angle` | `float` | force a certain start angle | *required* |
| `end_angle` | `float` | force a acertain end angle | *required* |
| `dbu` | `float` | database unit to use as a reference | *required* |

## extrude\_backbone\_cross\_section

```
extrude_backbone_cross_section(c: VKCell, backbone: Sequence[DPoint], cross_section: AnyCrossSection, start_angle: float, end_angle: float) -> None
```

Extrude a (symmetric or asymmetric) cross section along a backbone (um).

The virtual-cell counterpart of `extrude_path_cross_section`: symmetric cross sections reproduce `extrude_backbone` exactly (byte-identical, centered width + enclosure annuli); asymmetric ones are extruded as one signed band `[section_min, section_max]` per strip (main strip + each aux section), with strips sharing a layer merged.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `VKCell` | target virtual cell | *required* |
| `backbone` | `Sequence[DPoint]` | backbone to extrude (in um) | *required* |
| `cross_section` | `AnyCrossSection` | the cross section to extrude | *required* |
| `start_angle` | `float` | force a certain start angle | *required* |
| `end_angle` | `float` | force a certain end angle | *required* |

## extrude\_backbone\_dynamic

```
extrude_backbone_dynamic(c: VKCell, backbone: list[DPoint], width1: float, width2: float, layer: LayerInfo, start_angle: float, end_angle: float, dbu: float, enclosure: LayerEnclosure | None = None) -> None
```

Extrude a backbone into a virtual cell.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `VKCell` | target cell | *required* |
| `backbone` | `list[DPoint]` | backbone to extrude | *required* |
| `width1` | `float` | start width to extrude (main layer) | *required* |
| `width2` | `float` | end width to extrude (main layer) | *required* |
| `layer` | `LayerInfo` | main layer &amp; reference for enclosure | *required* |
| `enclosure` | `LayerEnclosure \| None` | enclosure to apply | `None` |
| `start_angle` | `float` | force a certain start angle | *required* |
| `end_angle` | `float` | force a acertain end angle | *required* |
| `dbu` | `float` | database unit to use as a reference | *required* |

## layer\_enclosure\_to\_sections

```
layer_enclosure_to_sections(enclosure: LayerEnclosure | None) -> list[tuple[kdb.LayerInfo, int] | tuple[kdb.LayerInfo, int, int]]
```

Flatten a `LayerEnclosure` into `CrossSectionSpec` `sections` (dbu).

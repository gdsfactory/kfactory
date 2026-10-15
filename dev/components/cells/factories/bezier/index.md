# Bezier S-Bend Factory

`bend_s_bezier_factory(kcl)` returns a cached cell function for cubic-bezier S-bends. Arguments `width`, `height`, and `length` are in **µm**. `height` is the lateral offset (negative flips the bend); `length` is the longitudinal extent.

```
import kfactory as kf
from kfactory.factories.bezier import bend_s_bezier_factory


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)


pdk = kf.KCLayout("FACTORIES_BEZIER_DEMO", infos=LAYER)
L = LAYER()
```

## Basic call

```
bend_s = bend_s_bezier_factory(pdk)

b = bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG)
print("S-bend:", b.name)
b
```

```
S-bend: bend_s_bezier_CSsym_028523d7_500_H5_L20_NP99_TS0_TS1
```

```

```

## Negative height

A negative `height` flips the offset direction.

```
b_flip = bend_s(width=0.5, height=-5.0, length=20.0, layer=L.WG)
b_flip
```

```

```

## Curve resolution

`nb_points` controls the polygon resolution of the bezier backbone (default 99). Lower values trade smoothness for fewer vertices.

```
b_lo = bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG, nb_points=20)
b_hi = bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG, nb_points=200)
print("low-res vertices:", b_lo.shapes(L.WG).each().__next__().polygon.num_points())
print("hi-res  vertices:", b_hi.shapes(L.WG).each().__next__().polygon.num_points())
```

```
low-res vertices: 40
hi-res  vertices: 362
```

## Cladding via `LayerEnclosure`

```
enc = kf.LayerEnclosure(
    sections=[(L.WGCLAD, pdk.to_dbu(2.0))],
    main_layer=L.WG,
    kcl=pdk,
)

b_clad = bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG, enclosure=enc)
b_clad
```

```

```

## Adding metadata

The factory accepts `additional_info` (a dict or callable returning a dict) that gets merged into `KCell.info`.

```
bend_s_meta = bend_s_bezier_factory(
    pdk,
    additional_info={"pdk": "FACTORIES_BEZIER_DEMO", "component_type": "bezier_sbend"},
)

b_meta = bend_s_meta(width=0.5, height=5.0, length=20.0, layer=L.WG)
print("cell info:", dict(b_meta.info))
```

```
[32m2026-10-15 19:04:31.679[0m | [31m[1mERROR   [0m | [36mkfactory.decorators[0m:[36mwrapped_cell[0m:[36m564[0m - [31m[1mName conflict in /home/runner/work/kfactory/kfactory/src/kfactory/factories/bezier.py::_bend_s_bezier at line 169
Renaming Unnamed_8 (cell_index=8) to bend_s_bezier_CSsym_028523d7_500_H5_L20_NP99_TS0_TS1 would cause it to be named the same as:
 - bend_s_bezier_CSsym_028523d7_500_H5_L20_NP99_TS0_TS1 (cell_index=0), function_name=_bend_s_bezier, basename=bend_s_bezier[0m


cell info: {'pdk': 'FACTORIES_BEZIER_DEMO', 'component_type': 'bezier_sbend'}
```

## See Also

| Topic | Where |
| --- | --- |
| Factory overview | [Factories: Overview](<https://gdsfactory.github.io/kfactory/dev/components/cells/factories/overview/index.md>) |
| Euler S-bend (clothoid alternative) | [Factories: Euler](<https://gdsfactory.github.io/kfactory/dev/components/cells/factories/euler/index.md>) |
| All-angle routing with S-bends | [Routing: All-Angle](<https://gdsfactory.github.io/kfactory/dev/routing/all_angle/index.md>) |

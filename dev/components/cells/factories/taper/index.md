# Taper

`taper_factory(kcl)` returns a function whose dimensions are all in **DBU**. Use `kcl.to_dbu(...)` to convert µm to DBU at the call site.

```
import kfactory as kf
from kfactory.factories.taper import taper_factory


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)


pdk = kf.KCLayout("FACTORIES_TAPER_DEMO", infos=LAYER)
L = LAYER()
```

```
taper = taper_factory(pdk)

tp = taper(
    width1=pdk.to_dbu(0.5),
    width2=pdk.to_dbu(2.0),
    length=pdk.to_dbu(20.0),
    layer=L.WG,
)
print("taper:", tp.name)
tp
```

```
taper: taper_CS028523d7_500_CS028523d7_2000_L20000
```

```

```

## See Also

| Topic | Where |
| --- | --- |
| Cross-section based taper specification | [Cross-Sections](<https://gdsfactory.github.io/kfactory/dev/components/cross_sections/index.md>) |

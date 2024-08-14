# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     custom_cell_magics: kql
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Enclosures

# %%
import kfactory as kf


class LayerInfos(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    SLAB: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
    NPP: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)

LAYER = LayerInfos()
kf.kcl.infos = LAYER

# %%
enc = kf.enclosure.LayerEnclosure(
    [
        (LAYER.SLAB, 2000),
    ],
    name="WGSLAB",
    main_layer=LAYER.WG,
)
c = kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG, enclosure=enc)
c.show()
c.plot()

# %%
enc = kf.enclosure.LayerEnclosure(
    [
        (LAYER.SLAB, 2000),
        (LAYER.NPP, 1000, 2000),
    ],
    name="SLAB_DOPED",
    main_layer=LAYER.WG,
)
c = kf.cells.euler.bend_euler(radius=5, width=1, layer=LAYER.WG, enclosure=enc)
c.show()
c.plot()

# %%
kcell_enc = kf.KCellEnclosure([enc])

@kf.cell
def two_bends(
    radius: float,
    width: float,
    layer: kf.kdb.LayerInfo,
    enclosure: kf.KCellEnclosure | None = None,
) -> kf.KCell:
    c = kf.KCell()
    b1 = c << kf.cells.euler.bend_euler(radius=radius, width=width, layer=layer)
    b2 = c << kf.cells.euler.bend_euler(radius=radius, width=width, layer=layer)
    b2.drotate(90)
    b2.dmovey(-11)
    b2.dmovex(b2.dxmin, 0)

    c.add_ports(b1.ports)
    c.add_ports(b2.ports)
    c.auto_rename_ports()

    if enclosure:
        enclosure.apply_minkowski_tiled(c)
    return c


c = two_bends(radius=5, width=1, layer=LAYER.WG, enclosure=kcell_enc)
c.show()
c.plot()

# %%

# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     custom_cell_magics: kql
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: base
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Enclosures

# %%
import kfactory as kf


class LAYER(kf.LayerEnum):
    kcl = kf.constant(kf.kcl)
    WG = (1, 0)
    SLAB = (2, 0)
    NPP = (3, 0)


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
@kf.cell
def two_bends(
    radius: float,
    width: float,
    layer: kf.LayerEnum,
    enclosure: kf.enclosure.LayerEnclosure | None = None,
) -> kf.KCell:
    c = kf.KCell()
    b1 = c << kf.cells.euler.bend_euler(radius=radius, width=width, layer=layer)
    b2 = c << kf.cells.euler.bend_euler(radius=radius, width=width, layer=layer)
    b2.d.rotate(90)
    b2.d.movey(-11)
    b2.d.movex(+9)

    if enclosure:
        enclosure.apply_minkowski_tiled(c)
    return c


c = two_bends(radius=5, width=1, layer=LAYER.WG, enclosure=enc)
c.show()
c.plot()

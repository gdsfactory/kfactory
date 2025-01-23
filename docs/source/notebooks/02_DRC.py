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
# # Fixing DRC Errors
#
# ## Min space violations
#
# You can fix Min space violations.

# %%
from datetime import datetime
import kfactory as kf

# Define Layers

class LayerInfos(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1,0)
    WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2,0) # WG Exclude
    CLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3,0) # cladding
    FLOORPLAN: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10,0)

# Make the layout object aware of the new layers:
LAYER = LayerInfos()
kf.kcl.infos = LAYER

# %%
triangle = kf.KCell()
triangle_poly = kf.kdb.DPolygon(
    [kf.kdb.DPoint(0, 10), kf.kdb.DPoint(30, 10), kf.kdb.DPoint(30, 0)]
)
triangle.shapes(triangle.layer(1, 0)).insert(triangle_poly)
triangle

# %%
box = kf.KCell(name="Box")
box_rect = kf.kdb.DBox(0, 0, 20, 5)
box.shapes(box.kcl.find_layer(1, 0)).insert(box_rect)
box

# %%
c = kf.KCell(name="fix_accute_angle")
c << triangle
c << box
c

# %%
c = kf.KCell(name="tiled_test")


d1 = datetime.now()

for i in range(50):
    ellipse = kf.kdb.Polygon.ellipse(kf.kdb.Box(10000, 20000), i * 2)

    x0 = 0
    for j in range(5000, 30000, 500):
        c.shapes(c.kcl.find_layer(1, 0)).insert(
            ellipse.transformed(kf.kdb.Trans(x0, i * 30000))
        )
        c.shapes(c.kcl.find_layer(1, 0)).insert(
            ellipse.transformed(kf.kdb.Trans(x0 + j, i * 30000))
        )

        x0 += 15000

d2 = datetime.now()

c.shapes(c.kcl.layer(2, 0)).insert(
    kf.utils.fix_spacing_tiled(
        c,
        1000,
        c.kcl.infos.WG,
        metrics=kf.kdb.Metrics.Euclidian,
        n_threads=32,
        tile_size=(250, 250),
    )
)

d3 = datetime.now()

print(f"time to draw: {d2-d1}")
print(f"time to clean: {d3-d2}")
print(f"total time: {d3-d1}")

c

# %%
c = kf.KCell()
d1 = datetime.now()

for i in range(50):
    ellipse = kf.kdb.Polygon.ellipse(kf.kdb.Box(10000, 20000), i * 2)

    x0 = 0
    for j in range(5000, 30000, 500):
        c.shapes(c.kcl.layer(1, 0)).insert(
            ellipse.transformed(kf.kdb.Trans(x0, i * 30000))
        )
        c.shapes(c.kcl.layer(1, 0)).insert(
            ellipse.transformed(kf.kdb.Trans(x0 + j, i * 30000))
        )

        x0 += 15000

d2 = datetime.now()

c.shapes(c.kcl.layer(2, 0)).insert(
    kf.utils.fix_spacing_minkowski_tiled(
        c,
        1000,
        c.kcl.infos.WG,
        n_threads=32,
        tile_size=(250, 250),
        smooth=5,
    )
)

d3 = datetime.now()

print(f"time to draw: {d2-d1}")
print(f"time to clean: {d3-d2}")
print(f"total time: {d3-d1}")

c.show()
c.plot()

# %% [markdown]
# ## Dummy fill
#
# To keep density constant you can add dummy fill.

# %%
c = kf.KCell()
c.shapes(kf.kcl.find_layer(1, 0)).insert(
    kf.kdb.DPolygon.ellipse(kf.kdb.DBox(5000, 3000), 512)
)
c.shapes(kf.kcl.find_layer(10, 0)).insert(
    kf.kdb.DPolygon(
        [kf.kdb.DPoint(0, 0), kf.kdb.DPoint(5000, 0), kf.kdb.DPoint(5000, 3000)]
    )
)
c

# %%
fc = kf.KCell()
fc.shapes(fc.kcl.find_layer(2, 0)).insert(kf.kdb.DBox(20, 40))
fc.shapes(fc.kcl.find_layer(3, 0)).insert(kf.kdb.DBox(30, 15))
fc

# %%
import kfactory.utils.fill as fill

# %%
# fill.fill_tiled(c, fc, [(kf.kcl.find_layer(1,0), 0)], exclude_layers = [(kf.kcl.find_layer(10,0), 100), (kf.kcl.find_layer(2,0), 0), (kf.kcl.find_layer(3,0),0)], x_space=5, y_space=5)
fill.fill_tiled(
    c,
    fc,
    [(kf.kcl.infos.WG, 0)],
    exclude_layers=[
        (LAYER.FLOORPLAN, 100),
        (LAYER.WGEX, 0),
        (LAYER.CLAD, 0),
    ],
    x_space=5,
    y_space=5,
)

# %%
c.show()
c.plot()

# %%

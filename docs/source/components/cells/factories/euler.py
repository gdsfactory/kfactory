# ---
# jupyter:
#   jupytext:
#     custom_cell_magics: kql
#     formats: py:percent
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
# # Euler Bend Factories
#
# Two factory functions live in `kf.factories.euler`:
#
# - `bend_euler_factory(kcl)` — clothoid 90° / arbitrary-angle bends.
# - `bend_s_euler_factory(kcl)` — S-shaped (laterally offset) clothoid bends.
#
# Unlike the DBU-native straight/taper factories, the euler factories take
# `width` and `radius` in **µm**. The factory handles the µm→DBU conversion
# internally.

# %%
import kfactory as kf
from kfactory.factories.euler import bend_euler_factory, bend_s_euler_factory


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)


pdk = kf.KCLayout("FACTORIES_EULER_DEMO", infos=LAYER)
L = LAYER()

# %% [markdown]
# ## `bend_euler_factory` — 90° bends

# %%
bend_euler = bend_euler_factory(pdk)

# 90° bend, 0.5 µm wide, 10 µm radius
b90 = bend_euler(width=0.5, radius=10.0, layer=L.WG)
print("90° euler bend:", b90.name)
b90

# %% [markdown]
# ### Arbitrary angle
#
# The `angle` parameter (degrees, default 90) produces partial euler bends.

# %%
b45 = bend_euler(width=0.5, radius=10.0, layer=L.WG, angle=45.0)
b180 = bend_euler(width=0.5, radius=10.0, layer=L.WG, angle=180.0)
print("45°  bend:", b45.name)
print("180° bend:", b180.name)
b180

# %% [markdown]
# ### Effective radius
#
# Euler bends are clothoid curves — the actual footprint extends beyond the
# nominal radius. Use `kf.routing.optical.get_radius(bend)` to get the footprint
# radius for routing spacing calculations.

# %%
footprint_r = kf.routing.optical.get_radius(b90)
print(f"nominal radius: 10.0 µm, footprint radius: {footprint_r:.3f} µm")

# %% [markdown]
# ## `bend_s_euler_factory` — S-bends
#
# `bend_s_euler_factory(kcl)` creates S-shaped (offset) bends. The `offset`
# argument controls the lateral displacement (µm); a negative value flips the
# direction of the offset.

# %%
sbend_euler = bend_s_euler_factory(pdk)

sbend = sbend_euler(offset=5.0, width=0.5, radius=10.0, layer=L.WG)
print("S-bend:", sbend.name)
sbend

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Factory overview | [Factories: Overview](overview.py) |
# | Euler bend cell page | [Components: Euler Bends](../euler.py) |
# | Optical routing with euler bends | [Routing: Optical](../../../routing/optical.py) |

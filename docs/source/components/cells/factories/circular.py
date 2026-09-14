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
# # Circular Bends
#
# `bend_circular_factory(kcl)` produces constant-radius arc bends. Unlike euler
# bends, the footprint radius equals the nominal radius (up to DBU rounding).
# `kf.routing.optical.get_radius` returns DBU, so convert it to µm for comparison.
# Arguments `width` and `radius` are in **µm**.

# %%
import kfactory as kf
from kfactory.factories.circular import bend_circular_factory


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)


pdk = kf.KCLayout("FACTORIES_CIRCULAR_DEMO", infos=LAYER)
L = LAYER()

# %%
bend_circ = bend_circular_factory(pdk)

bc90 = bend_circ(width=0.5, radius=10.0, layer=L.WG)
print("circular bend:", bc90.name)
footprint_radius_um = bc90.kcl.to_um(kf.routing.optical.get_radius(bc90.ports))
print("footprint radius:", footprint_radius_um, "µm (== nominal)")
bc90

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|

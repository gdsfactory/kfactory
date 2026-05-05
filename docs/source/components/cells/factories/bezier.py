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
# # Bezier S-Bend Factory
#
# `bend_s_bezier_factory(kcl)` returns a cached cell function for cubic-bezier
# S-bends. Arguments `width`, `height`, and `length` are in **µm**.
# `height` is the lateral offset (negative flips the bend); `length` is the
# longitudinal extent.

# %%
import kfactory as kf
from kfactory.factories.bezier import bend_s_bezier_factory


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)


pdk = kf.KCLayout("FACTORIES_BEZIER_DEMO", infos=LAYER)
L = LAYER()

# %% [markdown]
# ## Basic call

# %%
bend_s = bend_s_bezier_factory(pdk)

b = bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG)
print("S-bend:", b.name)
b

# %% [markdown]
# ## Negative height
#
# A negative `height` flips the offset direction.

# %%
b_flip = bend_s(width=0.5, height=-5.0, length=20.0, layer=L.WG)
b_flip

# %% [markdown]
# ## Curve resolution
#
# `nb_points` controls the polygon resolution of the bezier backbone (default 99).
# Lower values trade smoothness for fewer vertices.

# %%
b_lo = bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG, nb_points=20)
b_hi = bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG, nb_points=200)
print("low-res vertices:", b_lo.shapes(L.WG).each().__next__().polygon.num_points())
print("hi-res  vertices:", b_hi.shapes(L.WG).each().__next__().polygon.num_points())

# %% [markdown]
# ## Cladding via `LayerEnclosure`

# %%
enc = kf.LayerEnclosure(
    sections=[(L.WGCLAD, pdk.to_dbu(2.0))],
    main_layer=L.WG,
    kcl=pdk,
)

b_clad = bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG, enclosure=enc)
b_clad

# %% [markdown]
# ## Adding metadata
#
# The factory accepts `additional_info` (a dict or callable returning a dict)
# that gets merged into `KCell.info`.

# %%
bend_s_meta = bend_s_bezier_factory(
    pdk,
    additional_info={"pdk": "FACTORIES_BEZIER_DEMO", "component_type": "bezier_sbend"},
)

b_meta = bend_s_meta(width=0.5, height=5.0, length=20.0, layer=L.WG)
print("cell info:", dict(b_meta.info))

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Factory overview | [Factories: Overview](overview.py) |
# | Euler S-bend (clothoid alternative) | [Factories: Euler](euler.py) |
# | All-angle routing with S-bends | [Routing: All-Angle](../../../routing/all_angle.py) |

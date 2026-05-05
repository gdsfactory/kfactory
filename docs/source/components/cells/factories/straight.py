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
# # Straight Waveguide
#
# `straight_dbu_factory(kcl)` returns a cached cell function whose arguments are
# all in **DBU** (database units). Convert µm values with `kcl.to_dbu()`.

# %%
import kfactory as kf
from kfactory.factories.straight import straight_dbu_factory


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)


pdk = kf.KCLayout("FACTORIES_STRAIGHT_DEMO", infos=LAYER)
L = LAYER()

# %% [markdown]
# ## Build a few waveguides
#
# Each call with the same arguments returns the *same* cell object — that's the
# `@kcl.cell` cache at work.

# %%
straight = straight_dbu_factory(pdk)

wg_short = straight(
    width=pdk.to_dbu(0.5),    # 500 DBU = 0.5 µm
    length=pdk.to_dbu(10.0),  # 10000 DBU = 10 µm
    layer=L.WG,
)
wg_long = straight(
    width=pdk.to_dbu(0.5),
    length=pdk.to_dbu(20.0),
    layer=L.WG,
)

print("short name:", wg_short.name)
print("long  name:", wg_long.name)
print(
    "same object (same args)?",
    wg_short is straight(pdk.to_dbu(0.5), pdk.to_dbu(10.0), L.WG),
)
wg_short

# %% [markdown]
# ## Enclosure (cladding / exclude)
#
# Pass a `LayerEnclosure` to add slab or exclude layers automatically.

# %%
enc = kf.LayerEnclosure(
    sections=[(L.WGCLAD, pdk.to_dbu(3.0))],
    main_layer=L.WG,
    kcl=pdk,
)

wg_clad = straight(
    width=pdk.to_dbu(0.5),
    length=pdk.to_dbu(15.0),
    layer=L.WG,
    enclosure=enc,
)
wg_clad

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Cross-sections (alternative spec) | [Cross-Sections](../../cross_sections.py) |

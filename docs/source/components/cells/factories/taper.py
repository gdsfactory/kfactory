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
# # Taper
#
# `taper_factory(kcl)` returns a function whose dimensions are all in **DBU**.
# Use `kcl.to_dbu(...)` to convert µm to DBU at the call site.

# %%
import kfactory as kf
from kfactory.factories.taper import taper_factory


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)


pdk = kf.KCLayout("FACTORIES_TAPER_DEMO", infos=LAYER)
L = LAYER()

# %%
taper = taper_factory(pdk)

tp = taper(
    width1=pdk.to_dbu(0.5),
    width2=pdk.to_dbu(2.0),
    length=pdk.to_dbu(20.0),
    layer=L.WG,
)
print("taper:", tp.name)
tp

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Cross-section based taper specification | [Cross-Sections](../../cross_sections.py) |

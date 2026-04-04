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
# # Factory Functions
#
# A **factory** in kfactory is a function that returns another function — a
# *cell-making function* bound to a specific `KCLayout` instance.  Factories are the
# recommended way to build production PDKs because they:
#
# - **Tie cells to a specific layout** — every cell built by the factory lives in
#   the same `KCLayout`, so layer indices are consistent.
# - **Cache automatically** — the returned function is decorated with `@kcl.cell`,
#   so repeated calls with the same arguments return the *same* cell object.
# - **Carry typed protocols** — each factory returns a typed `Protocol` callable, so
#   IDEs and type-checkers can validate arguments at the call site.
# - **Enable routing** — the built-in routers (`route_bundle`, `place_manhattan`)
#   require factory functions, not raw cells, so they can create bend/straight
#   geometry on demand.
#
# ## Available factories
#
# | Factory function | Module | Returns | Unit system |
# |---|---|---|---|
# | `straight_dbu_factory(kcl)` | `kf.factories.straight` | `StraightFactory` | DBU |
# | `bend_euler_factory(kcl)` | `kf.factories.euler` | `BendEulerFactory` | µm |
# | `bend_s_euler_factory(kcl)` | `kf.factories.euler` | `BendSEulerFactory` | µm |
# | `bend_circular_factory(kcl)` | `kf.factories.circular` | `BendCircularFactory` | µm |
# | `taper_factory(kcl)` | `kf.factories.taper` | `TaperFactory` | DBU |
#
# ## Setup

# %%
import kfactory as kf
from kfactory.factories.straight import straight_dbu_factory
from kfactory.factories.euler import bend_euler_factory, bend_s_euler_factory
from kfactory.factories.circular import bend_circular_factory
from kfactory.factories.taper import taper_factory


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)


# Create a dedicated KCLayout for this demo PDK
pdk = kf.KCLayout("FACTORIES_DEMO", infos=LAYER)

# %% [markdown]
# ## 1 · Straight waveguide factory
#
# `straight_dbu_factory(kcl)` returns a cached cell function whose arguments are
# all in **DBU** (database units).  Convert µm values with `kcl.to_dbu()`.

# %%
straight = straight_dbu_factory(pdk)

# Build two waveguides — same width, different lengths
wg_short = straight(
    width=pdk.to_dbu(0.5),   # 500 DBU = 0.5 µm
    length=pdk.to_dbu(10.0), # 10000 DBU = 10 µm
    layer=LAYER().WG,
)
wg_long = straight(
    width=pdk.to_dbu(0.5),
    length=pdk.to_dbu(20.0),
    layer=LAYER().WG,
)

print("short name:", wg_short.name)
print("long  name:", wg_long.name)
print("same object (same args)?", wg_short is straight(pdk.to_dbu(0.5), pdk.to_dbu(10.0), LAYER().WG))
wg_short

# %% [markdown]
# ### Enclosure (cladding / exclude)
#
# Pass a `LayerEnclosure` to add slab or exclude layers automatically.

# %%
enc = kf.LayerEnclosure(
    sections=[(LAYER().WGCLAD, pdk.to_dbu(3.0))],
    main_layer=LAYER().WG,
    kcl=pdk,
)

wg_clad = straight(
    width=pdk.to_dbu(0.5),
    length=pdk.to_dbu(15.0),
    layer=LAYER().WG,
    enclosure=enc,
)
wg_clad

# %% [markdown]
# ## 2 · Euler bend factory
#
# `bend_euler_factory(kcl)` returns a function whose `width` and `radius` are in
# **µm** (not DBU).  The factory handles the µm→DBU conversion internally.

# %%
bend_euler = bend_euler_factory(pdk)

# 90° bend, 0.5 µm wide, 10 µm radius
b90 = bend_euler(width=0.5, radius=10.0, layer=LAYER().WG)
print("90° euler bend:", b90.name)
b90

# %% [markdown]
# ### Arbitrary angle
#
# The `angle` parameter (degrees, default 90) produces partial euler bends.

# %%
b45 = bend_euler(width=0.5, radius=10.0, layer=LAYER().WG, angle=45.0)
b180 = bend_euler(width=0.5, radius=10.0, layer=LAYER().WG, angle=180.0)
print("45° bend:", b45.name)
print("180° bend:", b180.name)
b180

# %% [markdown]
# ### Effective radius
#
# Euler bends are clothoid curves — the actual footprint extends beyond the nominal
# radius.  Use `kf.routing.optical.get_radius(bend)` to get the footprint radius
# for routing spacing calculations.

# %%
footprint_r = kf.routing.optical.get_radius(b90)
print(f"nominal radius: 10.0 µm, footprint radius: {footprint_r:.3f} µm")

# %% [markdown]
# ## 3 · Euler S-bend factory
#
# `bend_s_euler_factory(kcl)` creates S-shaped (offset) bends.  The `offset`
# argument controls the lateral displacement (µm); a negative value flips the
# direction of the offset.

# %%
sbend_euler = bend_s_euler_factory(pdk)

sbend = sbend_euler(offset=5.0, width=0.5, radius=10.0, layer=LAYER().WG)
print("S-bend:", sbend.name)
sbend

# %% [markdown]
# ## 4 · Circular bend factory
#
# `bend_circular_factory(kcl)` produces constant-radius arc bends.  Unlike euler
# bends, `get_radius` returns exactly the nominal radius.

# %%
bend_circ = bend_circular_factory(pdk)

bc90 = bend_circ(width=0.5, radius=10.0, layer=LAYER().WG)
print("circular bend:", bc90.name)
print("footprint radius:", kf.routing.optical.get_radius(bc90), "µm (== nominal)")
bc90

# %% [markdown]
# ## 5 · Taper factory
#
# `taper_factory(kcl)` returns a function whose dimensions are all in **DBU**.

# %%
taper = taper_factory(pdk)

tp = taper(
    width1=pdk.to_dbu(0.5),
    width2=pdk.to_dbu(2.0),
    length=pdk.to_dbu(20.0),
    layer=LAYER().WG,
)
print("taper:", tp.name)
tp

# %% [markdown]
# ## 6 · Factories and routing
#
# The built-in optical router (`kf.routing.optical.route_bundle`) requires factory
# callables — it uses them to instantiate bends and straights while building a
# route.  Passing cells directly is not supported.
#
# ```python
# routes = kf.routing.optical.route_bundle(
#     c,
#     start_ports=[...],
#     end_ports=[...],
#     bend90_cell=bend_euler,      # factory callable
#     straight_factory=straight,   # factory callable
# )
# ```
#
# Because each factory is bound to `pdk`, all route geometry automatically lands
# in the correct layout and uses the correct layer indices.

# %% [markdown]
# ## 7 · Bundling factories in a PDK module
#
# The recommended pattern for a production PDK is to define all factories in one
# place and import them wherever routing or assembly is needed.  This keeps layer
# indices and unit conventions consistent across the whole project.
#
# ```python
# # my_pdk/factories.py
# import kfactory as kf
# from kfactory.factories.straight import straight_dbu_factory
# from kfactory.factories.euler import bend_euler_factory
# from kfactory.factories.taper import taper_factory
# from my_pdk.layers import LAYER
#
# pdk = kf.KCLayout("MY_PDK", infos=LAYER)
#
# straight = straight_dbu_factory(pdk)
# bend_euler = bend_euler_factory(pdk)
# taper = taper_factory(pdk)
#
# __all__ = ["pdk", "straight", "bend_euler", "taper"]
# ```
#
# Consumers then just import:
#
# ```python
# from my_pdk.factories import pdk, straight, bend_euler
# ```

# %% [markdown]
# ## Summary
#
# | Task | API |
# |---|---|
# | Straight waveguide factory | `straight_dbu_factory(kcl)` → `StraightFactory` |
# | Euler bend factory | `bend_euler_factory(kcl)` → `BendEulerFactory` |
# | Euler S-bend factory | `bend_s_euler_factory(kcl)` → `BendSEulerFactory` |
# | Circular bend factory | `bend_circular_factory(kcl)` → `BendCircularFactory` |
# | Taper factory | `taper_factory(kcl)` → `TaperFactory` |
# | Get footprint radius (euler) | `kf.routing.optical.get_radius(bend_cell)` |
# | Register with layout | `pdk.straight_factory = ...`, `pdk.bend_factory = ...` |
#
# **Key rules:**
# - `straight_dbu_factory` / `taper_factory` → arguments in **DBU**
# - `bend_euler_factory` / `bend_circular_factory` → `width` and `radius` in **µm**
# - Always bind the factory to the same `KCLayout` that owns the cells being routed

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Parameterised cells & caching | [Components: PCells](pcells.py) |
# | Straight waveguide | [Components: Straight](straight.py) |
# | Euler bends | [Components: Euler Bends](euler.py) |
# | Circular bends | [Components: Circular Bends](circular.py) |
# | Width tapers | [Components: Tapers](taper.py) |
# | Bezier S-bends | [Components: Bezier](bezier.py) |
# | Routing integration | [Routing: Overview](../routing/overview.py) |
# | PDK bundling pattern | [PDK: Creating a PDK](../pdk/creating_pdk.py) |

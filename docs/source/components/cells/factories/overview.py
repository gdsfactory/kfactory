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
# *cell-making function* bound to a specific `KCLayout` instance. Factories are the
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
# | Factory | Module | Page |
# |---|---|---|
# | `straight_dbu_factory` | `kf.factories.straight` | [Straight](straight.py) |
# | `bend_euler_factory` / `bend_s_euler_factory` | `kf.factories.euler` | [Euler](euler.py) |
# | `bend_circular_factory` | `kf.factories.circular` | [Circular](circular.py) |
# | `taper_factory` | `kf.factories.taper` | [Taper](taper.py) |

# %% [markdown]
# ## Factories and routing
#
# The built-in optical router (`kf.routing.optical.route_bundle`) requires factory
# callables — it uses them to instantiate bends and straights while building a
# route. Passing cells directly is not supported.
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
# Because each factory is bound to a `KCLayout`, all route geometry automatically
# lands in the correct layout and uses the correct layer indices.

# %% [markdown]
# ## Bundling factories in a PDK module
#
# The recommended pattern for a production PDK is to define all factories in one
# place and import them wherever routing or assembly is needed. This keeps layer
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
# ## Key rules
#
# - `straight_dbu_factory` / `taper_factory` — arguments in **DBU**
# - `bend_euler_factory` / `bend_circular_factory` — `width` and `radius` in **µm**
# - Always bind the factory to the same `KCLayout` that owns the cells being routed

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Parameterised cells & caching | [Components: PCells](../pcells.py) |
# | Straight waveguide | [Components: Straight](../straight.py) |
# | Euler bends | [Components: Euler Bends](../euler.py) |
# | Circular bends | [Components: Circular Bends](../circular.py) |
# | Width tapers | [Components: Tapers](../taper.py) |
# | Bezier S-bends | [Components: Bezier](../bezier.py) |
# | Routing integration | [Routing: Overview](../../../routing/overview.py) |
# | PDK bundling pattern | [PDK: Creating a PDK](../../../pdk/creating_pdk.py) |

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
# # Best Practices & Common Pitfalls
#
# This guide collects the most frequent mistakes kfactory users encounter, with
# the correct patterns shown for each one.  Every section is self-contained and
# executable.
#
# **Contents**
#
# 1. [Units: DBU vs µm](#1-units-dbu-vs-m)
# 2. [Ports: `port=` keyword is required](#2-ports-port-keyword-is-required)
# 3. [Layers & KCLayout initialisation](#3-layers-kclayout-initialisation)
# 4. [Caching: arguments must be hashable](#4-caching-arguments-must-be-hashable)
# 5. [Cross-sections in cached cells](#5-cross-sections-in-cached-cells)
# 6. [Factory parameter units](#6-factory-parameter-units)
# 7. [Effective bend radius vs nominal radius](#7-effective-bend-radius-vs-nominal-radius)
# 8. [Routing: suppress collision errors in headless builds](#8-routing-suppress-collision-errors-in-headless-builds)
# 9. [PDK: always pass `kcl=` to `kf.Port`](#9-pdk-always-pass-kcl-to-kfport)
# 10. [Enclosures: µm sections need `kcl=`](#10-enclosures-m-sections-need-kcl)
# 11. [fill_tiled: call inside `@kf.cell`, result is in-place](#11-fill_tiled-call-inside-kfcell-result-is-in-place)
# 12. [Packing: spacing and limits are in DBU](#12-packing-spacing-and-limits-are-in-dbu)
# 13. [dmove: pass a tuple, not a DVector](#13-dmove-pass-a-tuple-not-a-dvector)

# %%
import kfactory as kf
import kfactory.routing.optical as opt

class LAYER(kf.LayerInfos):
    WG:   kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
    SLAB: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)

L = LAYER()
kf.kcl.infos = L

li_wg   = kf.kcl.find_layer(L.WG)
li_wgex = kf.kcl.find_layer(L.WGEX)

# %% [markdown]
# ---
# ## 1 · Units: DBU vs µm
#
# kfactory (and KLayout) has two parallel coordinate systems:
#
# | System | Unit | Python type | Rule of thumb |
# |--------|------|-------------|---------------|
# | **DBU** (database units) | 1 nm (default) | `int` | Use inside cell logic, ports, boolean ops |
# | **µm** (micrometres) | 1 µm | `float` | Use for user-facing parameters |
#
# The conversion is fixed: **1 µm = 1 000 DBU** (`kf.kcl.dbu = 0.001 µm`).
#
# ### Common mistake — passing µm where DBU is expected
#
# ```python
# # WRONG: 0.5 is treated as 0 DBU (rounds to integer)
# c.shapes(li_wg).insert(kf.kdb.Box(10.0, 0.5))
#
# # WRONG: width=0.5 sets port to 0 or 1 DBU, not 500 nm
# kf.Port(name="o1", width=0.5, ...)
# ```
#
# ### Correct pattern

# %%
# Convert µm → DBU explicitly at the boundary
width_um  = 0.5   # user-facing µm value
length_um = 10.0

w_dbu = kf.kcl.to_dbu(width_um)   # → 500  (int)
l_dbu = kf.kcl.to_dbu(length_um)  # → 10000 (int)

c = kf.KCell("bp_units_demo")
c.shapes(li_wg).insert(kf.kdb.Box(l_dbu, w_dbu))
c.add_port(port=kf.Port(
    name="o1",
    trans=kf.kdb.Trans(2, False, -l_dbu // 2, 0),
    width=w_dbu,          # ← integer DBU
    layer=li_wg,
    port_type="optical",
))
c.add_port(port=kf.Port(
    name="o2",
    trans=kf.kdb.Trans(0, False,  l_dbu // 2, 0),
    width=w_dbu,
    layer=li_wg,
    port_type="optical",
))

print(f"dbu setting : {kf.kcl.dbu} µm/DBU")
print(f"width → DBU : {w_dbu}")
print(f"bbox (DBU)  : {c.bbox()}")
print(f"bbox (µm)   : {c.dbbox()}")

# %% [markdown]
# ---
# ## 2 · Ports: `port=` keyword is required
#
# `KCell.add_port()` takes the port via the **keyword argument** `port=`.
# Passing it positionally raises a `TypeError`.
#
# ```python
# # WRONG — positional argument
# c.add_port(my_port)
#
# # WRONG — wrong keyword
# c.add_port(p=my_port)
# ```

# %%
# CORRECT — always use port=
example = kf.KCell("bp_add_port")
p = kf.Port(name="o1", trans=kf.kdb.Trans(0), width=500, layer=li_wg, port_type="optical")
example.add_port(port=p)  # ← keyword required

# Renaming when exposing a child port on a parent cell:
parent = kf.KCell("bp_parent")
inst   = parent << example
parent.add_port(port=inst.ports["o1"], name="in")  # ← name= renames
print(f"parent ports: {[p.name for p in parent.ports]}")

# %% [markdown]
# ---
# ## 3 · Layers & KCLayout initialisation
#
# ### Pass the **class** (not an instance) as `infos=`
#
# `KCLayout.__init__` calls `infos()` internally, so you must pass the class:
#
# ```python
# # WRONG — passes an instance; KCLayout calls LAYER()() which fails
# pdk = kf.KCLayout("mypdk", infos=LAYER())
#
# # CORRECT — pass the class
# pdk = kf.KCLayout("mypdk", infos=LAYER)
# ```
#
# ### Setting `infos` after construction does not fully register layers

# %%
# Full correct initialisation for a new KCLayout
pdk = kf.KCLayout("best_practices_pdk", infos=LAYER)
L2  = pdk.infos   # already an instance; use this for layer lookups

print(f"pdk.dbu   : {pdk.dbu}")
print(f"layer WG  : {pdk.find_layer(L2.WG)}")

# %% [markdown]
# ### `layerenum_from_dict` lives in `kfactory.layer`, not top-level `kf`
#
# ```python
# # WRONG
# kf.layerenum_from_dict(...)
#
# # CORRECT
# from kfactory.layer import layerenum_from_dict
# layerenum_from_dict(...)
# ```

# %% [markdown]
# ---
# ## 4 · Caching: arguments must be hashable
#
# `@kf.cell` identifies unique cells by hashing all arguments.  Any
# unhashable argument (list, dict, `LayerInfo` object, `CrossSection` object)
# raises `TypeError` at call time.
#
# **Rules:**
# - Use `int`, `float`, `str`, `bool`, `tuple`, or frozen containers.
# - Replace a `CrossSection` argument with its **name string**; look it up
#   inside the function.
# - Replace a `LayerInfo` with a `str` name or `int` layer index.

# %%
# Register a cross-section: call get_icross_section() with a spec to store it,
# then retrieve it by name inside the factory.
_xs_spec = kf.DCrossSection(
    kcl=kf.kcl,
    width=0.5,
    layer=L.WG,
    sections=[(L.WGEX, 1.0)],   # 1 µm cladding
    name="wg_500",
)
kf.kcl.get_icross_section(_xs_spec)   # ← registers under the name "wg_500"

@kf.cell
def waveguide_xs(xs_name: str = "wg_500", length_um: float = 10.0) -> kf.KCell:
    """Waveguide using a cross-section looked up by name."""
    xs  = kf.kcl.get_icross_section(xs_name)  # ← resolve here, not in signature
    c   = kf.KCell()
    l   = kf.kcl.to_dbu(length_um)
    w   = xs.width                              # already in DBU
    li  = kf.kcl.find_layer(xs.main_layer)
    c.shapes(li).insert(kf.kdb.Box(l, w))
    c.add_port(port=kf.Port(name="o1", trans=kf.kdb.Trans(2, False, -l//2, 0),
                            width=w, layer=li, port_type="optical"))
    c.add_port(port=kf.Port(name="o2", trans=kf.kdb.Trans(0, False,  l//2, 0),
                            width=w, layer=li, port_type="optical"))
    return c

wg_a = waveguide_xs(xs_name="wg_500", length_um=10.0)
wg_b = waveguide_xs(xs_name="wg_500", length_um=10.0)
print(f"Same params → same object: {wg_a is wg_b}")   # True

# %% [markdown]
# ---
# ## 5 · Cross-sections in cached cells
#
# Passing a `CrossSection` or `DCrossSection` **object** directly as a parameter
# raises `TypeError: unhashable type` because cross-section objects are not
# hashable.  Always pass the **name string** and resolve inside the function
# (see §4 above).

# %% [markdown]
# ---
# ## 6 · Factory parameter units
#
# Each factory function uses a specific unit system for its parameters.
# Getting this wrong produces silently wrong geometry.
#
# | Factory | Width | Length / Radius | Unit |
# |---------|-------|-----------------|------|
# | `straight_dbu_factory` | DBU (`int`) | DBU (`int`) | nm |
# | `taper_factory` | DBU (`int`) | DBU (`int`) | nm |
# | `bend_euler_factory` | µm (`float`) | µm (`float`) | µm |
# | `bend_circular_factory` | µm (`float`) | µm (`float`) | µm |
# | `bend_s_euler_factory` | µm (`float`) | µm (`float`) | µm |
# | `bezier_factory` | µm (`float`) | µm (`float`) | µm |

# %%
# Use a dedicated layout for the factory demo to avoid global state conflicts
fac_pdk = kf.KCLayout("BP_FAC_DEMO", infos=LAYER)

straight_f = kf.factories.straight.straight_dbu_factory(fac_pdk)
bend_euler_f = kf.factories.euler.bend_euler_factory(fac_pdk)

# straight_dbu_factory: width and length in DBU (use to_dbu to convert µm)
s = straight_f(
    width=fac_pdk.to_dbu(0.5),     # 500 DBU = 0.5 µm
    length=fac_pdk.to_dbu(10.0),   # 10000 DBU = 10 µm
    layer=L.WG,
)
print(f"straight bbox (DBU): {s.bbox()}")

# bend_euler_factory: width and radius in µm (no to_dbu needed)
b = bend_euler_f(width=0.5, radius=10.0, layer=L.WG)
print(f"euler bbox   (µm):   {b.dbbox()}")

# %% [markdown]
# ---
# ## 7 · Effective bend radius vs nominal radius
#
# Euler (clothoid) bends extend further than their nominal radius because the
# clothoid transitions ramp up gradually.  Always use
# `kf.routing.optical.get_radius(bend_cell)` to get the **footprint radius**
# that routing algorithms need, not the nominal value you passed to the factory.
#
# Circular bends return the exact nominal radius — `get_radius` is still safe
# to use but adds no correction.

# %%
bend90 = bend_euler_f(width=0.5, radius=10.0, layer=L.WG)

nominal_radius  = 10.0                              # what we asked for
footprint_radius = opt.get_radius(bend90)           # what routing needs

print(f"nominal radius  : {nominal_radius:.3f} µm")
print(f"footprint radius: {footprint_radius:.3f} µm")
print(f"difference      : {footprint_radius - nominal_radius:.3f} µm")

# %% [markdown]
# > **Rule:** Pass `footprint_radius` (not `nominal_radius`) to
# > `route_loopback(bend90_radius=...)`, `place_manhattan(...)`, and
# > similar functions. Using the nominal value causes "distance too small" errors.

# %% [markdown]
# ---
# ## 8 · Routing: suppress collision errors in headless builds
#
# By default, `route_bundle` enables collision detection and calls
# `kf.show()` / KLayout's error dialog when routes overlap.  In a headless
# documentation build (no display, no KLayout window) this hangs or crashes.
#
# Pass `on_collision=None` to disable the callback:
#
# ```python
# # Headless-safe (docs, CI, testing)
# kf.routing.optical.route_bundle(
#     ...,
#     on_collision=None,
# )
#
# # Interactive (development): keep default or pass on_collision="show"
# kf.routing.optical.route_bundle(...)
# ```
#
# > **Note:** Only suppress when you are confident the geometry is correct.
# > Leave collision detection on during development so errors are caught early.

# %% [markdown]
# ---
# ## 9 · PDK: always pass `kcl=` to `kf.Port`
#
# When building cells inside a custom `KCLayout` (PDK), ports created with
# `kf.Port(...)` default to the **global** `kf.kcl` layout.  Layer indices in
# the PDK layout will differ, causing silent mismatches or runtime errors.
#
# ```python
# # WRONG — port attached to global kf.kcl, not pdk
# p = kf.Port(name="o1", layer=pdk.find_layer(L.WG), ...)
#
# # CORRECT — port attached to the correct layout
# p = kf.Port(name="o1", layer=pdk.find_layer(L.WG), kcl=pdk, ...)
# ```

# %%
# Demonstrate: ports use pdk layout, not global kf.kcl
@pdk.cell
def pdk_straight(width: float = 0.5, length: float = 10.0) -> kf.KCell:
    c  = kf.KCell(kcl=pdk)
    w  = pdk.to_dbu(width)
    ll = pdk.to_dbu(length)
    li = pdk.find_layer(L2.WG)
    c.shapes(li).insert(kf.kdb.Box(ll, w))
    c.add_port(port=kf.Port(
        name="o1",
        trans=kf.kdb.Trans(2, False, -ll // 2, 0),
        width=w, layer=li, port_type="optical",
        kcl=pdk,   # ← attach to PDK layout
    ))
    c.add_port(port=kf.Port(
        name="o2",
        trans=kf.kdb.Trans(0, False,  ll // 2, 0),
        width=w, layer=li, port_type="optical",
        kcl=pdk,   # ← attach to PDK layout
    ))
    return c

ps = pdk_straight()
print(f"PDK cell layout : {ps.kcl.name}")
print(f"Port o1 layout  : {ps.ports['o1'].kcl.name}")

# %% [markdown]
# ---
# ## 10 · Enclosures: µm sections need `kcl=`
#
# `LayerEnclosure` accepts sections in either DBU or µm.  When using the
# `dsections=` (µm) form, the enclosure needs a reference `KCLayout` to
# convert µm → DBU.  Omitting `kcl=` raises `AttributeError` at apply time.
#
# ```python
# # WRONG — dsections without kcl=
# enc = kf.LayerEnclosure(dsections=[(L.WGEX, 1.0)])
#
# # CORRECT — provide kcl= so conversion is possible
# enc = kf.LayerEnclosure(dsections=[(L.WGEX, 1.0)], kcl=kf.kcl)
# ```
#
# ### Three-element sections create annular (ring) cladding
#
# ```python
# # Two-element  (layer, d)      → expand outward by d (DBU)
# enc_solid = kf.LayerEnclosure(sections=[(L.WGEX, 500)])
#
# # Three-element (layer, d_min, d_max) → ring from d_min to d_max (DBU)
# enc_ring  = kf.LayerEnclosure(sections=[(L.SLAB, 0, 2000)])
# ```

# %%
# Correct dsections usage with kcl=
enc_ok = kf.LayerEnclosure(dsections=[(L.WGEX, 1.0)], kcl=kf.kcl)
print(f"enclosure layer_sections: {enc_ok.layer_sections}")

# Three-element annular section demo (annular ring: d_min=0, d_max=2 µm)
enc_ring = kf.LayerEnclosure(sections=[(L.SLAB, 0, 2000)], kcl=kf.kcl)
print(f"ring layer_sections:      {enc_ring.layer_sections}")

# %% [markdown]
# ---
# ## 11 · `fill_tiled`: call inside `@kf.cell`, result is in-place
#
# Two rules that catch almost everyone:
#
# 1. **Call `fill_tiled` inside the decorated function** — the target cell must
#    be unlocked.  After `@kf.cell` caches and freezes the cell you can no
#    longer modify it.
# 2. **`fill_tiled` returns `None`** — it modifies the cell in-place.  Do not
#    assign its return value.
#
# ```python
# # WRONG — called after caching (cell is frozen)
# my_cell = make_fill_cell()
# kf.fill_tiled(my_cell, ...)         # AttributeError: cell is read-only
#
# # WRONG — return value assigned (it's None)
# region = kf.fill_tiled(c, ...)      # region is None
#
# # CORRECT — call inside the factory function
# @kf.cell
# def fill_block(width_um: float, height_um: float) -> kf.KCell:
#     c = kf.KCell()
#     ...
#     kf.fill_tiled(c, ...)            # ← in-place, returns None
#     return c
# ```
#
# Also note:
# - `row_step` / `col_step` are `kdb.DVector` in **µm**.
# - `x_space` / `y_space` are µm gaps between bounding boxes.
# - `@kf.cell(kcl=...)` is **not valid syntax** — create cells with
#   `kf.KCell(kcl=...)` explicitly inside the function body.

# %% [markdown]
# ---
# ## 12 · Packing: spacing and limits are in DBU
#
# `kf.packing.pack_kcells` and `kf.packing.pack_instances` live in the
# `kf.packing` **sub-module** (not top-level `kf`).  Their `spacing`,
# `max_width`, and `max_height` parameters are all in **DBU**.

# %%
import kfactory.packing as packing

# Build a handful of small cells to pack
cells = [
    kf.KCell(f"pack_demo_{i}")
    for i in range(5)
]
for i, cell in enumerate(cells):
    cell.shapes(li_wg).insert(kf.kdb.Box(
        kf.kcl.to_dbu((i + 1) * 5.0),   # 5, 10, 15, 20, 25 µm wide
        kf.kcl.to_dbu(2.0),             # 2 µm tall
    ))

container = kf.KCell("pack_container")
packing.pack_kcells(
    kcells=cells,
    target=container,
    spacing=kf.kcl.to_dbu(2.0),          # ← DBU (use to_dbu to convert from µm)
    max_width=kf.kcl.to_dbu(100.0),      # ← DBU
)
print(f"packed bbox (µm): {container.dbbox()}")

# %% [markdown]
# ---
# ## 13 · `dmove`: pass a tuple, not a `DVector`
#
# `Instance.dmove()` accepts a `(dx, dy)` tuple of µm floats.  Passing a
# `kdb.DVector` raises `TypeError` because the method tries to unpack it as
# a two-element iterable and gets a `CplxTrans` argument error.
#
# ```python
# # WRONG — DVector causes TypeError with DCplxTrans unpacking
# inst.dmove(kf.kdb.DVector(5.0, 0.0))
#
# # CORRECT — plain tuple
# inst.dmove((5.0, 0.0))
# ```

# %%
tile = kf.KCell("dmove_demo_tile")
tile.shapes(li_wg).insert(kf.kdb.Box(2000, 500))

canvas = kf.KCell("dmove_demo_canvas")
for i in range(4):
    inst = canvas << tile
    inst.dmove((i * 3.0, 0.0))   # ← tuple, not DVector

print(f"canvas bbox (µm): {canvas.dbbox()}")

# %% [markdown]
# ---
# ## Quick-reference summary
#
# | Pitfall | Rule |
# |---------|------|
# | µm vs DBU confusion | Convert at function boundary with `kf.kcl.to_dbu()` |
# | `add_port` errors | Always use `c.add_port(port=p)` keyword form |
# | KCLayout `infos=` | Pass the **class** (`infos=LAYER`), not an instance |
# | Unhashable `@kf.cell` args | Pass cross-sections / layers as **name strings** |
# | Wrong factory units | `straight_dbu_factory` → DBU; euler/circular → µm |
# | Routing with euler bends | Use `opt.get_radius(bend)` for footprint radius |
# | Headless collision errors | Pass `on_collision=None` in CI / doc builds |
# | PDK port layout mismatch | Always pass `kcl=pdk` to `kf.Port(...)` |
# | Enclosure µm sections | Pass `kcl=` to `LayerEnclosure(dsections=...)` |
# | `fill_tiled` usage | Call inside `@kf.cell`; return value is `None` |
# | Packing parameters | `spacing`, `max_width`, `max_height` are in **DBU** |
# | `dmove` argument | Pass `(dx, dy)` tuple, not `kdb.DVector` |

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Common patterns (positive guidance) | [How-To: Patterns](patterns.py) |
# | Frequently asked questions | [How-To: FAQ](faq.md) |
# | DBU vs µm coordinate systems | [Core Concepts: DBU vs µm](../concepts/dbu_vs_um.py) |
# | Creating a full PDK | [PDK: Creating a PDK](../pdk/creating_pdk.py) |

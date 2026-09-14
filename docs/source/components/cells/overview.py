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
# # Components & Factories
#
# kfactory ships a library of **built-in photonic components** under `kf.cells` and the
# **factories** that generate them under `kf.factories`.
#
# | Component | Cell function | Factory |
# |---|---|---|
# | Straight waveguide | `kf.cells.straight.straight` | `kf.factories.straight.straight_dbu_factory` |
# | Euler bend | `kf.cells.euler.bend_euler` | `kf.factories.euler.bend_euler_factory` |
# | Euler S-bend | `kf.cells.euler.bend_s_euler` | `kf.factories.euler.bend_s_euler_factory` |
# | Circular bend | `kf.cells.circular.bend_circular` | `kf.factories.circular.bend_circular_factory` |
# | Taper | `kf.cells.taper.taper` | `kf.factories.taper.taper_factory` |
# | Bezier S-bend | `kf.cells.bezier.bend_s` | `kf.factories.bezier.bend_s_bezier_factory` |
#
# ## Cells vs. Factories
#
# Every **cell function** under `kf.cells.*` uses the built-in demo `KCLayout` instance
# (`kf.cells.demo`). These are convenient for quick prototyping and learning.
#
# A **factory** is a function that *creates* a cell function bound to a specific
# `KCLayout`. When you build your own PDK you call the factory once, passing your
# layout, and get back a cell function that creates geometry in that layout:
#
# ```python
# my_straight = kf.factories.straight.straight_dbu_factory(kcl=my_kcl)
# wg = my_straight(width=500, length=10_000, layer=LAYER.WG)
# ```
#
# This page demonstrates both patterns side by side.

# %% [markdown]
# ## Setup

# %%
import kfactory as kf


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
    SLAB: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)


L = LAYER()
kf.kcl.infos = L

# %% [markdown]
# ## Straight waveguide
#
# `kf.cells.straight.straight` creates a rectangle of material with optional
# slab/exclude layers defined by a `LayerEnclosure`.
#
# ```
# ┌──────────────────────────────┐
# │         Slab/Exclude         │
# ├──────────────────────────────┤
# │                              │
# │             Core             │
# │                              │
# ├──────────────────────────────┤
# │         Slab/Exclude         │
# └──────────────────────────────┘
# ```
#
# Arguments are in **µm** (the `um` variant). All coordinates are converted to DBU
# internally. There is also a `straight_dbu` function for DBU-native code.

# %%
from kfactory.cells.straight import straight

# Simple straight — no cladding
wg = straight(width=0.5, length=10.0, layer=L.WG)
wg.plot()

# %% [markdown]
# ### With cladding via LayerEnclosure
#
# Wrap the core with an oxide/slab layer using `LayerEnclosure`:

# %%
enc = kf.LayerEnclosure(
    dsections=[(L.WGCLAD, 3)],  # 3 µm cladding on all sides
    kcl=kf.kcl,
)

wg_clad = straight(width=0.5, length=10.0, layer=L.WG, enclosure=enc)
wg_clad.plot()

# %% [markdown]
# ### Using the factory directly
#
# For PDK work, bind a straight factory to your `KCLayout`:

# %%
from kfactory.factories.straight import straight_dbu_factory

my_straight = straight_dbu_factory(kcl=kf.kcl)

# Dimensions in DBU (1 µm = 1000 dbu at default 1 nm/dbu)
wg_dbu = my_straight(
    width=kf.kcl.to_dbu(0.5),
    length=kf.kcl.to_dbu(20.0),
    layer=L.WG,
)
wg_dbu.plot()

# %% [markdown]
# ## Euler bend
#
# An **Euler bend** (clothoid bend) has a radius that varies continuously from 0 at the
# input to a maximum value at the midpoint and back to 0 at the output. This minimises
# mode mismatch and reflection compared to a circular bend of the same nominal radius.
#
# Key parameters:
# - `width` — waveguide core width \[µm\]
# - `radius` — nominal radius of the backbone \[µm\]
# - `angle` — total angle swept (default 90°)
# - `resolution` — number of backbone segments per 360° (default 150)

# %%
from kfactory.cells.euler import bend_euler

bend = bend_euler(width=0.5, radius=10.0, layer=L.WG)
bend.plot()

# %% [markdown]
# ### Euler bend — custom angle

# %%
bend_45 = bend_euler(width=0.5, radius=10.0, layer=L.WG, angle=45)
bend_45.plot()

# %% [markdown]
# ### Euler S-bend
#
# An Euler S-bend offsets two ports laterally by `offset` µm. The backbone consists of
# two Euler quarter-circles joined at their inflection point.

# %%
from kfactory.cells.euler import bend_s_euler

sbend = bend_s_euler(offset=2.0, width=0.5, radius=10.0, layer=L.WG)
sbend.plot()

# %% [markdown]
# ### Euler factory — PDK usage
#
# Bind an Euler factory to your layout to create bends that live in your PDK:

# %%
from kfactory.factories.euler import bend_euler_factory

my_bend_euler = bend_euler_factory(kcl=kf.kcl)
pdk_bend = my_bend_euler(width=0.5, radius=10.0, layer=L.WG)
pdk_bend.plot()

# %% [markdown]
# ## Circular bend
#
# A **circular bend** has a *constant* radius throughout. It is faster to compute than
# an Euler bend but has higher mode mismatch at the junction with a straight waveguide.
#
# Key parameters:
# - `width` — waveguide core width \[µm\]
# - `radius` — constant bend radius \[µm\]
# - `angle` — angle swept (default 90°)
# - `angle_step` — angular resolution (default 1° per point)

# %%
from kfactory.cells.circular import bend_circular

circ = bend_circular(width=0.5, radius=10.0, layer=L.WG)
circ.plot()

# %% [markdown]
# ### Circular bend — 180°

# %%
circ_180 = bend_circular(width=0.5, radius=5.0, layer=L.WG, angle=180)
circ_180.plot()

# %% [markdown]
# ## Taper
#
# A **linear taper** transitions between two different waveguide widths. Typical uses:
# - Mode-field adapter between a narrow routing waveguide and a wide MMI port.
# - Spot-size converter at a chip facet.
#
# ```
#            __
#          _/  │
#        _/  __│
#      _/  _/  │
#     │  _/    │ Core
#     │_/      │
#     │_       │
#     │ \_     │
#     │_  \_   │
#       \_  \__│
#         \_   │
#           \__│
# ```

# %%
from kfactory.cells.taper import taper

t = taper(width1=0.5, width2=3.0, length=20.0, layer=L.WG)
t.plot()

# %% [markdown]
# ### Taper with cladding

# %%
enc_slab = kf.LayerEnclosure(dsections=[(L.SLAB, 2)], kcl=kf.kcl)

t_clad = taper(width1=0.5, width2=3.0, length=20.0, layer=L.WG, enclosure=enc_slab)
t_clad.plot()

# %% [markdown]
# ## Bezier S-bend
#
# A **Bezier S-bend** uses a cubic Bezier curve to create a smooth lateral offset. It
# offers more shape control than an Euler S-bend (via `t_start`/`t_stop`).
#
# Key parameters:
# - `width` — waveguide width \[µm\]
# - `height` — lateral offset between the two ports \[µm\]
# - `length` — horizontal span of the bend \[µm\]
# - `nb_points` — backbone resolution (default 99)

# %%
from kfactory.cells.bezier import bend_s

bez = bend_s(width=0.5, height=2.0, length=15.0, layer=L.WG)
bez.plot()

# %% [markdown]
# ## Building your own PDK components
#
# The factory pattern lets you create component functions that are:
# 1. **Bound to your layout** — geometry lands in the right `KCLayout`.
# 2. **Cached automatically** — calling with the same params returns the same cell.
# 3. **Named consistently** — cell names embed all parameters for traceability.
#
# ### Example: custom PDK with two components

# %%
# Create a dedicated layout for "MyPDK"
my_pdk = kf.KCLayout("MyPDK")
my_pdk.infos = L  # reuse the same layer definitions


# Build factory-backed cell functions
@kf.cell
def my_waveguide(width: float, length: float) -> kf.KCell:
    """Straight waveguide using MyPDK's layout.

    Args:
        width: Core width [µm].
        length: Waveguide length [µm].
    """
    c = kf.KCell()
    c.shapes(c.kcl.find_layer(L.WG)).insert(
        kf.kdb.DBox(0, -width / 2, length, width / 2)
    )
    c.add_port(
        port=kf.Port(
            name="o1",
            trans=kf.kdb.Trans(2, False, 0, 0),
            layer=c.kcl.find_layer(L.WG),
            width=kf.kcl.to_dbu(width),
            port_type="optical",
        )
    )
    c.add_port(
        port=kf.Port(
            name="o2",
            trans=kf.kdb.Trans(0, False, kf.kcl.to_dbu(length), 0),
            layer=c.kcl.find_layer(L.WG),
            width=kf.kcl.to_dbu(width),
            port_type="optical",
        )
    )
    return c


wg_custom = my_waveguide(width=0.45, length=5.0)
print(f"Cell name: {wg_custom.name!r}")
print(f"Ports: {[p.name for p in wg_custom.ports]}")
wg_custom.plot()

# %% [markdown]
# ### Caching in action
#
# The `@kf.cell` decorator caches cells by their parameter signature. Calling the same
# function with the same arguments returns the *identical* cell object:

# %%
wg_a = my_waveguide(width=0.5, length=10.0)
wg_b = my_waveguide(width=0.5, length=10.0)
wg_c = my_waveguide(width=0.5, length=20.0)  # different params → new cell

print(f"wg_a is wg_b: {wg_a is wg_b}")  # True — same cached cell
print(f"wg_a is wg_c: {wg_a is wg_c}")  # False — different length

# %% [markdown]
# ## Assembling components
#
# Assemble an MZI arm from two lower L-bends and an inverted U across the top.
# The U consists of two 90° bends joined by a horizontal straight of `length`.
# Each vertical leg receives a `delta_length / 2` straight, adding `delta_length`
# to the optical path while keeping the input and output positions fixed.
# All dimensions passed to the cell factories below are in **µm**.
#
# ```text
#              ┌────── length ──────┐
#              │                    │
#       delta_length / 2      delta_length / 2
#              │                    │
#    o1 ───────┘                    └─────── o2
# ```
#
# Use `<<` to place instances and `connect()` to snap their ports. Traverse
# the two top bends from `o2` to `o1` to turn back down toward the output.


# %%
@kf.cell
def mzi_arm(length: float = 20.0, delta_length: float = 20.0) -> kf.KCell:
    """Assemble an MZI arm with a top straight and two equal delay legs.

    Args:
        length: Length of the horizontal top straight in µm. Must be positive.
        delta_length: Extra path length in µm, split equally between the legs.
            Must be nonnegative. Zero connects the bends directly.
    """
    if length <= 0 or delta_length < 0:
        raise ValueError("length must be positive and delta_length nonnegative")
    c = kf.KCell()

    enc = kf.LayerEnclosure(dsections=[(L.WGCLAD, 2)], kcl=kf.kcl)

    bend = bend_euler(width=0.5, radius=10.0, layer=L.WG, enclosure=enc)
    left_l = c << bend
    top_left = c << bend
    top_right = c << bend
    right_l = c << bend
    top = c << straight(width=0.5, length=length, layer=L.WG, enclosure=enc)

    # Left L turns upward. Add half the extra length before entering the U.
    left_end = left_l.ports["o2"]
    if delta_length > 0:
        delay = straight(width=0.5, length=delta_length / 2, layer=L.WG, enclosure=enc)
        left_delay = c << delay
        left_delay.connect("o1", left_end)
        left_end = left_delay.ports["o2"]

    # Inverted U: upward → rightward → downward.
    top_left.connect("o2", left_end)
    top.connect("o1", top_left.ports["o1"])
    top_right.connect("o2", top.ports["o2"])

    # Descend by the same extra length, then turn right through the second L.
    right_end = top_right.ports["o1"]
    if delta_length > 0:
        right_delay = c << delay
        right_delay.connect("o1", right_end)
        right_end = right_delay.ports["o2"]
    right_l.connect("o1", right_end)

    c.add_port(name="o1", port=left_l.ports["o1"])
    c.add_port(name="o2", port=right_l.ports["o2"])
    return c


# 20 µm total extra length gives a 10 µm straight in each vertical leg.
arm = mzi_arm(length=20.0, delta_length=20.0)
arm.plot()

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Straight waveguide deep-dive | [Components: Straight](factories/straight.py) |
# | Euler (clothoid) bends | [Components: Euler Bends](factories/euler.py) |
# | Circular (constant-radius) bends | [Components: Circular Bends](factories/circular.py) |
# | Width tapers | [Components: Tapers](factories/taper.py) |
# | Bezier S-bends | [Components: Bezier](factories/bezier.py) |
# | Virtual (non-physical) cells | [Components: Virtual Cells](virtual.py) |
# | PCells & caching | [Components: PCells](pcells.py) |
# | Factory functions reference | [Components: Factories](factories/overview.py) |
# | KCell / DKCell / VKCell | [Core Concepts: KCell](../../concepts/kcell.py) |

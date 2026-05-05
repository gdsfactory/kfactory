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
# # Bezier S-Bends
#
# Bezier S-bends use a **cubic Bezier curve** to smoothly connect two parallel
# waveguides that are laterally offset.  The shape is controlled by four
# control points:
#
# ```
#  (0, 0)  →  (L/2, 0)  →  (L/2, H)  →  (L, H)
# ```
#
# This gives a gentle S-shaped curve whose tangent is horizontal at both
# entry and exit — ideal for fanning in/out fiber arrays or shifting
# waveguide tracks.
#
# ```
#                    ╭────── o2  (height H above o1)
#                   ╱
#   o1 ────────────╯
#       length L
# ```
#
# ## API summary
#
# | Function | When to use |
# |---|---|
# | `kf.cells.bezier.bend_s(width, height, length, layer)` | Quick prototyping |
# | `kf.factories.bezier.bend_s_bezier_factory(kcl=...)` | Production PDK |
#
# All length/height/width parameters are in **micrometres (µm)**.
#
# ## Setup

# %%
import kfactory as kf


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)


L = LAYER()
kf.kcl.infos = L

# %% [markdown]
# ## Basic Bezier S-bend
#
# `kf.cells.bezier.bend_s` takes **width**, **height** (lateral offset), and
# **length** all in **µm**, plus a `kdb.LayerInfo` for the core layer.

# %%
sbend = kf.cells.bezier.bend_s(
    width=0.5,  # µm — core width
    height=5.0,  # µm — lateral offset between o1 and o2
    length=20.0,  # µm — horizontal span of the bend
    layer=L.WG,
)
sbend.plot()

# %% [markdown]
# Two ports are created:
# - **`o1`** — input port, pointing west (rotation 2 = 180°), at origin
# - **`o2`** — output port, pointing east (rotation 0 = 0°), at `(length, height)`

# %%
for p in sbend.ports:
    print(f"{p.name}: width={p.dwidth:.3f} µm  trans={p.trans}")

# %% [markdown]
# The bounding box reflects the geometry:

# %%
bb = sbend.dbbox()
print(f"width={bb.width():.3f} µm  height={bb.height():.3f} µm")

# %% [markdown]
# ## Varying height and length
#
# A larger **height** shifts the output waveguide further up; a larger
# **length** makes the curve more gradual (lower curvature):

# %%
sbend_wide = kf.cells.bezier.bend_s(
    width=0.5,
    height=20.0,  # larger offset
    length=60.0,  # proportionally longer for gentle curve
    layer=L.WG,
)
sbend_wide.plot()

# %% [markdown]
# A compact bend uses a short length for a tighter offset:

# %%
sbend_compact = kf.cells.bezier.bend_s(
    width=0.5,
    height=2.0,
    length=10.0,
    layer=L.WG,
)
sbend_compact.plot()

# %% [markdown]
# ## Negative height — flipping the bend
#
# Setting `height` to a negative value shifts the output waveguide
# **downward**:

# %%
sbend_neg = kf.cells.bezier.bend_s(
    width=0.5,
    height=-5.0,  # offset downward
    length=20.0,
    layer=L.WG,
)
sbend_neg.plot()

# %% [markdown]
# ## Controlling curve resolution
#
# The `nb_points` parameter sets the number of polygon vertices that
# approximate the Bezier curve (default 99).  Fewer points produce a
# coarser shape; more points produce a smoother edge at the cost of a
# larger polygon count:

# %%
sbend_coarse = kf.cells.bezier.bend_s(
    width=0.5,
    height=5.0,
    length=20.0,
    layer=L.WG,
    nb_points=9,  # very coarse — for illustration only
)
sbend_coarse.plot()

# %%
sbend_fine = kf.cells.bezier.bend_s(
    width=0.5,
    height=5.0,
    length=20.0,
    layer=L.WG,
    nb_points=201,
)
sbend_fine.plot()

# %% [markdown]
# ## Partial Bezier curves with t_start / t_stop
#
# The internal parameter `t` runs from 0 to 1 along the full Bezier arc.
# By changing `t_start` and `t_stop` you can extract only a sub-arc,
# useful for more exotic routing shapes:

# %%
sbend_half = kf.cells.bezier.bend_s(
    width=0.5,
    height=5.0,
    length=20.0,
    layer=L.WG,
    t_start=0.0,
    t_stop=0.5,  # only the first half of the S-curve
)
sbend_half.plot()

# %% [markdown]
# ## Cladding with LayerEnclosure
#
# Pass a `LayerEnclosure` to automatically add slab or exclude regions
# around the core:

# %%
enc = kf.LayerEnclosure(
    name="WGSTD",
    sections=[(L.WGCLAD, 2_000)],  # 2 µm cladding (in DBU)
)

sbend_clad = kf.cells.bezier.bend_s(
    width=0.5,
    height=5.0,
    length=20.0,
    layer=L.WG,
    enclosure=enc,
)
sbend_clad.plot()

# %% [markdown]
# ## Caching
#
# Like all `@kf.cell`-decorated functions, `bend_s` is cached — the same
# parameters always return the **same object**:

# %%
b1 = kf.cells.bezier.bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG)
b2 = kf.cells.bezier.bend_s(width=0.5, height=5.0, length=20.0, layer=L.WG)
print("same object?", b1 is b2)  # True

b3 = kf.cells.bezier.bend_s(width=0.5, height=8.0, length=20.0, layer=L.WG)
print("different height → same?", b1 is b3)  # False

# %% [markdown]
# ## Fan-out — connecting multiple waveguides
#
# A common use case is a fiber-array fan-out: bring several parallel
# waveguides from a tight pitch to a wider pitch.  Each track gets its own
# S-bend with the same length but a different height:

# %%
N_GUIDES = 5
PITCH_IN = 2.0  # µm — tight input pitch
PITCH_OUT = 10.0  # µm — wide output pitch
SBEND_LEN = 50.0  # µm


@kf.cell
def fanout() -> kf.KCell:
    c = kf.kcl.kcell()

    for i in range(N_GUIDES):
        height = (i - (N_GUIDES - 1) / 2) * (PITCH_OUT - PITCH_IN)
        sb = kf.cells.bezier.bend_s(
            width=0.5,
            height=height,
            length=SBEND_LEN,
            layer=L.WG,
        )
        inst = c << sb
        # place input ports on a tight grid
        inst.dmove((0, i * PITCH_IN))
        c.add_port(port=inst.ports["o1"], name=f"in_{i}")
        c.add_port(port=inst.ports["o2"], name=f"out_{i}")
    return c


fan_out = fanout()
fan_out.plot()

# %% [markdown]
# ## Production use — the factory pattern
#
# `kf.cells.bezier.bend_s` is bound to kfactory's internal demo `KCLayout`.
# For a real PDK, create a factory bound to your own layout:

# %%
my_kcl = kf.KCLayout("MyPDK_Bezier", infos=LAYER)

bend_s_fn = kf.factories.bezier.bend_s_bezier_factory(kcl=my_kcl)

b_pdk = bend_s_fn(width=0.5, height=5.0, length=20.0, layer=L.WG)
print("cell belongs to:", b_pdk.kcl.name)

# %% [markdown]
# The factory also accepts `additional_info` for metadata and `port_type`
# (default `"optical"`):

# %%
bend_s_meta = kf.factories.bezier.bend_s_bezier_factory(
    kcl=my_kcl,
    additional_info={"pdk": "MyPDK_Bezier", "component_type": "bezier_sbend"},
)

b_meta = bend_s_meta(width=0.5, height=5.0, length=20.0, layer=L.WG)
print("cell info:", dict(b_meta.info))

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Components overview & gallery | [Components: Overview](overview.py) |
# | Euler (clothoid) bends | [Components: Euler Bends](euler.py) |
# | Circular (constant-radius) bends | [Components: Circular Bends](circular.py) |
# | Factory functions reference | [Components: Factories](factories.py) |
# | All-angle routing | [Routing: All-Angle](../routing/all_angle.py) |

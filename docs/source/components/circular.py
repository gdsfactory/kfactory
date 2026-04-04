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
# A circular bend sweeps through a constant radius arc — every point on the
# backbone has the **same curvature**.  This makes the geometry simple and
# easy to reason about, but introduces an abrupt curvature step at the entry
# and exit which can cause extra radiation loss for photonic waveguides.
#
# ```
#        ╭──────╮
#       ╱        ╲
#      │     R    │  ← constant radius R everywhere
#  ────╯           ╰────
#  o1   entry     exit   o2
# ```
#
# **Euler vs circular bends:**
#
# | Property | Euler | Circular |
# |---|---|---|
# | Curvature profile | Linearly ramped (smooth) | Step (discontinuous) |
# | Radiation loss | Lower | Higher |
# | Footprint for same radius | Larger | Smaller |
# | Effective routing radius | > nominal | = nominal |
# | When to use | Photonic waveguides | Electrical wires, coarse simulations |
#
# ## API summary
#
# | Function | When to use |
# |---|---|
# | `kf.cells.circular.bend_circular(width, radius, layer, angle=90)` | Quick prototyping |
# | `kf.factories.circular.bend_circular_factory(kcl=...)` | Production PDK |
#
# All length and radius parameters are in **micrometres (µm)**.
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
# ## Basic 90° circular bend
#
# `kf.cells.circular.bend_circular` takes **width** and **radius** in **µm** and a
# `kdb.LayerInfo` for the core layer.  The default angle is 90°.

# %%
bend = kf.cells.circular.bend_circular(
    width=0.5,    # µm — core width
    radius=10.0,  # µm — backbone radius
    layer=L.WG,
)
bend.plot()

# %% [markdown]
# Two ports are created:
# - **`o1`** — input port, pointing west (rotation 2 = 180°)
# - **`o2`** — output port, pointing north (rotation 1 = 90°) for a 90° bend

# %%
for p in bend.ports:
    print(f"{p.name}: width={p.dwidth:.3f} µm  trans={p.trans}")

# %% [markdown]
# The bounding box reflects the compact footprint.  For a circular bend the
# box is exactly `radius × radius` (plus the wire half-width on each side),
# because there is no clothoid run-in:

# %%
print("bounding box:", bend.dbbox())

# %% [markdown]
# ## Arbitrary bend angles
#
# Set `angle` to any positive value in degrees.  Here a 45° bend:

# %%
bend_45 = kf.cells.circular.bend_circular(
    width=0.5,
    radius=10.0,
    layer=L.WG,
    angle=45,
)
bend_45.plot()

# %%
for p in bend_45.ports:
    print(f"{p.name}: trans={p.trans}")

# %% [markdown]
# ## Polygon resolution — `angle_step`
#
# The backbone is discretised into polygon segments.  `angle_step` (in degrees)
# controls the angular increment between backbone points.
# Smaller values give smoother curves at the cost of more polygon vertices.
#
# Default: `angle_step=1` (1° per segment → 90 segments for a 90° bend).

# %%
# Coarser resolution — 5° steps (18 segments for 90°)
bend_coarse = kf.cells.circular.bend_circular(
    width=0.5,
    radius=10.0,
    layer=L.WG,
    angle_step=5,
)
bend_coarse.plot()

# %%
# Finer resolution — 0.5° steps (180 segments for 90°)
bend_fine = kf.cells.circular.bend_circular(
    width=0.5,
    radius=10.0,
    layer=L.WG,
    angle_step=0.5,
)
print("coarse bbox:", bend_coarse.dbbox())
print("fine bbox:  ", bend_fine.dbbox())

# %% [markdown]
# ## Cladding with LayerEnclosure
#
# Pass a `LayerEnclosure` to add slab or exclude regions around the core:

# %%
enc = kf.LayerEnclosure(
    name="WGSTD_CIRC",
    sections=[(L.WGCLAD, 2_000)],  # 2 µm cladding on each side (in DBU)
)

bend_clad = kf.cells.circular.bend_circular(
    width=0.5,
    radius=10.0,
    layer=L.WG,
    enclosure=enc,
)
bend_clad.plot()

# %% [markdown]
# ## Caching
#
# Like all `@kf.cell`-decorated functions, `bend_circular` is cached — the same
# parameters always return the **same object**:

# %%
b1 = kf.cells.circular.bend_circular(width=0.5, radius=10.0, layer=L.WG)
b2 = kf.cells.circular.bend_circular(width=0.5, radius=10.0, layer=L.WG)
print("same object?", b1 is b2)  # True

b3 = kf.cells.circular.bend_circular(width=0.5, radius=15.0, layer=L.WG)
print("different radius → same?", b1 is b3)  # False

# %% [markdown]
# ## Assembling an L-shaped arm
#
# Connect two straights and a circular bend into a simple L-shaped waveguide:

# %%
@kf.cell
def l_arm_circular() -> kf.KCell:
    c = kf.kcl.kcell()

    s_in  = kf.cells.straight.straight(width=0.5, length=5.0, layer=L.WG)
    b     = kf.cells.circular.bend_circular(width=0.5, radius=10.0, layer=L.WG)
    s_out = kf.cells.straight.straight(width=0.5, length=5.0, layer=L.WG)

    i_in  = c << s_in
    i_b   = c << b
    i_out = c << s_out

    i_b.connect("o1", i_in, "o2")    # snap bend input to straight output
    i_out.connect("o1", i_b, "o2")   # snap exit straight to bend output

    c.add_port(port=i_in.ports["o1"], name="o1")
    c.add_port(port=i_out.ports["o2"], name="o2")
    return c


arm = l_arm_circular()
arm.plot()

# %% [markdown]
# ## Routing radius
#
# Unlike Euler bends, a circular arc does **not** extend beyond its nominal radius.
# The effective routing radius returned by `kf.routing.optical.get_radius` equals
# the `radius` argument you passed in:

# %%
effective_r = kf.routing.optical.get_radius(bend)
print(f"nominal radius: 10.0 µm  →  effective routing radius: {effective_r:.3f} µm")

# %% [markdown]
# This means you can use circular bends in `route_bundle` / `place_manhattan`
# with the nominal radius directly — no correction factor needed.

# %%
from functools import partial

straight_factory = partial(
    kf.factories.straight.straight_dbu_factory(kcl=kf.kcl),
    layer=L.WG,
)

WG_WIDTH = kf.kcl.to_dbu(0.5)

c_routed = kf.KCell("circular_routed")

p_start = kf.Port(
    name="o1",
    trans=kf.kdb.Trans(1, False, 0, 0),
    width=WG_WIDTH,
    layer_info=L.WG,
)
p_end = kf.Port(
    name="o2",
    trans=kf.kdb.Trans(3, False, kf.kcl.to_dbu(40), kf.kcl.to_dbu(120)),
    width=WG_WIDTH,
    layer_info=L.WG,
)

kf.routing.optical.route_bundle(
    c_routed,
    [p_start],
    [p_end],
    separation=kf.kcl.to_dbu(5),
    straight_factory=straight_factory,
    bend90_cell=bend,
)
c_routed

# %% [markdown]
# ## Production use — the factory pattern
#
# `kf.cells.circular.bend_circular` is bound to kfactory's internal demo `KCLayout`.
# For a real PDK, create a factory bound to your own layout:

# %%
my_kcl = kf.KCLayout("MyPDK_Circ", infos=LAYER)

bend_fn = kf.factories.circular.bend_circular_factory(kcl=my_kcl)

b_pdk = bend_fn(width=0.5, radius=10.0, layer=L.WG)
print("cell belongs to:", b_pdk.kcl.name)

# %% [markdown]
# The factory accepts `additional_info` for injecting metadata into `cell.info`:

# %%
bend_fn_meta = kf.factories.circular.bend_circular_factory(
    kcl=my_kcl,
    additional_info={"pdk": "MyPDK_Circ", "component_type": "bend_circular"},
)

b_meta = bend_fn_meta(width=0.5, radius=10.0, layer=L.WG)
print("cell info:", dict(b_meta.info))

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Components overview & gallery | [Components: Overview](overview.py) |
# | Euler (clothoid) bends | [Components: Euler Bends](euler.py) |
# | Parameterised cells & caching | [Components: PCells](pcells.py) |
# | Factory functions reference | [Components: Factories](factories.py) |
# | Optical routing | [Routing: Optical](../routing/optical.py) |

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
# # Euler Bends
#
# Euler bends (also called clothoid or Cornu-spiral bends) are the default bend
# type in kfactory.  Unlike a circular arc — where curvature jumps
# discontinuously at the entry and exit — an Euler bend transitions curvature
# **smoothly** from zero to its peak and back to zero.  This dramatically
# reduces radiation loss and reflections for photonic waveguides.
#
# ```
#          ╭──────╮
#         ╱        ╲
#        │           │  ← curvature grows then shrinks
#   ─────╯           ╰─────
#  o1   entry        exit   o2
# ```
#
# ## API summary
#
# | Function | When to use |
# |---|---|
# | `kf.cells.euler.bend_euler(width, radius, layer, angle=90)` | Quick prototyping |
# | `kf.cells.euler.bend_s_euler(offset, width, radius, layer)` | S-bends between parallel guides |
# | `kf.factories.euler.bend_euler_factory(kcl=...)` | Production PDK |
# | `kf.factories.euler.bend_s_euler_factory(kcl=...)` | Production PDK S-bends |
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
# ## Basic 90° Euler bend
#
# `kf.cells.euler.bend_euler` takes **width** and **radius** in **µm** and a
# `kdb.LayerInfo` for the core layer.  The default angle is 90°.

# %%
bend = kf.cells.euler.bend_euler(
    width=0.5,   # µm — core width
    radius=10.0, # µm — backbone radius at the mid-point
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
# The bounding box reveals the footprint.  Note it is **larger than** a
# circular arc of the same nominal radius because the clothoid curve needs
# extra length at the entry and exit to complete the curvature transition:

# %%
print("bounding box:", bend.dbbox())

# %% [markdown]
# ## Arbitrary bend angles
#
# Set `angle` to any positive value in degrees.  Here a 45° bend:

# %%
bend_45 = kf.cells.euler.bend_euler(
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
# ## Cladding with LayerEnclosure
#
# Pass a `LayerEnclosure` to automatically add slab or exclude regions:

# %%
enc = kf.LayerEnclosure(
    name="WGSTD",
    sections=[(L.WGCLAD, 2_000)],  # 2 µm cladding on each side (in DBU)
)

bend_clad = kf.cells.euler.bend_euler(
    width=0.5,
    radius=10.0,
    layer=L.WG,
    enclosure=enc,
)
bend_clad.plot()

# %% [markdown]
# ## Caching
#
# Like all `@kf.cell`-decorated functions, `bend_euler` is cached — the same
# parameters always return the **same object**:

# %%
b1 = kf.cells.euler.bend_euler(width=0.5, radius=10.0, layer=L.WG)
b2 = kf.cells.euler.bend_euler(width=0.5, radius=10.0, layer=L.WG)
print("same object?", b1 is b2)  # True

b3 = kf.cells.euler.bend_euler(width=0.5, radius=15.0, layer=L.WG)
print("different radius → same?", b1 is b3)  # False

# %% [markdown]
# ## Assembling an L-shaped arm
#
# Connect two straights and an euler bend into a simple L-shaped waveguide:

# %%
@kf.cell
def l_arm() -> kf.KCell:
    c = kf.kcl.kcell()

    s_in  = kf.cells.straight.straight(width=0.5, length=5.0, layer=L.WG)
    b     = kf.cells.euler.bend_euler(width=0.5, radius=10.0, layer=L.WG)
    s_out = kf.cells.straight.straight(width=0.5, length=5.0, layer=L.WG)

    i_in  = c << s_in
    i_b   = c << b
    i_out = c << s_out

    i_b.connect("o1", i_in, "o2")    # snap bend input to straight output
    i_out.connect("o1", i_b, "o2")   # snap exit straight to bend output

    c.add_port(port=i_in.ports["o1"], name="o1")
    c.add_port(port=i_out.ports["o2"], name="o2")
    return c


arm = l_arm()
arm.plot()

# %% [markdown]
# ## Effective routing radius
#
# Because the clothoid curve extends beyond the nominal radius, the actual
# footprint radius is larger than the `radius` argument.
# `kf.routing.optical.get_radius` returns the correct value to use when calling
# `route_loopback` or similar functions:

# %%
effective_r = kf.routing.optical.get_radius(bend)
print(f"nominal radius: 10.0 µm  →  effective footprint radius: {effective_r:.3f} µm")

# %% [markdown]
# ## S-bend
#
# An Euler S-bend connects two **parallel** waveguides offset by `offset` µm.
# The algorithm automatically finds the bend angle required to achieve the
# requested offset; if the offset is too large for the chosen radius it inserts
# a short straight section at the apex.

# %%
sbend = kf.cells.euler.bend_s_euler(
    offset=5.0,   # µm — lateral shift between input and output
    width=0.5,
    radius=10.0,
    layer=L.WG,
)
sbend.plot()

# %%
for p in sbend.ports:
    print(f"{p.name}: width={p.dwidth:.3f} µm  trans={p.trans}")

# %% [markdown]
# Both ports face in the **same direction** (east) — `o1` on the left,
# `o2` offset upward by `offset` µm.
#
# A negative `offset` flips the S-bend downward:

# %%
sbend_neg = kf.cells.euler.bend_s_euler(
    offset=-5.0,
    width=0.5,
    radius=10.0,
    layer=L.WG,
)
sbend_neg.plot()

# %% [markdown]
# ## Production use — the factory pattern
#
# `kf.cells.euler.bend_euler` is bound to kfactory's internal demo `KCLayout`.
# For a real PDK, create factories bound to your own layout:

# %%
my_kcl = kf.KCLayout("MyPDK", infos=LAYER)

bend_fn   = kf.factories.euler.bend_euler_factory(kcl=my_kcl)
sbend_fn  = kf.factories.euler.bend_s_euler_factory(kcl=my_kcl)

b_pdk = bend_fn(width=0.5, radius=10.0, layer=L.WG)
print("cell belongs to:", b_pdk.kcl.name)

# %% [markdown]
# The factory also accepts a `port_type` argument (default `"optical"`) and
# `additional_info` for injecting metadata into `cell.info`:

# %%
bend_fn_meta = kf.factories.euler.bend_euler_factory(
    kcl=my_kcl,
    additional_info={"pdk": "MyPDK", "component_type": "bend_euler"},
)

b_meta = bend_fn_meta(width=0.5, radius=10.0, layer=L.WG)
print("cell info:", dict(b_meta.info))

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Components overview & gallery | [Components: Overview](overview.py) |
# | Circular (constant-radius) bends | [Components: Circular Bends](circular.py) |
# | Parameterised cells & caching | [Components: PCells](pcells.py) |
# | Factory functions reference | [Components: Factories](factories.py) |
# | Optical routing with euler bends | [Routing: Optical](../routing/optical.py) |
# | All-angle routing | [Routing: All-Angle](../routing/all_angle.py) |
# | Effective radius vs nominal radius | [Routing: Manhattan](../routing/manhattan.py) |

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
# The straight waveguide is the most fundamental photonic building block — a
# simple rectangular cross-section of core material, optionally surrounded by
# slab or exclude regions.
#
# ```
# ┌─────────────────────────────┐
# │        Slab/Exclude         │
# ├─────────────────────────────┤
# │                             │
# │            Core             │  ← width
# │                             │
# ├─────────────────────────────┤
# │        Slab/Exclude         │
# └─────────────────────────────┘
#         ←── length ──→
# ```
#
# ## API summary
#
# | Function | Unit system | When to use |
# |---|---|---|
# | `kf.cells.straight.straight(width, length, layer)` | µm | Quick prototyping / learning |
# | `kf.cells.straight.straight_dbu(width, length, layer)` | DBU | Direct DBU control |
# | `kf.factories.straight.straight_dbu_factory(kcl=...)` | DBU | Production PDK |
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
# ## Basic straight in µm
#
# `kf.cells.straight.straight` takes **width** and **length** in **micrometres**
# and a `kdb.LayerInfo` object for the core layer.  It returns a cached `KCell`.

# %%
wg = kf.cells.straight.straight(
    width=0.5,   # µm
    length=10.0, # µm
    layer=L.WG,
)
wg.plot()

# %% [markdown]
# The cell has two ports named **`o1`** (west, pointing left) and **`o2`**
# (east, pointing right):

# %%
for p in wg.ports:
    print(f"{p.name}: width={p.dwidth:.3f} µm  trans={p.trans}")

# %% [markdown]
# The bounding box confirms the geometry:

# %%
print("bounding box:", wg.dbbox())  # DBox in µm

# %% [markdown]
# ## Basic straight in DBU
#
# `kf.cells.straight.straight_dbu` accepts **integer** DBU values
# (`1 µm = 1000 DBU` for the default 1 nm grid).  The width must be
# an **even** number of DBU so that the port sits exactly on the grid centre.

# %%
wg_dbu = kf.cells.straight.straight_dbu(
    width=500,    # DBU  (= 0.5 µm)
    length=10_000, # DBU  (= 10 µm)
    layer=L.WG,
)
print("bbox (DBU):", wg_dbu.bbox())
print("port o2 trans:", wg_dbu.ports["o2"].trans)

# %% [markdown]
# ## Adding cladding with LayerEnclosure
#
# Pass a `LayerEnclosure` to automatically grow slab or exclude regions
# around the core.  The enclosure sections use **DBU** integers:

# %%
wg_enc = kf.LayerEnclosure(
    name="WGSTD",
    sections=[(L.WGCLAD, 2_000)],  # 2 µm cladding on each side
)

wg_clad = kf.cells.straight.straight(
    width=0.5,
    length=10.0,
    layer=L.WG,
    enclosure=wg_enc,
)
wg_clad.plot()

# %% [markdown]
# The bounding box now includes the 2 µm cladding above and below:

# %%
print("bbox with cladding:", wg_clad.dbbox())  # total height = 0.5 + 2×2 = 4.5 µm

# %% [markdown]
# ## Caching behaviour
#
# `kf.cells.straight.straight` is decorated with `@kf.cell`, so calling it
# twice with the same parameters returns the **same object**:

# %%
wg_a = kf.cells.straight.straight(width=0.5, length=10.0, layer=L.WG)
wg_b = kf.cells.straight.straight(width=0.5, length=10.0, layer=L.WG)
print("same object?", wg_a is wg_b)  # True

wg_c = kf.cells.straight.straight(width=0.5, length=20.0, layer=L.WG)
print("different length → same?", wg_a is wg_c)  # False

# %% [markdown]
# ## Assembling a waveguide path
#
# Use `<<` to place instances and `instance.connect(port, other, other_port)` to
# snap them together.  Here two straights of different lengths are connected
# end-to-end:

# %%
@kf.cell
def path_example() -> kf.KCell:
    c = kf.kcl.kcell()

    s10 = kf.cells.straight.straight_dbu(width=500, length=10_000, layer=L.WG)
    s5  = kf.cells.straight.straight_dbu(width=500, length=5_000,  layer=L.WG)

    i1 = c << s10
    i2 = c << s5
    i2.connect("o1", i1, "o2")  # snap o1 of s5 → o2 of s10

    c.add_port(port=i1.ports["o1"], name="o1")  # expose input
    c.add_port(port=i2.ports["o2"], name="o2")  # expose output
    return c


path = path_example()
path.plot()

# %% [markdown]
# The total length is 10 + 5 = 15 µm:

# %%
print("total length:", path.dbbox().width(), "µm")

# %% [markdown]
# ## Production use — the factory pattern
#
# When building a PDK you should **not** use `kf.cells.straight.straight`
# directly because it is bound to kfactory's internal demo `KCLayout`.
# Instead, create a factory bound to your own layout:

# %%
# In a real PDK this would be your own KCLayout instance:
# Pass the class (not an instance) — KCLayout calls infos() internally
my_kcl = kf.KCLayout("MyPDK", infos=LAYER)

straight_fn = kf.factories.straight.straight_dbu_factory(kcl=my_kcl)

# straight_fn behaves identically to straight_dbu but uses my_kcl:
s_pdk = straight_fn(width=500, length=10_000, layer=L.WG)
print("cell belongs to:", s_pdk.kcl.name)

# %% [markdown]
# ### Width rules
#
# The DBU width **must be even** — this ensures the port centre lies exactly on
# the integer grid.  Odd widths raise a `ValueError`:

# %%
try:
    kf.cells.straight.straight_dbu(width=501, length=5_000, layer=L.WG)
except ValueError as e:
    print("Error:", e)

# %% [markdown]
# To convert a µm width to DBU use `kf.kcl.to_dbu` and round to the nearest
# even integer:

# %%
width_um = 0.505  # µm
width_dbu = round(kf.kcl.to_dbu(width_um) / 2) * 2  # round to even
print(f"{width_um} µm → {width_dbu} DBU (even)")

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Width tapers (linear transitions) | [Components: Tapers](taper.py) |
# | Parameterised cells & caching | [Components: PCells](pcells.py) |
# | Cross-sections & cladding specs | [Enclosures: Cross-Sections](../enclosures/cross_sections.py) |
# | Layer enclosures (auto-cladding) | [Enclosures: Layer Enclosure](../enclosures/layer_enclosure.py) |
# | Factory functions reference | [Components: Factories](factories.py) |
# | Routing with straight waveguides | [Routing: Overview](../routing/overview.py) |

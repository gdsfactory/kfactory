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
# A linear taper transitions a waveguide from one width to another over a fixed
# length.  Tapers appear everywhere in photonic circuits — coupling between
# different waveguide widths, mode-matching to fibre, and connecting
# cross-sections with different enclosures.
#
# ```
#            __
#          _/  │  Slab/Exclude
#        _/  __│
#      _/  _/  │
#     │  _/    │
#     │_/      │
#     │_       │  Core
#     │ \_     │
#     │_  \_   │
#       \_  \__│
#         \_   │
#           \__│  Slab/Exclude
#
#   o1  (width1)               o2  (width2)
# ```
#
# ## API summary
#
# | Function | Unit system | When to use |
# |---|---|---|
# | `kf.cells.taper.taper(width1, width2, length, layer)` | µm | Quick prototyping / learning |
# | `kf.cells.taper.taper_dbu(width1, width2, length, layer)` | DBU | Direct DBU control |
# | `kf.factories.taper.taper_factory(kcl=...)` | DBU | Production PDK |
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
# ## Basic taper (µm API)
#
# `kf.cells.taper.taper` takes **width1**, **width2**, and **length** all in
# **µm**, plus a `kdb.LayerInfo` for the core layer.

# %%
t = kf.cells.taper.taper(
    width1=0.5,   # µm — input width
    width2=2.0,   # µm — output width
    length=10.0,  # µm — taper length
    layer=L.WG,
)
t.plot()

# %% [markdown]
# Two ports are created:
# - **`o1`** — input port at `x=0`, pointing west (rotation 2 = 180°), width = `width1`
# - **`o2`** — output port at `x=length`, pointing east (rotation 0 = 0°), width = `width2`

# %%
for p in t.ports:
    print(f"{p.name}: width={p.dwidth:.3f} µm  trans={p.trans}")

# %% [markdown]
# The bounding box confirms the geometry:

# %%
print("bounding box:", t.dbbox())

# %% [markdown]
# ## Tapers in both directions
#
# A taper with `width1 > width2` simply narrows the waveguide.  The port names
# (`o1`, `o2`) follow input → output order regardless of which end is wider.

# %%
t_narrow = kf.cells.taper.taper(
    width1=2.0,
    width2=0.5,
    length=10.0,
    layer=L.WG,
)
t_narrow.plot()

# %%
for p in t_narrow.ports:
    print(f"{p.name}: width={p.dwidth:.3f} µm")

# %% [markdown]
# ## Symmetric taper (same width on both sides)
#
# When `width1 == width2` you get a plain rectangular waveguide — equivalent to
# a straight waveguide.  This is useful when you want a uniform component type
# across a circuit.

# %%
t_straight = kf.cells.taper.taper(
    width1=0.5,
    width2=0.5,
    length=5.0,
    layer=L.WG,
)
t_straight.plot()

# %% [markdown]
# ## Cladding with LayerEnclosure
#
# Pass a `LayerEnclosure` to automatically add slab or exclude regions.  The
# enclosure is applied with `apply_minkowski_y` — it expands the core polygon in
# the Y direction, creating cladding that exactly follows the taper profile.

# %%
enc = kf.LayerEnclosure(
    name="WGSTD",
    sections=[(L.WGCLAD, 2_000)],  # 2 µm cladding (in DBU — 1 DBU = 1 nm)
)

t_clad = kf.cells.taper.taper(
    width1=0.5,
    width2=2.0,
    length=10.0,
    layer=L.WG,
    enclosure=enc,
)
t_clad.plot()

# %% [markdown]
# ## DBU API
#
# `taper_dbu` accepts widths and length in **database units (DBU)**.  By default
# kfactory uses 1 nm/DBU, so multiply µm values by 1000:

# %%
t_dbu = kf.cells.taper.taper_dbu(
    width1=500,    # DBU → 0.5 µm
    width2=2000,   # DBU → 2.0 µm
    length=10_000, # DBU → 10 µm
    layer=L.WG,
)
print("bounding box (DBU):", t_dbu.bbox())
print("bounding box (µm): ", t_dbu.dbbox())

# %% [markdown]
# ## Caching
#
# Like all `@kf.cell`-decorated functions, `taper` is cached — the same
# parameters always return the **same object**:

# %%
ta = kf.cells.taper.taper(width1=0.5, width2=2.0, length=10.0, layer=L.WG)
tb = kf.cells.taper.taper(width1=0.5, width2=2.0, length=10.0, layer=L.WG)
print("same object?", ta is tb)  # True

tc = kf.cells.taper.taper(width1=0.5, width2=3.0, length=10.0, layer=L.WG)
print("different width2 → same?", ta is tc)  # False

# %% [markdown]
# ## Assembling a mode-adapter
#
# A typical application: coupling from a narrow access waveguide into a wider
# multimode waveguide with tapers on both ends.

# %%
@kf.cell
def mode_adapter() -> kf.KCell:
    c = kf.kcl.kcell()

    wg_narrow = 0.5   # µm
    wg_wide   = 2.0   # µm
    taper_len = 10.0  # µm
    wg_len    = 20.0  # µm

    t_in  = kf.cells.taper.taper(width1=wg_narrow, width2=wg_wide, length=taper_len, layer=L.WG)
    wg    = kf.cells.straight.straight(width=wg_wide, length=wg_len, layer=L.WG)
    t_out = kf.cells.taper.taper(width1=wg_wide, width2=wg_narrow, length=taper_len, layer=L.WG)

    i_in  = c << t_in
    i_wg  = c << wg
    i_out = c << t_out

    i_wg.connect("o1", i_in, "o2")
    i_out.connect("o1", i_wg, "o2")

    c.add_port(port=i_in.ports["o1"],  name="o1")
    c.add_port(port=i_out.ports["o2"], name="o2")
    return c


adapter = mode_adapter()
adapter.plot()

# %%
for p in adapter.ports:
    print(f"{p.name}: width={p.dwidth:.3f} µm  trans={p.trans}")

# %% [markdown]
# ## Production use — the factory pattern
#
# `kf.cells.taper.taper` is bound to kfactory's internal demo `KCLayout`.
# For a real PDK, create a factory bound to your own layout:

# %%
my_kcl = kf.KCLayout("MyPDK_Taper", infos=LAYER)

taper_fn = kf.factories.taper.taper_factory(kcl=my_kcl)

t_pdk = taper_fn(
    width1=my_kcl.to_dbu(0.5),   # factory takes DBU values
    width2=my_kcl.to_dbu(2.0),
    length=my_kcl.to_dbu(10.0),
    layer=L.WG,
)
print("cell belongs to:", t_pdk.kcl.name)
print("bounding box:   ", t_pdk.dbbox())

# %% [markdown]
# The factory also accepts `additional_info` for injecting metadata into
# `cell.info`, and `port_type` to label ports differently (e.g. `"electrical"`):

# %%
taper_fn_meta = kf.factories.taper.taper_factory(
    kcl=my_kcl,
    additional_info={"pdk": "MyPDK_Taper", "component_type": "taper"},
)

t_meta = taper_fn_meta(
    width1=my_kcl.to_dbu(0.5),
    width2=my_kcl.to_dbu(2.0),
    length=my_kcl.to_dbu(10.0),
    layer=L.WG,
)
print("cell info:", dict(t_meta.info))

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Straight waveguide | [Components: Straight](straight.py) |
# | Cross-sections & cladding specs | [Enclosures: Cross-Sections](../enclosures/cross_sections.py) |
# | Layer enclosures (auto-cladding) | [Enclosures: Layer Enclosure](../enclosures/layer_enclosure.py) |
# | Parameterised cells & caching | [Components: PCells](pcells.py) |
# | Factory functions reference | [Components: Factories](factories.py) |

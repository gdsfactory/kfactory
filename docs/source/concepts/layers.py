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
# # Layers
#
# In GDS-based photonic and electronic design, a **layer** is an integer pair
# `(layer_number, datatype)` that identifies a fabrication process step — for example
# waveguide core, metal trace, or doping implant.  kfactory provides three abstractions
# for working with layers:
#
# | Class | Best for |
# |-------|----------|
# | `LayerInfos` | Defining your process layer palette (the primary approach) |
# | `LayerEnum` | When you need layers to behave as plain integers (KLayout-native style) |
# | `LayerStack` | 3-D simulation / cross-section metadata (thickness, material, z-position) |
#
# This page walks through each.

# %%
import kfactory as kf
from kfactory.layer import LayerLevel, layerenum_from_dict

# %% [markdown]
# ## `LayerInfos` — define your layer palette
#
# `LayerInfos` is a [Pydantic](https://docs.pydantic.dev) model.  Subclass it and declare
# each layer as a class attribute typed `kf.kdb.LayerInfo`:

# %%
class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)      # waveguide core
    WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)    # waveguide exclusion zone
    CLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(4, 0)    # cladding
    FLOORPLAN: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10, 0)

L = LAYER()

# %% [markdown]
# Each field is a `kdb.LayerInfo(layer_number, datatype)`.  The field name is
# automatically stored as the layer's `.name` attribute, which is useful for DRC
# reports and technology files.
#
# Instantiating the class runs Pydantic validation — it checks that every field is a
# `kdb.LayerInfo` with valid `layer` and `datatype` numbers.

# %%
print(L.WG)          # LayerInfo(1/0) — KLayout's string representation
print(L.WG.layer)    # 1
print(L.WG.datatype) # 0
print(L.WG.name)     # "WG"  — auto-set from the field name

# %% [markdown]
# ### Registering layers with a layout
#
# A `KCLayout` (the global `kf.kcl` by default) must know about your layers so that
# `find_layer` and other helpers work correctly.  Assign your `LayerInfos` instance to
# `kcl.infos`:

# %%
kf.kcl.infos = L

# %% [markdown]
# ### Looking up the integer layer index
#
# KLayout stores shapes using an integer *layer index* (not the `(layer, datatype)` pair
# directly).  Use `kcl.find_layer` to convert a `LayerInfo` to this index:

# %%
idx_wg = kf.kcl.find_layer(L.WG)
print(f"WG layer index: {idx_wg}")

# You can also look up by number/datatype directly:
idx_wg2 = kf.kcl.find_layer(1, 0)
print(f"Same index via (layer, datatype): {idx_wg2}")
print(f"Indices match: {idx_wg == idx_wg2}")

# %% [markdown]
# ### Accessing layers by name
#
# `LayerInfos` supports dict-style access, which is useful in generic code:

# %%
print(L["CLAD"])   # same as L.CLAD

# %% [markdown]
# ### Iterating over all layers
#
# Because `LayerInfos` is a Pydantic model, `model_fields` gives you the declared
# layers and `model_dump()` serialises them:

# %%
for name in L.model_fields:
    li = getattr(L, name)
    print(f"  {name:12s}  layer={li.layer}  datatype={li.datatype}")

# %% [markdown]
# ## `LayerEnum` — integer-style layer access
#
# `LayerEnum` is an alternative that maps layer names to KLayout *layer indices*
# (integers).  It is useful when interfacing with older KLayout APIs that expect an
# integer directly, or when you want to use a layer as a dict key with O(1) lookup.
#
# Use `layerenum_from_dict` to convert a `LayerInfos` into a `LayerEnum`:

# %%
LE = layerenum_from_dict(L)

print(type(LE.WG))         # <enum 'LAYER'>
print(int(LE.WG))          # integer layer index in kf.kcl.layout
print(LE.WG.layer)         # 1  — original layer number
print(LE.WG.datatype)      # 0  — original datatype
print(LE.WG[0], LE.WG[1]) # tuple-style access: (layer, datatype)

# %% [markdown]
# Both `LayerInfos` and `LayerEnum` are valid everywhere kfactory expects a layer —
# `kf.kcl.find_layer` accepts a `LayerInfo`, a `LayerEnum`, or an `(int, int)` tuple.

# %%
# LayerInfos → find_layer gives the integer index:
print(kf.kcl.find_layer(L.WG))         # from LayerInfos
print(kf.kcl.find_layer(1, 0))         # from (layer, datatype) pair

# LayerEnum members *are* layer indices already:
print(int(LE.WG))                       # same integer, no find_layer needed

# %% [markdown]
# ## `LayerStack` — 3-D process metadata
#
# `LayerStack` stores per-layer physical properties needed for 3-D simulation, cross-
# section rendering, or fabrication export.  Each entry is a `LayerLevel`:

# %%
stack = kf.LayerStack(
    wg_core=LayerLevel(
        layer=L.WG,
        zmin=0.0,
        thickness=0.22,
        material="Si",
        sidewall_angle=85.0,
    ),
    cladding=LayerLevel(
        layer=L.CLAD,
        zmin=-3.0,
        thickness=3.22,
        material="SiO2",
    ),
)

# %% [markdown]
# `LayerLevel` fields:
#
# | Field | Type | Meaning |
# |-------|------|---------|
# | `layer` | `(int, int)` or `kdb.LayerInfo` | GDS layer |
# | `zmin` | float µm | Bottom of the material |
# | `thickness` | float µm | Material thickness |
# | `material` | str \| None | Material name (for simulation) |
# | `sidewall_angle` | float degrees | Etch sidewall angle (90° = vertical) |
# | `info` | `Info` | Free-form simulation metadata |

# %%
# Access individual levels by attribute or dict key
print(stack["wg_core"].thickness)   # 0.22
print(stack.cladding.material)       # SiO2

# Convenience helpers for simulation
print(stack.get_layer_to_thickness())   # {(1,0): 0.22, (4,0): 3.22}
print(stack.get_layer_to_material())    # {(1,0): 'Si', (4,0): 'SiO2'}

# %% [markdown]
# ## Putting it all together: a minimal PDK layer set
#
# A typical PDK definition combines `LayerInfos` and `LayerStack` in one module:

# %%
class PDK_LAYER(kf.LayerInfos):
    WG:         kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WG_TRENCH:  kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
    METAL1:     kf.kdb.LayerInfo = kf.kdb.LayerInfo(11, 0)
    METAL2:     kf.kdb.LayerInfo = kf.kdb.LayerInfo(12, 0)
    FLOORPLAN:  kf.kdb.LayerInfo = kf.kdb.LayerInfo(99, 0)

pdk_layers = PDK_LAYER()

pdk_stack = kf.LayerStack(
    wg=LayerLevel(layer=pdk_layers.WG,     zmin=0.0,  thickness=0.22, material="Si"),
    m1=LayerLevel(layer=pdk_layers.METAL1, zmin=0.5,  thickness=0.5,  material="Al"),
    m2=LayerLevel(layer=pdk_layers.METAL2, zmin=1.2,  thickness=0.5,  material="Al"),
)

print("Layer palette:")
for name in pdk_layers.model_fields:
    li = getattr(pdk_layers, name)
    print(f"  {name:12s}  ({li.layer}/{li.datatype})")

print("\n3-D stack:")
for name, level in pdk_stack.layers.items():
    print(f"  {name:6s}  z={level.zmin:.1f}…{level.zmin+level.thickness:.2f} µm  {level.material}")

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | KCLayout — the layout registry that owns layers | [Core Concepts: KCLayout](kclayout.py) |
# | Cross-sections built on top of layers | [Enclosures: Cross-Sections](../enclosures/cross_sections.py) |
# | LayerLevel and full 3-D stack in a PDK | [PDK: Technology & Layer Stack](../pdk/technology.py) |
# | Assembling a full PDK with layers | [PDK: Creating a PDK](../pdk/creating_pdk.py) |

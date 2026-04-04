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
# # Technology & Layer Stack
#
# A **LayerStack** describes the vertical cross-section of your fabrication process:
# which physical materials are deposited on which GDS layers, at what height (`zmin`),
# and with what thickness. This information is used by simulation exporters
# (e.g. Tidy3D, MEEP, Lumerical) that consume kfactory layouts.
#
# This page covers:
#
# | Topic | What you'll learn |
# |---|---|
# | `LayerLevel` | One physical layer in the process |
# | `LayerStack` | Collection of `LayerLevel`s |
# | `Info` | Extra metadata (mesh order, refractive index, etch type, …) |
# | Attaching a stack to a PDK | Best-practice pattern |
# | Querying the stack | Per-layer lookups |

# %% [markdown]
# ## 1 · LayerLevel — one process step
#
# `LayerLevel` describes a single physical layer:
#
# | Parameter | Type | Meaning |
# |---|---|---|
# | `layer` | `(int, int)` or `kdb.LayerInfo` | GDS layer / datatype |
# | `zmin` | `float` (µm) | Bottom of the slab |
# | `thickness` | `float` (µm) | Vertical thickness |
# | `material` | `str` | Material name (passed to simulator) |
# | `sidewall_angle` | `float` (°) | 0° = vertical, 90° = horizontal |
# | `info` | `Info` | Optional simulation metadata |

# %%
import kfactory as kf
from kfactory.layer import Info, LayerLevel, LayerStack

# Silicon waveguide core: 220 nm thick, starts at z=0
wg_level = LayerLevel(
    layer=(1, 0),
    zmin=0.0,
    thickness=0.22,   # µm
    material="si",
    sidewall_angle=80.0,  # near-vertical etch
)

print(wg_level)

# %% [markdown]
# ### Info — simulation metadata
#
# Pass an `Info` object to attach extra metadata that simulators can consume.
# Common fields:
#
# | Field | Meaning |
# |---|---|
# | `mesh_order` | Lower = higher priority in mesher (1 overrides 2) |
# | `refractive_index` | `float` (int/float only; complex must be stored as a string) |
# | `type` | `"grow"`, `"etch"`, `"implant"`, or `"background"` |

# %%
wg_level_with_info = LayerLevel(
    layer=(1, 0),
    zmin=0.0,
    thickness=0.22,
    material="si",
    sidewall_angle=80.0,
    info=Info(
        mesh_order=1,
        refractive_index=3.47,
        type="grow",
    ),
)
print(wg_level_with_info.info)

# %% [markdown]
# ## 2 · LayerStack — the full process
#
# `LayerStack` is a named collection of `LayerLevel`s. Pass levels as keyword arguments;
# the keyword name becomes the layer's logical name in the stack.

# %%
stack = LayerStack(
    # --- core waveguide layers ---
    wg=LayerLevel(
        layer=(1, 0),
        zmin=0.0,
        thickness=0.22,
        material="si",
        sidewall_angle=80.0,
        info=Info(mesh_order=1, refractive_index=3.47, type="grow"),
    ),
    slab=LayerLevel(
        layer=(3, 0),
        zmin=0.0,
        thickness=0.09,   # partial etch leaves 90 nm slab
        material="si",
        sidewall_angle=70.0,
        info=Info(mesh_order=2, refractive_index=3.47, type="grow"),
    ),
    # --- oxide cladding ---
    clad=LayerLevel(
        layer=(111, 0),
        zmin=-3.0,
        thickness=3.22,   # 3 µm below + 0.22 µm above wg top
        material="sio2",
        info=Info(mesh_order=3, refractive_index=1.44, type="background"),
    ),
    # --- metal ---
    metal=LayerLevel(
        layer=(41, 0),
        zmin=0.5,
        thickness=1.0,
        material="al",
        info=Info(mesh_order=1, type="grow"),
    ),
)

print(stack)

# %% [markdown]
# ## 3 · Querying the stack
#
# `LayerStack` exposes several lookup helpers. Keys are `(layer, datatype)` tuples.

# %%
print("Thicknesses:")
for layer_tuple, t in stack.get_layer_to_thickness().items():
    print(f"  {layer_tuple}: {t} µm")

print("\nMaterials:")
for layer_tuple, mat in stack.get_layer_to_material().items():
    print(f"  {layer_tuple}: {mat}")

print("\nZ-min positions:")
for layer_tuple, zmin in stack.get_layer_to_zmin().items():
    print(f"  {layer_tuple}: {zmin} µm")

print("\nSidewall angles:")
for layer_tuple, angle in stack.get_layer_to_sidewall_angle().items():
    print(f"  {layer_tuple}: {angle}°")

# %% [markdown]
# Access individual levels by name or by index:

# %%
wg = stack["wg"]
print(f"wg zmin={wg.zmin} µm, thickness={wg.thickness} µm, top={wg.zmin + wg.thickness} µm")

# %% [markdown]
# ## 4 · Attaching a stack to a PDK
#
# A `LayerStack` is not built into `KCLayout` — you attach it to your PDK module as a
# module-level constant alongside `LAYER` and the layout object.
#
# Best practice: define everything in one module and import `pdk`, `LAYER`, and `STACK`
# from it.

# %%
# --- pdk_with_stack.py (inline for demo) ---

class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    SLAB: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
    METAL: kf.kdb.LayerInfo = kf.kdb.LayerInfo(41, 0)
    FLOORPLAN: kf.kdb.LayerInfo = kf.kdb.LayerInfo(99, 0)


pdk = kf.KCLayout("DEMO_TECH_PDK", infos=LAYER)
L = pdk.infos   # LayerInfos instance; use for layer objects

STACK = LayerStack(
    wg=LayerLevel(
        layer=(L.WG.layer, L.WG.datatype),
        zmin=0.0,
        thickness=0.22,
        material="si",
        sidewall_angle=80.0,
        info=Info(mesh_order=1, refractive_index=3.47, type="grow"),
    ),
    clad=LayerLevel(
        layer=(L.WGCLAD.layer, L.WGCLAD.datatype),
        zmin=-3.0,
        thickness=3.22,
        material="sio2",
        info=Info(mesh_order=3, refractive_index=1.44, type="background"),
    ),
)

print(f"PDK:   {pdk}")
print(f"Stack: {list(STACK.layers.keys())} layers defined")

# %% [markdown]
# ## 5 · Serialising the stack
#
# `to_dict()` returns a plain Python dict — useful for saving to YAML or JSON, or
# for passing to simulators that don't import kfactory directly.

# %%
import json

d = stack.to_dict()
print(json.dumps(d, indent=2, default=str))

# %% [markdown]
# ## Summary
#
# | Class | Key role |
# |---|---|
# | `LayerLevel` | Single process step: layer, z position, thickness, material |
# | `Info` | Simulation extras: mesh order, refractive index, etch type |
# | `LayerStack` | Named dict of `LayerLevel`s; exposes per-layer lookup helpers |
#
# Keep `STACK` as a module-level constant in your PDK module alongside `pdk` and `LAYER`.
# Simulators can then `from my_pdk import pdk, LAYER, STACK` and get everything they need
# from a single import.

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Creating a full PDK | [PDK: Creating a PDK](creating_pdk.py) |
# | Layer definitions | [Core Concepts: Layers](../concepts/layers.py) |
# | Cross-sections (port geometry) | [Enclosures: Cross-Sections](../enclosures/cross_sections.py) |
# | KCLayout (owns the cell DB) | [Core Concepts: KCLayout](../concepts/kclayout.py) |

# Technology &amp; Layer Stack

A **LayerStack** describes the vertical cross-section of your fabrication process: which physical materials are deposited on which GDS layers, at what height (`zmin`), and with what thickness. This information is used by simulation exporters (e.g. Tidy3D, MEEP, Lumerical) that consume kfactory layouts.

This page covers:

| Topic | What you'll learn |
| --- | --- |
| `LayerLevel` | One physical layer in the process |
| `LayerStack` | Collection of `LayerLevel`s |
| `Info` | Extra metadata (mesh order, refractive index, etch type, …) |
| Attaching a stack to a PDK | Best-practice pattern |
| Querying the stack | Per-layer lookups |

## 1 · LayerLevel — one process step

`LayerLevel` describes a single physical layer:

| Parameter | Type | Meaning |
| --- | --- | --- |
| `layer` | `(int, int)` or `kdb.LayerInfo` | GDS layer / datatype |
| `zmin` | `float` (µm) | Bottom of the slab |
| `thickness` | `float` (µm) | Vertical thickness |
| `material` | `str` | Material name (passed to simulator) |
| `sidewall_angle` | `float` (°) | 0° = vertical, 90° = horizontal |
| `info` | `Info` | Optional simulation metadata |

```
import kfactory as kf
from kfactory.layer import Info, LayerLevel, LayerStack

# Silicon waveguide core: 220 nm thick, starts at z=0
wg_level = LayerLevel(
    layer=(1, 0),
    zmin=0.0,
    thickness=0.22,  # µm
    material="si",
    sidewall_angle=80.0,  # near-vertical etch
)

print(wg_level)
```

```
layer=(1, 0) thickness=0.22 thickness_tolerance=None zmin=0.0 material='si' sidewall_angle=80.0 z_to_bias=None info=Info()
```

### Info — simulation metadata

Pass an `Info` object to attach extra metadata that simulators can consume. Common fields:

| Field | Meaning |
| --- | --- |
| `mesh_order` | Lower = higher priority in mesher (1 overrides 2) |
| `refractive_index` | `float` (int/float only; complex must be stored as a string) |
| `type` | `"grow"`, `"etch"`, `"implant"`, or `"background"` |

```
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
```

```
Info(mesh_order=1, refractive_index=3.47, type='grow')
```

## 2 · LayerStack — the full process

`LayerStack` is a named collection of `LayerLevel`s. Pass levels as keyword arguments; the keyword name becomes the layer's logical name in the stack.

```
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
        thickness=0.09,  # partial etch leaves 90 nm slab
        material="si",
        sidewall_angle=70.0,
        info=Info(mesh_order=2, refractive_index=3.47, type="grow"),
    ),
    # --- oxide cladding ---
    clad=LayerLevel(
        layer=(111, 0),
        zmin=-3.0,
        thickness=3.22,  # 3 µm below + 0.22 µm above wg top
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
```

```
layers={'wg': LayerLevel(layer=(1, 0), thickness=0.22, thickness_tolerance=None, zmin=0.0, material='si', sidewall_angle=80.0, z_to_bias=None, info=Info(mesh_order=1, refractive_index=3.47, type='grow')), 'slab': LayerLevel(layer=(3, 0), thickness=0.09, thickness_tolerance=None, zmin=0.0, material='si', sidewall_angle=70.0, z_to_bias=None, info=Info(mesh_order=2, refractive_index=3.47, type='grow')), 'clad': LayerLevel(layer=(111, 0), thickness=3.22, thickness_tolerance=None, zmin=-3.0, material='sio2', sidewall_angle=0.0, z_to_bias=None, info=Info(mesh_order=3, refractive_index=1.44, type='background')), 'metal': LayerLevel(layer=(41, 0), thickness=1.0, thickness_tolerance=None, zmin=0.5, material='al', sidewall_angle=0.0, z_to_bias=None, info=Info(mesh_order=1, type='grow'))}
```

## 3 · Querying the stack

`LayerStack` exposes several lookup helpers. Keys are `(layer, datatype)` tuples.

```
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
```

```
Thicknesses:
  (1, 0): 0.22 µm
  (3, 0): 0.09 µm
  (111, 0): 3.22 µm
  (41, 0): 1.0 µm

Materials:
  (1, 0): si
  (3, 0): si
  (111, 0): sio2
  (41, 0): al

Z-min positions:
  (1, 0): 0.0 µm
  (3, 0): 0.0 µm
  (111, 0): -3.0 µm
  (41, 0): 0.5 µm

Sidewall angles:
  (1, 0): 80.0°
  (3, 0): 70.0°
  (111, 0): 0.0°
  (41, 0): 0.0°
```

Access individual levels by name or by index:

```
wg = stack["wg"]
print(
    f"wg zmin={wg.zmin} µm, thickness={wg.thickness} µm, top={wg.zmin + wg.thickness} µm"
)
```

```
wg zmin=0.0 µm, thickness=0.22 µm, top=0.22 µm
```

## 4 · Attaching a stack to a PDK

A `LayerStack` is not built into `KCLayout` — you attach it to your PDK module as a module-level constant alongside `LAYER` and the layout object.

Best practice: define everything in one module and import `pdk`, `LAYER`, and `STACK` from it.

```
# --- pdk_with_stack.py (inline for demo) ---


class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    SLAB: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
    METAL: kf.kdb.LayerInfo = kf.kdb.LayerInfo(41, 0)
    FLOORPLAN: kf.kdb.LayerInfo = kf.kdb.LayerInfo(99, 0)


pdk = kf.KCLayout("DEMO_TECH_PDK", infos=LAYER)
L = pdk.infos  # LayerInfos instance; use for layer objects

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
```

```
PDK:   name='DEMO_TECH_PDK' layout=<klayout.dbcore.Layout object at 0x7fd8e6c44c20> layer_enclosures=LayerEnclosureModel(root={}) cross_sections={} enclosure=KCellEnclosure(enclosures=LayerEnclosureCollection(enclosures=[])) library=<klayout.dbcore.Library object at 0x7fd8e6d21d60> factories=<kfactory.layout.Factories object at 0x7fd8e6dbb750> virtual_factories=<kfactory.layout.Factories object at 0x7fd8e6bfd0f0> generic_factories={} tkcells={} infos=LAYER(WG=WG (1/0), SLAB=SLAB (3/0), WGCLAD=WGCLAD (111/0), METAL=METAL (41/0), FLOORPLAN=FLOORPLAN (99/0)) layer_stack=LayerStack(layers={}) netlist_layer_mapping={} sparameters_path=None interconnect_cml_path=None constants=Constants() rename_function=<function rename_clockwise_multi at 0x7fd9057687d0> thread_lock=<unlocked _thread.RLock object owner=0 count=0 at 0x7fd8e6c559f0> info=Info() settings=KCellSettings(version='3.2.2', klayout_version='0.30.12', meta_format='v3') decorators=<kfactory.decorators.Decorators object at 0x7fd8e6dbbb10> default_cell_output_type=<class 'kfactory.kcell.KCell'> default_vcell_output_type=<class 'kfactory.kcell.VKCell'> connectivity=[] routing_strategies={} technology_file=None layers=<aenum 'LAYER'>
Stack: ['wg', 'clad'] layers defined
```

## 5 · Serialising the stack

`to_dict()` returns a plain Python dict — useful for saving to YAML or JSON, or for passing to simulators that don't import kfactory directly.

```
import json

d = stack.to_dict()
print(json.dumps(d, indent=2, default=str))
```

```
{
  "wg": {
    "layer": [
      1,
      0
    ],
    "thickness": 0.22,
    "thickness_tolerance": null,
    "zmin": 0.0,
    "material": "si",
    "sidewall_angle": 80.0,
    "z_to_bias": null,
    "info": {
      "mesh_order": 1,
      "refractive_index": 3.47,
      "type": "grow"
    }
  },
  "slab": {
    "layer": [
      3,
      0
    ],
    "thickness": 0.09,
    "thickness_tolerance": null,
    "zmin": 0.0,
    "material": "si",
    "sidewall_angle": 70.0,
    "z_to_bias": null,
    "info": {
      "mesh_order": 2,
      "refractive_index": 3.47,
      "type": "grow"
    }
  },
  "clad": {
    "layer": [
      111,
      0
    ],
    "thickness": 3.22,
    "thickness_tolerance": null,
    "zmin": -3.0,
    "material": "sio2",
    "sidewall_angle": 0.0,
    "z_to_bias": null,
    "info": {
      "mesh_order": 3,
      "refractive_index": 1.44,
      "type": "background"
    }
  },
  "metal": {
    "layer": [
      41,
      0
    ],
    "thickness": 1.0,
    "thickness_tolerance": null,
    "zmin": 0.5,
    "material": "al",
    "sidewall_angle": 0.0,
    "z_to_bias": null,
    "info": {
      "mesh_order": 1,
      "type": "grow"
    }
  }
}
```

## Summary

| Class | Key role |
| --- | --- |
| `LayerLevel` | Single process step: layer, z position, thickness, material |
| `Info` | Simulation extras: mesh order, refractive index, etch type |
| `LayerStack` | Named dict of `LayerLevel`s; exposes per-layer lookup helpers |

Keep `STACK` as a module-level constant in your PDK module alongside `pdk` and `LAYER`. Simulators can then `from my_pdk import pdk, LAYER, STACK` and get everything they need from a single import.

## See Also

| Topic | Where |
| --- | --- |
| Creating a full PDK | [PDK: Creating a PDK](<https://gdsfactory.github.io/kfactory/dev/pdk/creating_pdk/index.md>) |
| Layer definitions | [Core Concepts: Layers](<https://gdsfactory.github.io/kfactory/dev/concepts/layers/index.md>) |
| Cross-sections (port geometry) | [Cross-Sections](<https://gdsfactory.github.io/kfactory/dev/components/cross_sections/index.md>) |
| KCLayout (owns the cell DB) | [Core Concepts: KCLayout](<https://gdsfactory.github.io/kfactory/dev/concepts/kclayout/index.md>) |

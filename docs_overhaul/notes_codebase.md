# Codebase Notes for Documentation Writing

## Source code map

All paths relative to `src/kfactory/`.

### Core (document first)
| Module | Size | Key exports | Notes |
|--------|------|-------------|-------|
| `kcell.py` | 4336 LOC | `KCell`, `DKCell`, `VKCell`, `BaseKCell` | Dynamic proxy for `kdb.Cell`. The central class. Has `@cell`/`@vcell` decorators for caching. |
| `port.py` | 1571 LOC | `Port`, `DPort`, `ProtoPort` | Position + width + layer + type. Transform-aware. |
| `ports.py` | 903 LOC | `Ports`, `DPorts`, `ProtoPorts` | Collection classes with filtering (by direction, layer, type, regex). |
| `instance.py` | 1099 LOC | `Instance`, `DInstance`, `VInstance` | Cell placements. `<<` operator for adding, `connect()` for port-based connection. |
| `layout.py` | 2245 LOC | `KCLayout`, `kcl`, `kcls` | Layout context. Owns cells, manages factories, routing strategies, cross-sections. `kcl` is the default global instance. |
| `layer.py` | 277 LOC | `LayerEnum`, `LayerInfos`, `LayerStack` | Layer definitions. `LayerInfos` maps names to `kdb.LayerInfo`. |
| `geometry.py` | 785 LOC | Helper classes for geometric ops | Wraps KLayout Point/Vector/Edge/Box/Polygon/Region. |
| `cross_section.py` | 573 LOC | `CrossSection`, `DCrossSection`, `SymmetricalCrossSection` | Defines port geometry. Links to enclosures. |
| `enclosure.py` | 1679 LOC | `LayerEnclosure`, `KCellEnclosure` | Auto-generate cladding/exclude via Minkowski sums. |
| `decorators.py` | 966 LOC | `cell`, `vcell` | Caching decorators. Cell naming from function name + params. |
| `conf.py` | 347 LOC | `Constants`, logging config | loguru integration, display settings, env vars. |

### Cells (pre-built components)
| Module | What it creates |
|--------|----------------|
| `cells/straight.py` | Straight waveguides |
| `cells/circular.py` | Circular bends (constant radius) |
| `cells/euler.py` | Euler bends (clothoid, varying radius) |
| `cells/bezier.py` | Bezier curve bends |
| `cells/taper.py` | Linear width transitions |
| `cells/virtual/` | Virtual (non-physical) variants of above |
| `cells/_demopdk.py` | Demo PDK with example components |

### Factories (cell generators)
| Module | Protocol |
|--------|----------|
| `factories/straight.py` | `StraightFactoryDBU`, `StraightFactoryUM` |
| `factories/circular.py` | Creates circular bend factories |
| `factories/euler.py` | Creates euler bend factories |
| `factories/bezier.py` | Creates bezier bend factories |
| `factories/taper.py` | Creates taper factories |
| `factories/virtual/` | Virtual factory variants |

### Routing (~300K total code)
| Module | Size | Use case |
|--------|------|----------|
| `routing/optical.py` | 71K | Bend-based optical routing: `route_bundle`, `place_manhattan`, `route_loopback`, `path_length_match` |
| `routing/electrical.py` | 49K | Wire-based electrical routing: `route_bundle`, `route_bundle_dual_rails`, `route_bundle_rf` |
| `routing/manhattan.py` | ~100K | Core manhattan routing algorithm |
| `routing/generic.py` | | `ManhattanRoute` class (return type for routes) |
| `routing/steps.py` | | Routing step definitions |
| `routing/length_functions.py` | | Path length calculation |
| `routing/aa/optical.py` | 20K | All-angle routing |
| `routing/utils.py` | | Debug utilities |

### Utilities
| Module | Purpose |
|--------|---------|
| `grid.py` | 923 LOC. `grid`/`grid_dbu`/`flexgrid`/`flexgrid_dbu`. Has great ASCII art docs in source (lines 36-73). |
| `packing.py` | `pack_kcells`, `pack_instances` via rectangle-packer |
| `utils/violations.py` | DRC violation detection and auto-fixing |
| `utils/fill.py` | Fill algorithms |
| `utils/simplify.py` | Path simplification |
| `utils/difftest.py` | Layout comparison/regression testing |

### Advanced
| Module | Purpose |
|--------|---------|
| `schematic.py` | 2771 LOC. Experimental. `Schematic`/`DSchematic` for netlist-driven layout. |
| `serialization.py` | 416 LOC. YAML serialization. |
| `session_cache.py` | `save_session`/`load_session` |
| `technology/layer_map.py` | `yaml_to_lyp` for KLayout technology files |

## Public API surface

77 exports in `__all__` (from `__init__.py`):
- Cell types: `KCell`, `DKCell`, `VKCell`, `BaseKCell`, `ProtoKCell`, `ProtoTKCell`
- Ports: `Port`, `DPort`, `ProtoPort`, `Ports`, `DPorts`, `ProtoPorts`
- Pins: `Pin`, `DPin`, `ProtoPin`, `Pins`, `DPins`
- Instances: `Instance`, `DInstance`, `VInstance`, `InstanceGroup`, `DInstanceGroup`, `VInstanceGroup`
- Instance ports: `InstancePorts`, `DInstancePorts`, `VInstancePorts`
- Cross-sections: `CrossSection`, `DCrossSection`, `SymmetricalCrossSection`
- Layers: `LayerEnum`, `LayerInfos`, `LayerStack`
- Enclosures: `KCellEnclosure`, `LayerEnclosure`
- Layout: `KCLayout`, `kcl`, `kcls`
- Decorators: `cell`, `vcell`
- Grid: `grid`, `grid_dbu`, `flexgrid`, `flexgrid_dbu`
- Schematic: `Netlist`, `Schematic`, `DSchematic`
- Utilities: `Info`, `KCellSettings`, `show`, `save_session`, `load_session`, `Constants`
- KLayout re-exports: `kdb`, `lay`, `rdb`

## Docstring quality

- Most public classes/functions have Google-style docstrings
- Type hints throughout (Python 3.12+)
- Some complex algorithms (routing internals, enclosure calculations) have sparse comments
- Good docstrings: `grid.py` (ASCII diagrams), `cross_section.py`, factory protocols
- Thin docstrings: some routing internals, `manhattan.py`

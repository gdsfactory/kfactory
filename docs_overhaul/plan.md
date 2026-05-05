# kfactory Documentation Overhaul Plan

## Goal

Bring kfactory documentation to gdsfactory-level quality. Current docs cover ~30% of features. Target: hierarchical navigation, executable notebook pages for every major feature, visual examples, and comprehensive coverage.

## Approach

Find uv in ~/.local/bin/uv
Incremental — one section at a time. Each step: create files, verify `just docs` builds, then move on.

## Format

- Primary format: **jupytext percent-format `.py` files** executed by `mkdocs-jupyter`
- Static `.md` only for: index, changelog, migration, FAQ, installation, klive setup
- Each `.py` notebook is self-contained (own imports, own `LayerInfos`)

## Target Navigation Structure

```
Home
├── index.md
├── gdsfactory.md

Getting Started
├── getting_started/prerequisites.md
├── getting_started/installation.md
├── getting_started/quickstart.py          (from intro.md)
├── getting_started/klive_setup.md

Core Concepts
├── concepts/kcell.py
├── concepts/layers.py
├── concepts/geometry.py                   (absorbs 00_geometry.py)
├── concepts/ports.py                      (absorbs port parts of 01_references.py)
├── concepts/instances.py                  (absorbs instance parts of 01_references.py)
├── concepts/kclayout.py                   (absorbs 04_KCL.py)
├── concepts/dbu_vs_um.py

Components & Factories
├── components/overview.py                 (visual gallery)
├── components/straight.py
├── components/euler.py
├── components/circular.py
├── components/bezier.py
├── components/taper.py
├── components/virtual.py
├── components/pcells.py                   (absorbs pcells.md)
├── components/factories.py

Cross-Sections & Enclosures
├── enclosures/cross_sections.py
├── enclosures/layer_enclosure.py          (absorbs 03_Enclosures.py)
├── enclosures/kcell_enclosure.py

Routing
├── routing/overview.py
├── routing/optical.py
├── routing/electrical.py
├── routing/manhattan.py
├── routing/all_angle.py
├── routing/bundle.py
├── routing/path_length.py

Layout Utilities
├── utilities/grid.py
├── utilities/packing.py
├── utilities/drc_fix.py                   (absorbs 02_DRC.py)
├── utilities/fill.py
├── utilities/difftest.py

PDK & Technology
├── pdk/creating_pdk.py
├── pdk/technology.py

Schematic-Driven Design
├── schematics/overview.py                 (absorbs 05_Schematics.py)
├── schematics/netlist.py

How-To Guides
├── howto/best_practices.py
├── howto/patterns.py
├── howto/faq.md

Migration: migration.md
Configuration: config.md
API Reference: reference/
Changelog: changelog.md
```

## Step-by-step execution order

### Step 1: Environment & baseline
- Install `.[dev,docs,ci]` into uv env
- Run `just docs` to confirm current build works
- Commit current state if needed

### Step 2: Scaffold directories + mkdocs.yml
- Create all new directories under `docs/source/`
- Update `mkdocs.yml` with new nav
- Put minimal placeholder `.py`/`.md` files so the build doesn't break
- Verify `just docs` still builds

### Step 3: Core Concepts (highest impact)
- [x] `concepts/kcell.py` — KCell/DKCell/VKCell, decorators, caching, shapes, plot
  - Fixed `dwidth` → `width=kf.kcl.to_dbu(...)` and positional `add_port` → `add_port(port=...)`
- [x] `concepts/layers.py` — LayerInfos, LayerEnum, LayerStack, LayerLevel, layerenum_from_dict
  - `LayerLevel` and `layerenum_from_dict` must be imported from `kfactory.layer` (not in top-level `kf`)
- [x] `concepts/ports.py` — Port/DPort construction, Ports filtering, connect, add_ports, auto_rename_ports
- [x] `concepts/instances.py` — absorb 01_references.py instance content, expand
- [x] `concepts/geometry.py` — absorb 00_geometry.py, expand with Region/boolean ops
- [x] `concepts/kclayout.py` — absorb 04_KCL.py, expand with dbu explanation, factories, GDS read/write
- [x] `concepts/dbu_vs_um.py` — coordinate systems
- Verify build after each file or batch

### Step 4: Routing (biggest gap)
- [x] `routing/overview.py` — routing sub-modules, route_bundle (optical + electrical),
  place_manhattan, route_loopback, obstacle avoidance
  - `bend_euler_factory` takes width/radius in **µm** (not DBU)
  - `straight_dbu_factory` takes width/length in **DBU**
  - Ports must use the **same `KCLayout`** as the factories/cells (use `kf.kcl` + `kf.kcl.infos = L`)
  - Use `kf.routing.optical.get_radius(bend90)` for loopback `bend90_radius` (euler bend footprint > nominal radius)
  - `kf.routing.electrical.route_bundle` uses `place_layer=` + `route_width=` (no `straight_factory`)
- [x] `routing/optical.py` — waypoints, starts/ends stubs, path_length_matching_config, inside loopback, direct place_manhattan
  - Routes need ≥ 150 µm horizontal spacing for path_length_match loops to fit without collision
  - `path_length_matching_config` requires routes to have bends (not pure straight lines) for loop insertion to work
  - Waypoints use `kdb.Trans(angle, flip, x, y)` for single-point corridors; `list[kdb.Point]` for multi-point corridors
  - Collision check enabled by default; test geometry carefully before publishing
- [x] `routing/electrical.py` — route_bundle, dual_rails
  - `width_rails` is the **total** outer width of the hollow path; `separation_rails` is the inner gap (must be < `width_rails`)
  - Pass `on_collision=None` to suppress KLayout show_error in headless doc builds when collision detection is not needed
- [x] `routing/manhattan.py` — backbone calculation (`route_manhattan`, `route_manhattan_180`), `place_manhattan`, Steps API (Straight/Left/Right), ManhattanRoute info
  - Use `kf.routing.optical.get_radius(bend_cell)` — euler footprint is larger than nominal radius; passing nominal causes "distance too small" error in `place_manhattan`
  - `route_smart` expects `BasePort` (pydantic model), NOT `kf.Port`; use `route_manhattan` + `place_manhattan` directly for low-level control
  - `Straight(dist=...)` raises `ValueError` if dist < `bend90_radius`
  - Verify build ✓ (docs build in 19 s)
- [x] `routing/all_angle.py` — single route, diagonal backbone, bundle routing, VKCell pattern
  - `route()` and `route_bundle()` live in `kf.routing.aa.optical`
  - Uses **virtual factories**: `virtual_straight_factory` (µm) + `virtual_bend_euler_factory` (µm)
  - Bundle: `start_ports` anti-clockwise, `end_ports` clockwise; backbone ≥2 points
  - Backbone segments must be ≥ 2× effective bend radius to avoid "not enough space" error
  - Can route into real `KCell` or `VKCell`; `VInstance.insert_into(c)` materialises virtual route
  - Verify build ✓ (docs build in 20 s)
- [x] `routing/bundle.py` — sort_ports, separation, sbend_factory, bbox_routing modes, collision_check_layers, mismatch flags; parameter quick-reference table
  - `sbend_factory` works for same-pitch bundles; fan-out (different pitches) requires the standard bend routing without sbend_factory
  - `bbox_routing='full'` keeps the bundle grouped around obstacles; `'minimal'` allows individual routes to detour independently
  - Verify build ✓ (docs build in 20 s)
- [x] `routing/path_length.py` — baseline vs matched lengths, loop_side (left/center/right), loop_position (start/center/end), loops=2, element selection, route length inspection table
  - `path_length_matching_config` is a post-processing step; all routes need enough horizontal clearance (≥ 2× bend_radius) to fit the loops without overlap
  - Use `on_collision=None` for headless doc builds; pass `route.length / 1000` to get µm values
  - `route.length` is in µm (float); `route.length_straights`, `route.n_bend90` also available for diagnostics
  - Verify build ✓ (docs build in 20 s)
- Verify build ✓

### Step 5: Components & Factories
- [x] `components/overview.py` — visual gallery covering straight, euler bends, circular bends, tapers, bezier S-bends, factory pattern, caching demo, and component assembly example
  - `kf.cells.*` functions use `kf.cells.demo` KCLayout; PDK usage requires `*_factory(kcl=my_kcl)`
  - `@kf.cell` caching: same params → same object (`wg_a is wg_b` is True)
  - `bend_euler_factory` / `bend_circular_factory` take width/radius in **µm**
  - `straight_dbu_factory` takes width/length in **DBU** (convert with `kf.kcl.to_dbu(...)`)
  - `kf.routing.optical.get_radius(bend)` returns actual footprint radius (euler > nominal)
- [x] `components/straight.py` — straight waveguide deep-dive: µm API, DBU API, enclosure, caching, path assembly, factory pattern, width-must-be-even rule
  - `Port` has no `dtrans` attribute — use `.trans` (integer Trans) directly
  - `KCLayout("name", infos=LAYER)` takes the **class** not an instance (KCLayout calls `infos()` internally)
  - Verify build ✓ (docs build in 16 s)
- [x] `components/euler.py` — euler bends (90°/arbitrary angle), S-bend, cladding, caching, L-arm assembly, effective radius, factory pattern
  - `kf.routing.optical.get_radius(bend)` returns actual footprint radius (clothoid extends beyond nominal)
  - `bend_s_euler` ports are always parallel; negative `offset` flips direction
  - Verify build ✓ (docs build in 16 s)
- [x] `components/taper.py` — linear taper: µm API, DBU API, enclosure, caching, mode-adapter assembly, factory pattern
  - `taper_factory` takes width/length in **DBU**; use `my_kcl.to_dbu(...)` to convert µm
  - `apply_minkowski_y` expands the trapezoid in the Y direction — cladding follows the taper profile exactly
  - Verify build ✓ (docs build in 16 s)
- [x] `components/circular.py` — constant-radius arc bend: basic 90°, arbitrary angle, angle_step resolution, cladding, caching, L-arm assembly, routing radius (== nominal, unlike euler), factory pattern
  - `kf.cells.circular.bend_circular` / `kf.factories.circular.bend_circular_factory`
  - `angle_step` controls polygon resolution (default 1°); `get_radius` returns the nominal radius unchanged
  - Verify build ✓ (docs build in 21 s)
- [x] `components/pcells.py` — PCell concept, `@kf.cell` (DBU + µm via output_type), `@kf.vcell`, `@pdk.cell`, caching, auto-naming, settings, composing PCells, decorator options table
  - `@kf.cell(output_type=kf.DKCell)` wraps the returned KCell in DKCell automatically
  - Arguments must be hashable (int, float, str, LayerInfo, frozen containers)
  - Pass `kcl=pdk` to `kf.Port(...)` when building inside a PDK KCLayout to avoid layer index mismatch
  - Verify build ✓ (docs build in 18 s)
- [x] `components/bezier.py` — cubic Bezier S-bend: basic usage, height/length variation, negative height, nb_points resolution, t_start/t_stop partial curves, cladding, caching, fan-out assembly, factory pattern
  - `inst.dmove((x, y))` takes a tuple, NOT `kdb.DVector` (causes TypeError with DCplxTrans unpacking)
  - Verify build ✓ (docs build in 18 s)
- [x] `components/virtual.py` — VKCell concept, direct shape insertion, ports, nesting VKCells, `@pdk.vcell` decorator, `virtual_straight_factory` / `virtual_bend_euler_factory`, all-angle routing into VKCell, `insert_into` vs `insert_into_flat`
  - `kcl.vkcell(name=...)` creates the cell; shapes go in via `vc.shapes(layer_idx).insert(kdb.DBox(...))`
  - Ports use `create_port(dcplx_trans=kdb.DCplxTrans(...))` with µm coords
  - Virtual factories returned by `virtual_straight_factory(kcl)` / `virtual_bend_euler_factory(kcl)` accept µm params; bind defaults with `functools.partial`
  - `kf.VInstance(vc).insert_into(target)` materialises hierarchically; `insert_into_flat` inlines geometry with no sub-cells
  - Use a dedicated `KCLayout` for virtual demos to keep layer indices consistent
  - Verify build ✓ (docs build in 18 s)
- [x] `components/factories.py` — factory protocols, usage: straight_dbu_factory (DBU), bend_euler_factory / bend_s_euler_factory (µm), bend_circular_factory (µm), taper_factory (DBU); footprint radius; routing integration; PDK bundling pattern
  - `KCLayout` does NOT have `straight_factory`/`bend_factory` slots — store factories in module-level variables or a dataclass instead
  - Verify build ✓ (docs build in 18 s)

### Step 6: Cross-Sections & Enclosures
- [x] `enclosures/cross_sections.py` — DCrossSection/CrossSection/SymmetricalCrossSection; multi-layer sections; annular sections; bbox_layers; KCLayout registry (get_icross_section/get_dcross_section); port creation pattern; routing tips
  - `@kf.cell` caches by parameters — pass cross-section as a **name string** and look it up inside with `kcl.get_icross_section(name)`; passing a `CrossSection` object directly raises `TypeError: unhashable type`
  - `add_port` requires `port=` keyword argument (not positional)
- [x] `enclosures/layer_enclosure.py` — absorbs 03_Enclosures.py; covers LayerEnclosure (DBU + µm sections), multi-layer annular sections, KCellEnclosure.apply_minkowski_tiled, SymmetricalCrossSection
  - `dsections=` requires `kcl=` to be set for µm→DBU conversion
  - Three-element sections `(layer, d_min, d_max)` produce annular (ring) regions
  - `KCellEnclosure` merges sub-cell geometry before expansion — use it for multi-component cells to avoid gaps
- [x] `enclosures/kcell_enclosure.py` — multiple enclosures, tiling params (n_pts/tile_size/n_threads/carve_out_ports), apply_minkowski_y (horizontal waveguides), apply_minkowski_x (vertical waveguides), apply_minkowski_custom (diamond kernel), method comparison table
  - `apply_minkowski_y/x/custom` on `KCellEnclosure` take only `c: KCell` (no `ref` arg, unlike `LayerEnclosure` variants)
  - All `LayerEnclosure` objects must have `main_layer=` set for `KCellEnclosure` to find source geometry
  - Call apply methods **inside** `@kf.cell` function before `return c` (cell must be unlocked)
  - `n_pts` controls circle polygon resolution in `apply_minkowski_tiled`; lower = faster but angular corners
- Verify build ✓ (docs build in 20 s)

### Step 7: Utilities
- [x] `utilities/grid.py` — grid/flexgrid (µm) and grid_dbu/flexgrid_dbu; 1D, 2D with shape=, explicit list-of-lists, alignment options, InstanceGroup usage
  - `grid`/`flexgrid` take `DKCell` components (µm); `grid_dbu`/`flexgrid_dbu` take `KCell` components (DBU)
  - `None` slots in list-of-lists cause AttributeError in `grid` (µm) — only `flexgrid_dbu` handles None correctly; avoid None in µm variants
  - Verify build ✓ (docs build in 16 s)
- [x] `utilities/packing.py` — pack_kcells / pack_instances; basic pack, max_width constrained pack, pack_instances rearrange, InstanceGroup usage
  - `kf.packing.pack_kcells` / `kf.packing.pack_instances` (sub-module, not top-level `kf.*`)
  - `spacing` and `max_width`/`max_height` are in **dbu** (use `kf.kcl.to_dbu()` to convert)
- [x] `utilities/drc_fix.py` — absorbs 02_DRC.py; covers fix_spacing_tiled, fix_spacing_minkowski_tiled, workflow pattern, performance notes
  - Both fixers return a `kdb.Region` — they do NOT modify in-place; caller inserts result
  - `fix_spacing_minkowski_tiled` accepts `smooth=` in dbu (not um) for corner smoothing
  - `n_threads=None` uses `kf.config.n_threads` (logical CPU count); override for CI environments
- [x] `utilities/difftest.py` — xor/diff/difftest; in-memory xor, file-based diff, pytest integration pattern, ignore flags
  - `xor()` and `diff()` take **KCLayout** objects (not cells); use `kcl_a.layer(L.WG)` (instance method) not `kcl.find_layer(LAYER.WG)` (class attribute)
  - Layer instance `L = LAYER()` required for attribute access; `kf.kcl.infos = L` registers it with the global layout
  - `difftest()` raises `AssertionError` on first run (no ref) — not safe to call in executable notebook; show as code comment instead
  - Verify build ✓ (docs build in 17 s)
- [x] `utilities/fill.py` — fill_tiled: fill_layers, fill_regions, exclude_layers, exclude_regions, x_space/y_space, row_step/col_step, multiple exclusion layers
  - `fill_tiled` must be called **inside** the `@kf.cell` function (target cell must be unlocked)
  - `fill_tiled` returns `None` and modifies in-place; `each_inst()` returns cell-instance arrays, not individual fills
  - `row_step`/`col_step` are `kdb.DVector` in **µm**; `x_space`/`y_space` are µm gaps between bboxes
  - `@kf.cell(kcl=...)` is NOT valid syntax — use a separate `KCLayout` and plain `@kf.cell` with cells created explicitly via `kf.KCell(kcl=...)`
- Verify build ✓ (docs build in 19 s)
- [x] `utilities/session_cache.py` — `save_session` / `load_session`; first-run no-op; save creates `cells.gds.gz` + `factories.pkl` per layout; SHA-256 invalidation on factory source change; `c=` subset save; complete PDK usage pattern
  - Factory functions must live in a real `.py` file on disk (not ephemeral notebook/exec code) because `save_session` hashes their `__code__.co_filename` to detect changes
  - Demonstrate round-trip in a notebook by importing factories from a temp `.py` file via `importlib.util`; cannot clear and reload in the same kernel (cells already exist in the layout)
  - `load_session(warn_missing_dir=False)` is the safe call at startup — silently skips if no session exists
  - Verify build ✓ (docs build in 19 s)

### Step 8: PDK, Schematics, How-To
- [x] `pdk/creating_pdk.py` — layers + KCLayout + enclosures + cross-sections + factories + custom @cell + assembly + GDS export + module pattern
  - Pass `infos=LAYER` (the **class**) to `KCLayout.__init__` — setting `pdk.infos = L` after creation does NOT update `pdk.layers` fully
  - Always pass `kcl=pdk` when constructing `kf.Port` — without it the port uses `kf.kcl` (global layout) and layer indices mismatch
  - Use `kf.Port(trans=kf.kdb.Trans(...), kcl=pdk, layer=pdk.find_layer(L.WG), ...)` for DBU-integer port placement
  - `c.add_port(port=instance.ports["name"], name="new_name")` to rename when exposing child ports on a parent cell (not `port.copy("name")`)
  - Verify build ✓ (docs build in 16 s)
- [x] `pdk/technology.py` — LayerLevel, LayerStack, Info; per-layer queries; PDK attachment pattern; JSON serialisation
  - `Info` does NOT support `complex` refractive index (only int/float/str/list/dict/tuple/None)
  - Verify build ✓ (docs build in 16 s)
- [x] `schematics/overview.py` — new clean replacement for 05_Schematics.py; covers Schematic/DSchematic, schematic_cell decorator, create_inst, place, connect, netlist extraction, LVS check, code generation
  - Settings in `create_inst` must be JSON-serialisable (no `LayerInfo` objects; use int/float/str)
  - `routing_strategy` decorator does NOT exist on `KCLayout` (removed); use plain routing calls instead
  - `cell.netlist()` returns a dict keyed by cell name; each value is a `Netlist` with `.instances`, `.nets` (list of `Net`), and `.ports`
  - `schematic.netlist()` (on the model) derives connectivity from declared placements/connections; matches extracted netlist for LVS
  - Verify build ✓ (docs build in 16 s)
- [x] `schematics/netlist.py` — Netlist data model (instances/nets/ports), inspecting PortRef, sort() for stable comparison, JSON/YAML serialisation (exclude `unit` field), `read_schematic` round-trip, `lvs_equivalent` for electrically-equivalent ports (pads), programmatic Netlist construction with `create_inst`/`create_net`/`create_port`
  - `model_dump_json(exclude={"unit"})` required — `unit` is fixed by subclass `__init__` and must NOT appear in the payload passed to `read_schematic`/`model_validate`
  - Verify build ✓ (docs build in 19 s)
- [x] `howto/best_practices.py` — 13 pitfalls covering units, `add_port(port=)`, KCLayout `infos=` class arg, caching hashability, cross-section registry via `get_icross_section`, factory parameter units (DBU vs µm), effective euler radius, headless collision suppression, `kcl=pdk` in Port, enclosure `dsections=` needs `kcl=`, `fill_tiled` in-place pattern, packing DBU params, `dmove` tuple not DVector
  - `kf.kcl.add_cross_section()` does NOT exist — use `kf.kcl.get_icross_section(spec)` to register, then retrieve by name string
  - `@pdk.cell` required when factory body creates `KCell(kcl=pdk)`; using `@kf.cell` raises `ValueError: must use same KCLayout`
  - `straight_dbu_factory(kcl)` / `bend_euler_factory(kcl)` take only `kcl` + optional kwargs; `layer` and `enclosure` go to the *returned* function
  - `LayerEnclosure` attribute is `layer_sections` (not `enclosures`)
  - `apply_minkowski_y(c, ref)` only takes 2 args (c + optional ref layer); target layers come from the enclosure's `layer_sections`
  - Use a dedicated `KCLayout` for factory demos to avoid global `kf.kcl` state conflicts
  - Verify build ✓ (docs build in 18 s)
- [x] `howto/patterns.py` — 6 patterns: component composition, port propagation, factory bundle dataclass, cross-section lookup in cached cells, tile/array pattern, VKCell→KCell materialise
  - `virtual_straight_factory(kcl)` / `virtual_bend_euler_factory(kcl)` return bare callables; use `functools.partial` to bind `layer=`, `width=`, `radius=` before passing to `aa.route`
  - VKCell must be created via `pdk.vkcell()` (not bare `kf.VKCell()`) so layer indices match the PDK's registry
  - `grid_dbu(target, kcells, ...)` requires a `target` KCell as first positional arg (returns `InstanceGroup`, not a cell)
  - `LayerEnclosure` passed to `SymmetricalCrossSection` must have `main_layer=` set
  - `StraightFactory` (not `StraightFactoryDBU`) is the correct import from `kfactory.factories.straight`
  - Verify build ✓ (docs build in 19 s)
- [x] `howto/faq.md` — comprehensive FAQ covering units (DBU/µm), ports (`port=` keyword, renaming, angles), layers/KCLayout (`infos=` class arg, `kcl=pdk` in Port, LayerLevel import path), caching (hashable args, `@pdk.cell` vs `@kf.cell`), routing (effective vs nominal radius, path-length match spacing, collision suppression, `route_smart` BasePort, all-angle spacing), enclosures (`apply_minkowski_y`, `dsections=kcl`), utilities (`fill_tiled` in-place, packing DBU, `dmove` tuple), schematics (JSON-serialisable settings), difftest (first-run AssertionError). Verify build ✓ (docs build in 16 s)
- [x] `howto/contributing.md` — dev setup (just dev / uv), running tests (just test / just test-min / just dev-cov), building docs (just docs / docs-serve), code quality (lint/format/mypy/ty), contribution workflow, PR guidelines, project layout, dependency extras table, getting-help links. Verify build ✓ (docs build in 16 s)
- Verify build

### Step 9: Getting Started & polish
- [x] `getting_started/prerequisites.md` — Python, environments, KLayout, klive overview
- [x] `getting_started/installation.md` — pip/uv install, extras table, verify snippet, next-steps links
- [x] `getting_started/quickstart.py` — self-contained notebook: layers, @cell straight, euler bend factory, L-shaped arm assembly, port inspection
  - Use `kf.kcl.find_layer(info)` for shape/port layer index (not `L.WG` directly)
  - Use `kf.Port` + `add_port` with `DCplxTrans` (not `create_port` + `Trans`)
  - `bend_euler_factory` takes width/radius in µm, requires `layer=` kwarg
- [x] `getting_started/klive_setup.md` — klive install video, how it works, tip about file-reload dialog
- [x] mkdocs.yml: added `Getting Started` nav section (legacy `First Steps` section kept until Step 10 cleanup)
- Verify build ✓ (docs build in 14 s)
- [x] gdsfactory.md: updated cross-sections section (was incorrectly claiming kfactory has no cross-sections), added routing comparison table, fixed broken link to deleted notebooks
- [x] Expanded `index.md` — replaced `--8<-- "README.md"` with a proper kfactory 3.0 landing page: brief intro, 9 quick-nav grid cards (Getting Started, Core Concepts, Routing, Components, Enclosures, Utilities, PDK, Schematics, How-To), key-features bullet list, link to gdsfactory comparison
- [x] `config.md` — added env var quick-reference table at top (23 rows, all `KFACTORY_*` vars with type/default/description), dotenv tip admonition
- [x] `migration.md` — added "3.0 Change Summary" table at top (7 rows covering module move, removed functions, deprecated params, schematics routing)
- Verify build ✓ (docs build in 14.75 s)

### Step 10: Cleanup
- [x] Deleted `docs/source/notebooks/` (all content migrated to new sections)
- [x] Deleted orphaned files: dosdonts.md, pre.md, intro.md, pcells.md
- [x] Deleted root helper .py files: complex_cell.py, layers.py, star.py, straight.py (only referenced from intro.md which was deleted)
- [x] Updated mkdocs.yml: removed "First Steps (legacy)" and "Tutorials" sections; removed dosdonts.md from Home nav
- [x] Final full build verified ✓ (docs build in 13 s)

### Step 11: Cross-linking (See Also sections)
- [x] Added "See Also" tables to all 7 Core Concepts pages:
  - `concepts/kcell.py` → Ports, Instances, DBU vs µm, PCells, Virtual Cells
  - `concepts/layers.py` → KCLayout, Cross-Sections, Technology, Creating a PDK
  - `concepts/ports.py` → Instances, Cross-Sections, Routing Overview, Components
  - `concepts/instances.py` → Ports, Routing Overview, Components, Grid Layout
  - `concepts/geometry.py` → DRC Fixing, Layer Enclosure, Fill, Difftest
  - `concepts/kclayout.py` → Creating a PDK, Session Cache, Difftest, Layers
  - `concepts/dbu_vs_um.py` → KCell, Ports, Factory Functions, FAQ
- Verify build ✓ (docs build in 28 s, python 3.13)

### Step 12: Cross-linking — Routing section
- [x] Added "See Also" tables to all 7 Routing pages:
  - `routing/overview.py` → Optical, Electrical, Manhattan, All-Angle, Bundle, Path Length, Euler Bends, DBU vs µm
  - `routing/optical.py` → Overview, Bundle, Path Length, Manhattan, All-Angle, Euler Bends, Ports
  - `routing/electrical.py` → Overview, Bundle, Optical, Layers, Cross-Sections, Ports
  - `routing/manhattan.py` → Optical, Bundle, Euler Bends, Ports, DBU vs µm
  - `routing/all_angle.py` → Optical, Virtual Cells, Euler Bends, Overview, Ports
  - `routing/bundle.py` → Optical, Electrical, Path Length, Manhattan, Overview, Ports
  - `routing/path_length.py` → Bundle, Optical, Overview, Euler Bends, DBU vs µm
- Verify build ✓ (docs build in 29 s, python 3.14)

### Step 13: Cross-linking — All remaining sections
- [x] Added "See Also" tables to all 9 Components pages:
  - `components/overview.py` → Straight, Euler, Circular, Taper, Bezier, Virtual, PCells, Factories, KCell
  - `components/straight.py` → Taper, PCells, Cross-Sections, Layer Enclosure, Factories, Routing Overview
  - `components/euler.py` → Overview, Circular, PCells, Factories, Optical, All-Angle, Manhattan
  - `components/circular.py` → Overview, Euler, PCells, Factories, Optical
  - `components/taper.py` → Straight, Cross-Sections, Layer Enclosure, PCells, Factories
  - `components/pcells.py` → Factories, Virtual, KCell, DBU vs µm, Creating a PDK
  - `components/bezier.py` → Overview, Euler, Circular, Factories, All-Angle
  - `components/virtual.py` → PCells, Factories, All-Angle, KCell
  - `components/factories.py` → PCells, Straight, Euler, Circular, Taper, Bezier, Routing Overview, PDK
- [x] Added "See Also" tables to all 3 Enclosures pages:
  - `enclosures/cross_sections.py` → Layer Enclosure, KCell Enclosure, Straight, Taper, Routing Overview
  - `enclosures/layer_enclosure.py` → Cross-Sections, KCell Enclosure, Straight, Taper
  - `enclosures/kcell_enclosure.py` → Layer Enclosure, Cross-Sections, Geometry, Fill
- [x] Added "See Also" tables to all 6 Utilities pages:
  - `utilities/drc_fix.py` → Geometry, Fill, KCell Enclosure, Difftest
  - `utilities/fill.py` → DRC Fix, Geometry, KCell Enclosure, Grid
  - `utilities/grid.py` → Packing, Components Overview, Creating a PDK, Instances
  - `utilities/packing.py` → Grid, Components Overview, Instances, Creating a PDK
  - `utilities/difftest.py` → Session Cache, Creating a PDK, Geometry, FAQ
  - `utilities/session_cache.py` → Difftest, Creating a PDK, KCLayout
- [x] Added "See Also" tables to both PDK pages:
  - `pdk/creating_pdk.py` → Technology, Cross-Sections, Layer Enclosure, PCells, Factories, Session Cache
  - `pdk/technology.py` → Creating a PDK, Layers, Cross-Sections, KCLayout
- [x] Added "See Also" tables to both Schematics pages:
  - `schematics/overview.py` → Netlist, Creating a PDK, PCells
  - `schematics/netlist.py` → Schematic Overview, Creating a PDK
- [x] Added "See Also" tables to How-To pages:
  - `howto/best_practices.py` → Patterns, FAQ, DBU vs µm, Creating a PDK
  - `howto/patterns.py` → Best Practices, FAQ, PCells, Routing Overview
  - `howto/faq.md` → Best Practices, Patterns, Contributing, DBU vs µm
  - `howto/contributing.md` → FAQ, Installation, Best Practices
- [x] Added "See Also" tables to Getting Started pages:
  - `getting_started/prerequisites.md` → Installation, KLive Setup, Quickstart
  - `getting_started/klive_setup.md` → Prerequisites, Installation, Quickstart
  - (installation.md and quickstart.py already had "Next steps" navigation)
- Verify build ✓ (docs build in 63 s)

### Status: COMPLETE (2026-04-04)
Steps 1–13 done. Docs build ✓ (63 s, python 3.14) with no errors.
All pages have "See Also" / "Next steps" cross-linking.

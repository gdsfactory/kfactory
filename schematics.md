# Schematic Annotation Deep Dive

This document summarizes how `@gf.cell(..., schematic_function=...)` is used in
the local `intel`, `cspdk`, `ihp`, `gdsfactory`, `gfp`, and `kfactory`
workspaces, and proposes a future direction for kfactory. It is written to help
a future implementer improve metadata annotations in kfactory first, then
migrate downstream consumers and PDKs.

The future direction in this document assumes a breaking cleanup is acceptable.
It therefore favors a coherent target API over preserving metadata-only
`schematic_function` behavior.

The short version: today one hook is doing two different jobs.

1. A real kfactory schematic can be the source of a generated layout
   (`@kcl.schematic_cell`).
2. A lightweight symbol/model annotation can be attached to an ordinary layout
   factory (`@gf.cell(..., schematic_function=...)`).

The PDKs mostly use the second pattern. They build tiny `DSchematic` objects
whose important data lives in free-form `s.info` keys. `gfp` then consumes those
keys as component-library metadata for Mosaic and simulation. That works, but
the API shape hides the actual contract and forces each PDK and consumer to
create its own schema, tests, adapters, and private wrapper introspection.

## Current Implementation

### kfactory objects

`kfactory.schematic.TSchematic` is a full Pydantic schematic model. Its real
fields include:

- `name`
- `instances`
- `placements`
- `nets`
- `routes`
- `ports`
- `pins`
- `constraints`
- `info`
- `unit`
- `kcl`

`Schematic` fixes `unit="dbu"`. `DSchematic` fixes `unit="um"`.

This model can create layout through `TSchematic.create_cell(...)`, produce a
netlist through `TSchematic.netlist(...)`, and round-trip through YAML/code
generation. That full schematic machinery is not what most current PDK
annotations are using.

### `@cell(..., schematic_function=...)`

In kfactory, `KCLayout.cell(..., schematic_function=f)` stores `f` on the
`WrappedKCellFunc` instance as `_f_schematic`. The public-ish methods are:

- `factory.schematic_driven() -> bool`
- `factory.get_schematic(*args, **kwargs) -> TSchematic`

The original layout factory remains the source of geometry. Calling the cell
factory does not use the schematic to build layout, and does not attach the
annotation result to the created cell as `cell.schematic`. The gdsfactory test
suite documents this explicitly with a commented-out assertion in
`gdsfactory/tests/test_cell.py`.

Consequences:

- `get_schematic(...)` can run without creating a layout cell.
- The annotation function must accept the same relevant arguments as the cell
  function, but kfactory does not enforce that relationship.
- The returned object is typed as a full `TSchematic`, even when the caller only
  needs a symbol, port list, and model metadata.
- `schematic_driven()` returns `True` for both full schematic-driven layout cells
  and metadata-only symbol annotations.

### `@schematic_cell`

`KCLayout.schematic_cell` is a separate path. It wraps a function that returns a
`TSchematic`, registers it through `@cell(..., schematic_function=f)`, then calls
`schematic.create_cell(...)` inside the generated cell function.

This is the true schematic-as-source mode:

- the schematic builds the cell geometry,
- the resulting cell gets `c.schematic = schematic`,
- schematic placement, routes, constraints, pins, and netlist behavior matter.

This is not how the reviewed PDK annotations are generally being used.

### gdsfactory wrapper

`gdsfactory._cell.cell` forwards `schematic_function` directly to
`kfactory.cell`. `gf.cell_with_module_name` does the same with module-derived
basenames. `gdsfactory.__init__` also aliases `kfactory.DSchematic` as
`gf.Schematic`, so gdsfactory component schematic functions are usually
returning kfactory `DSchematic` objects.

## Current Annotation Convention

The PDK annotations follow a de facto schema inside `DSchematic.info`:

```python
s = DSchematic()
s.info["symbol"] = "mmi-1x2"
s.info["tags"] = ["mmi"]
s.info["ports"] = [
    {"name": "o1", "side": "left", "type": "photonic"},
    {"name": "o2", "side": "right", "type": "photonic"},
    {"name": "o3", "side": "right", "type": "photonic"},
]
s.info["models"] = [...]
s.create_port(name="o1", cross_section="strip", x=-1, y=0, orientation=180)
```

The important fields are not Pydantic fields on `DSchematic`. They are plain
entries in the free-form `info` dict.

### `info["symbol"]`

`symbol` is a schematic/editor glyph identifier. The local repos use values such
as:

- photonic: `straight`, `bend`, `sbend`, `taper`, `transition`,
  `grating-coupler`, `coupler`, `coupler-ring`, `mmi-1x2`, `mmi-2x2`,
  `ring-single`, `ring-double`, `spiral`, `crossing`, `terminator`
- electrical/compact device: `nmos`, `pmos`, `npn`, `pnp`, `resistor`,
  `capacitor`, `diode`, `varicap`, `tap`, `pad`
- generic/fallback: `ckt`
- Intel-specific approximation: `amp` for SOA cells

Intel validates symbol names against a hard-coded Mosaic-supported device type
set in `intel/tests/test_schematics.py`. kfactory itself does not know this
vocabulary.

### `info["ports"]`

`ports` is a list of dicts with this shape:

```python
{"name": str, "side": "left" | "right" | "top" | "bottom", "type": str}
```

Observed `type` values:

- `photonic` in gdsfactory, cspdk, and Intel
- `electric` in all reviewed repos

This list is separate from `DSchematic.ports`. In current helpers, both are
created:

- `info["ports"]` carries editor-facing side/type metadata.
- `DSchematic.ports` carries actual kfactory `Port` objects with coordinates,
  orientation, and a cross-section name.

These two representations can diverge because they are maintained manually.

### Side and orientation convention

The shared convention maps schematic sides to outward port orientations:

| side | orientation |
| --- | ---: |
| `right` | `0` |
| `top` | `90` |
| `left` | `180` |
| `bottom` | `270` |

The common helper places symbol ports on a unit box:

| side | base point |
| --- | --- |
| `left` | `(-1, 0)` |
| `right` | `(1, 0)` |
| `top` | `(0, 1)` |
| `bottom` | `(0, -1)` |

When multiple ports are on the same side, the helpers use a `0.5` spacing and
center the group around the side midpoint. The list order controls where ports
land.

Intel and cspdk tests enforce a stricter ordering convention:

- left side: bottom to top, increasing `y`
- right side: top to bottom, decreasing `y`
- top side: left to right, increasing `x`
- bottom side: right to left, decreasing `x`

They call this "clockwise-from-left". The exact convention is external to
kfactory, but PDKs rely on it for the nyanlib/Mosaic bridge.

### `info["models"]`

`models` is a list of backend model links. kfactory does not interpret it.

SAX-style entries in cspdk/Intel have this shape:

```python
{
    "language": "sax",
    "name": "mmi1x2",
    "module": "cspdk.si220.cband.models",
    "qualname": "mmi1x2",
    "port_order": ["o1", "o2", "o3"],
    "params": {"length_mmi": "length_mmi"},
}
```

IHP compact-device entries use NgSpice and VACASK/Spectre:

```python
{
    "language": "spice",
    "implementation": "NgSpice",
    "name": "sg13_lv_nmos",
    "spice_type": "SUBCKT",
    "library": "ihp/models/ngspice/models/cornerMOSlv.lib",
    "sections": ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"],
    "port_order": ["D", "G", "S", "B"],
    "params": {
        "w": "width * 1e-6",
        "l": "length * 1e-6",
        "ng": "nf",
        "m": "m",
    },
}
```

The `params` values are strings. Some are simple renames; others are expressions
over component parameters. There is no typed expression language or validation in
kfactory today.

## How gfp Consumes The Metadata

`gfp` is the clearest consumer of the current convention. Its pipeline treats
`schematic_function` output as component metadata, not as a full kfactory
schematic.

### Runtime extraction

`crates/gfp-server/src/worker/runtime/schematic.rs` activates the selected PDK,
iterates `kfactory.kcl.factories._all`, calls `factory.get_schematic()`, reads
`schematic.info`, JSON-serializes that dict, and stores it by fully-qualified
factory name.

Important details:

- It intentionally iterates private `_all` instead of the public short-name
  mapping because short names collide across PDK modules.
- It catches failures from `get_schematic()` and skips factories that do not
  provide schematic metadata.
- It only consumes `schematic.info`; `DSchematic.instances`, `placements`,
  `nets`, `routes`, and `DSchematic.ports` are ignored on this path.

So in gfp, the "schematic" is effectively a metadata envelope. Creating
`DSchematic` ports and fake unit-box geometry is not part of the consumed
contract, except indirectly through PDK-side tests.

### Runtime fallback from layout cells

`crates/gfp-server/src/worker/runtime/symbols.rs` provides a separate fallback
when explicit schematic metadata is missing or incomplete. It imports each
factory by fully-qualified name, instantiates `factory()` with defaults, and
extracts:

- physical ports from `cell.ports`,
- a generated SVG symbol from the main polygon layer when possible,
- default parameter values,
- JSON schemas for parameter annotations.

The runtime port fallback maps physical port orientation to side:

| orientation | side |
| ---: | --- |
| `0` | `right` |
| `90` | `top` |
| `180` | `left` |
| `270` | `bottom` |

It maps physical `port_type == "optical"` to annotation type `"photonic"` and
everything else to `"electric"`. It sorts fallback ports clockwise-from-left by
actual geometry:

- left side: bottom to top,
- top side: left to right,
- right side: top to bottom,
- bottom side: right to left.

This mirrors the Intel/cspdk convention, but is computed from the built cell
instead of provided by `info["ports"]`.

### Nyanlib generation

`crates/gfp-server/src/factory/mosaic/nyanlib/mod.rs` merges indexed Python
factory data, schematic info, and runtime fallback info into generated
`build/models.nyanlib` entries.

The important mapping is:

| nyanlib field | source |
| --- | --- |
| `name` | indexed factory short name |
| `type` | `schematic.info["symbol"]`, defaulting to `"ckt"` |
| `tags` | `@cell(tags=[...])`, not `schematic.info["tags"]` |
| `ports` | `schematic.info["ports"]`, else runtime ports from `cell.ports` |
| `models` | `schematic.info["models"]` |
| `props` | indexed factory parameters plus runtime defaults/schemas |
| `symbol` | runtime-generated SVG path, not `schematic.info["symbol"]` |

Two naming collisions matter:

- Legacy `info["symbol"]` is really a Mosaic device type or glyph kind. It
  becomes the nyanlib `type` field.
- Nyanlib `symbol` is a custom SVG path generated from layout geometry.

`models` entries are also normalized for Clojure by converting object keys from
snake case to kebab case, for example `spice_type` becomes `spice-type` and
`port_order` becomes `port-order`.

Before writing ports to nyanlib, gfp converts gdsfactory's
clockwise-from-left list into Mosaic render order by reversing the `left` and
`bottom` side groups. This is an adapter for the current PDK convention, not a
kfactory-level rule.

### Mosaic frontend contract

The generated nyanlib entries are loaded into Mosaic's model database. The
schema in `frontend/mosaic/src/main/nyancad/mosaic/common.cljc` expects:

```clojure
{:name   string
 :type   string?
 :tags   [string]?
 :ports  [{:name string :side "top|bottom|left|right" :type "electric|photonic"?}]?
 :models [{:language string ...}]?
 :props  [{:name string ...}]?
 :symbol string?}
```

Mosaic uses these fields as follows:

- `:type` selects the built-in schematic glyph and is validated against
  `device-types`; unknown values fall back to `"ckt"` on factory-card drop.
- `:ports` drives schematic pin placement, port labels, airwires, net
  attribution, and typed electric/photonic connection metadata.
- `:models` marks a component as having code-model metadata and is available to
  downstream simulation/netlisting paths.
- `:props` supplies editable model parameters and default values when a factory
  card is dropped onto the schematic canvas.
- `:symbol` is a custom SVG image path used by the generic circuit renderer.

One subtle mismatch remains: `port-locations` groups ports by side and then
sorts each side by `:name` before placing them. That means a carefully ordered
nyanlib port list can still be overridden by lexical port naming in the Mosaic
renderer. The current PDK convention, the nyanlib reorder bridge, and Mosaic's
name sort should be treated as three separate contracts until this is cleaned
up.

### Livewire and simulation consumers

`crates/gfp-server/src/worker/runtime/bbox.rs` also calls
`factory.get_schematic()` and reads `info["symbol"]` to assign a Mosaic-style
component `type` to Livewire instances. It again has to locate the correct
registered factory through private `kcl.factories._all` to avoid short-name
collisions.

`python/gfp-kfactory/gfp_kfactory/simulate_sax.py` uses schematic metadata for
SAX model resolution. It reaches into `gf.kcl.factories[component]._f_schematic()`,
reads `info["models"]`, selects the first `{"language": "sax", ...}` entry, and
imports the referenced Python model. This is another consumer of the metadata
schema, and it currently depends on private wrapper state.

### Implication

For the current gfp integration, the full `DSchematic` return type is incidental.
The stable thing gfp needs is a factory metadata record with:

- a device type / editor glyph kind,
- declared ports with side and electric/photonic kind,
- model links for SAX/SPICE/Spectre/etc.,
- tags,
- parameter defaults and schemas,
- optional custom display symbol assets.

That strongly suggests the first kfactory PR should focus on a better
first-class metadata annotation API, rather than changing full schematic-driven
layout behavior. If downstream compatibility is not a constraint, the cleanest
path is to stop treating metadata-only `schematic_function` uses as supported
new API and migrate those PDK annotations directly to the new metadata model.

## Repository Findings

Counts below are from local static inspection with `uv run python`. They include
test files when those files matched the searched pattern; the gdsfactory count,
for example, includes one direct test fixture.

### gdsfactory

Observed usage:

- 102 decorated functions with `schematic_function=...`
- 100 use `gf.cell_with_module_name`
- 2 use `gf.cell` directly, one of which is a test
- 76 files contain decorated functions
- 24 reusable symbol functions are built in `gdsfactory/components/_schematic.py`

The helper is minimal:

- `schematic(symbol, tags, ports)` returns a closure.
- The closure ignores `**kwargs`.
- `_make_schematic(...)` creates a `DSchematic`, sets `info["tags"]`,
  `info["symbol"]`, `info["ports"]`, and creates unit-box ports.
- There are no model links.

The built-in port cross-section names are hard-coded:

- `strip` for non-electric ports
- `metal1_routing` for electric ports

This is enough for a symbol editor, but it is not a general kfactory contract.

### cspdk

Observed usage:

- 128 decorated functions
- all use `gf.cell`
- 30 files contain decorated functions
- most repeated across multiple material/platform variants
- shared helpers live in `cspdk/_schematic.py` plus per-platform `_schematic.py`
  modules

Top repeated schematic functions include:

- `straight_schematic`
- `bend_s_schematic`
- `bend_euler_schematic`
- `taper_schematic`
- `coupler_schematic`
- `grating_coupler_rectangular_schematic`
- `mmi1x2_schematic`
- `mmi2x2_schematic`
- `mzi_schematic`
- `pad_schematic`

Symbol assignment counts from static factory calls:

- `grating-coupler`: 13
- `straight`: 12
- `taper`: 12
- `pad`: 10
- `wire-corner`: 10
- `coupler`: 10
- `bend`: 9
- `sbend`: 8
- `mmi-1x2`: 6
- `mmi-2x2`: 6
- `mzi`: 6
- `ckt`: 4
- smaller counts for `crossing`, `wire`, `wire-bend`, `wire-sbend`,
  `coupler-ring`, `ring-single`, `ring-double`, `spiral`

cspdk uses `info["models"]` for SAX links. Tests in
`cspdk/tests/_schematic_checks.py` validate:

- every schematic-driven cell has a non-empty symbol,
- declared schematic ports are a subset of physical component ports,
- declared port sides match physical GDS port orientations,
- 90-degree bends declare `o1` left and `o2` top,
- same-side ports follow the clockwise-from-left ordering convention,
- SAX model references import and their `port_order` covers the model SDict keys.

The tests need to unwrap `WrappedKCellFunc` from the closure returned by
`gf.cell` because global factory lookup can collide across multiple bands with
the same cell names. That is a current API smell: PDK tests have to depend on
kfactory's wrapper internals to inspect annotations reliably.

### Intel

Observed usage:

- 101 decorated functions
- all use `gf.cell`
- 6 files contain decorated functions
- 80 are in `intel/cells/static.py`
- shared helper lives in `intel/_schematic.py`

Symbol assignment counts:

- `ckt`: 41
- `transition`: 28
- `grating-coupler`: 5
- `coupler`: 4
- `mmi-1x2`: 4
- `mmi-2x2`: 4
- `resistor`: 4
- `terminator`: 4
- `straight`: 3
- `amp`: 2
- `bend`: 1
- `crossing`: 1

Intel is the clearest example of the annotation mechanism being constrained by
an external editor symbol vocabulary. `intel/_schematic_tracking.md` tracks:

- cells rendered as generic `ckt` because Mosaic lacks a better glyph,
- cells using a real symbol with caveats,
- cells skipped entirely,
- SAX links and cells not linked yet.

The helper docstring explicitly says the returned closure ignores call kwargs
and represents the default-argument cell. That is a practical choice for a
symbol library, but it means `factory.get_schematic(non_default=...)` can return
a symbol whose ports no longer match the specific layout call if a parameter
changes port names/types/count.

Intel tests mirror cspdk tests and additionally validate symbol membership
against the Mosaic device type set.

### IHP

Observed usage:

- 24 decorated functions
- all use `gf.cell`
- 8 files contain decorated functions
- schematic functions are written inline next to the device layout functions
- all annotated ports are electric
- 76 `s.create_port(...)` calls across the 24 schematic functions

Symbol counts:

- `nmos`: 5
- `pmos`: 4
- `resistor`: 3
- `npn`: 3
- `diode`: 2
- `tap`: 2
- `capacitor`: 2
- `pad`: 1
- `varicap`: 1
- `pnp`: 1

Every IHP schematic function observed sets:

- `info["symbol"]`
- `info["ports"]`
- `info["models"]`

Each model list has one NgSpice entry and one VACASK/Spectre entry. Tests in
`ihp/tests/test_vacask_models.py` validate representative schematic functions
for matching NgSpice/VACASK metadata, library paths, and model file existence.

IHP highlights requirements that a photonic-only future spec would miss:

- compact-device symbols,
- multi-backend model entries,
- SPICE/Spectre library sections,
- `SUBCKT` port order,
- parameter expressions with unit conversion.

## Problems With The Current API

### One name covers two meanings

`schematic_function` sounds like "this cell has a schematic". In practice it can
mean:

- "this function is the schematic source used to create layout", or
- "this ordinary layout cell has a symbol/model annotation".

Both result in `schematic_driven() == True`. That name is misleading for
metadata-only annotations.

### Important schema is hidden in `info`

The current PDK contract is effectively:

```python
TSchematic.info["symbol"]: str
TSchematic.info["ports"]: list[dict]
TSchematic.info["models"]: list[dict]
```

kfactory does not define or validate these keys. A typo in `side`, a missing
model field, a stale `port_order`, or a mismatch between `info["ports"]` and
`DSchematic.ports` is invisible unless each PDK adds its own tests.

In gfp, these free-form keys are not decorative. They become the generated
`models.nyanlib` contract used by Mosaic and simulation. That makes the lack of
a typed kfactory-side schema more expensive: downstream tools have to duplicate
the schema in Rust, Clojure, Python, and PDK tests.

### Port metadata is duplicated

For symbol annotations, each port exists twice:

- as an `info["ports"]` dict with `name`, `side`, `type`,
- as a real `DSchematic.ports[name]` object with `cross_section`, `x`, `y`,
  `orientation`.

The side and orientation carry the same information in two places. The port kind
and side are not first-class fields on `Port`.

### The cross-section requirement is incidental

`DSchematic.create_port(...)` requires a cross-section name. For symbol
annotations this is often a placeholder:

- gdsfactory uses `strip` / `metal1_routing`
- cspdk uses `strip` / `metal_routing`
- Intel uses `strip_sm_routing_with_trenches` / `metal2`
- IHP uses its own electrical `_XS`

These names are needed because the annotation is forced through `DSchematic`.
They are not necessarily part of the intended symbol/model annotation.

### Static annotations can diverge from parametric layouts

Many helper-generated schematic functions ignore kwargs. This is fine for a
default symbol library, but the API signature suggests the schematic corresponds
to the specific parameterized cell call.

Intel documents this caveat. It can matter when parameters affect:

- port count,
- port names,
- port types,
- whether optional ports are present,
- model parameter mapping,
- symbol choice.

### Model parameter mapping is untyped

Model `params` are strings. Current strings encode several distinct concepts:

- identity mapping: `"length": "length"`
- rename: `"l": "length"`
- expression/unit conversion: `"w": "width * 1e-6"`
- constant as string: `"m": "1"`

There is no schema for the expression language, no static validation against the
cell signature, and no shared evaluation policy.

### PDKs depend on private wrapper internals

cspdk and Intel tests extract the `WrappedKCellFunc` from the closure of the
function returned by `gf.cell`. They do this because registry lookup by name can
collide between PDK bands/platforms.

That means annotation introspection is possible, but not ergonomic or stable.

### Decorator `tags` and `info["tags"]` overlap

PDKs often pass `tags=[...]` to `@gf.cell` and also set `s.info["tags"]`. These
are related but not connected by kfactory. A future consumer has to know which
one is authoritative for which purpose.

gfp currently writes nyanlib `tags` from the decorator, not from
`schematic.info["tags"]`. That means two PDK annotations can appear consistent
locally but export different tags depending on which field a consumer reads.

### `symbol` is overloaded across layers

Current PDKs use `s.info["symbol"]` for an editor device type such as
`"mmi-1x2"` or `"nmos"`. gfp writes that value to nyanlib as `type`.

The nyanlib field named `symbol` means something else: a custom SVG asset path
generated from runtime layout geometry. A future kfactory API should avoid
carrying the old `symbol` name forward without qualification.

### Consumers have to execute schematic functions for metadata

gfp has to activate a PDK, iterate kfactory's private factory registry, and call
`get_schematic()` merely to discover metadata. That is heavier and more fragile
than reading a static annotation record from an indexed factory. It also means a
metadata extraction failure looks like a schematic failure, even when no real
schematic behavior is involved.

### `vcell` has no equivalent hook

Intel explicitly skips at least one all-angle `@gf.vcell` because vcell does not
accept `schematic_function`. If annotations are a general factory metadata
feature, they should not be limited to regular KCell factories.

## Current Spec, As Implemented By Convention

This section describes the current PDK-facing contract as it exists today, not
as it should be.

### Decorator

```python
@gf.cell(tags=[...], schematic_function=<callable>)
def cell_name(...):
    ...
```

The callable should:

- accept the cell parameters it cares about,
- return a `DSchematic` or `Schematic`,
- be callable independently of layout creation,
- usually create one schematic-level port per declared symbol port,
- put symbol/editor/model metadata in `s.info`.

### Required info keys for symbol annotations

For current PDK consumers, a symbol annotation should provide:

```python
s.info["symbol"] = str
s.info["ports"] = list[PortInfo]
```

where:

```python
PortInfo = {
    "name": str,
    "side": "left" | "right" | "top" | "bottom",
    "type": "photonic" | "electric" | str,
}
```

Optional but common:

```python
s.info["tags"] = list[str]
s.info["models"] = list[ModelInfo]
```

### Port consistency rules used by PDK tests

For every `PortInfo`:

- `name` should exist on the real component for default cell settings.
- `side` should match the physical port orientation:
  - `right` -> `0`
  - `top` -> `90`
  - `left` -> `180`
  - `bottom` -> `270`
- same-side ports should be listed clockwise-from-left, unless a documented
  exception applies.
- `DSchematic.ports[name].orientation` should agree with `PortInfo["side"]`.

### Model consistency rules used by PDK tests

For SAX entries:

- `module` should import,
- `qualname` should exist in that module,
- if a PDK model registry exists, `name` should resolve there,
- model SDict keys should be a subset of `port_order`,
- `port_order` should be a subset of component port names.

For SPICE/Spectre entries:

- paired backend entries should describe the same device,
- `library` paths should exist,
- `sections`, `port_order`, and `params` should be consistent across backends
  where applicable.

## Future Spec Proposal

The main change should be to split "layout schematic" from "cell metadata
annotation". The current `TSchematic` model is valuable for schematic-driven
layout. It should not also be the only carrier for symbol/model metadata.

For a first PR, the center of gravity should be metadata annotation. Avoid
redesigning schematic-driven layout. The practical goal is to make the current
`info["symbol"]`, `info["ports"]`, `info["models"]`, and tag behavior explicit,
typed, serializable, and introspectable.

The normalized data model should be `CellAnnotation`, but the ergonomic authoring
model should be provider-based. In particular, model metadata should be attachable
from a different module or package than the geometry factory.

### New first-class type: `CellAnnotation`

Introduce a typed model for factory annotations:

```python
class CellAnnotation(BaseModel):
    device_type: str | None = None
    ports: tuple[AnnotationPort, ...] = ()
    models: tuple[ModelSpec, ...] = ()
    tags: tuple[str, ...] = ()
    display: DisplaySpec | None = None
    metadata: dict[str, JSONSerializable] = {}
```

Names are negotiable. The important part is that this is not a `TSchematic`.
This should be the resolved form: the object consumers get after all annotations
and overlays have been composed.

Recommended current-to-new mapping for planning the breaking migration:

| current field | future field |
| --- | --- |
| `s.info["symbol"]` | `annotation.device_type` |
| `s.info["ports"]` | `annotation.ports` |
| `s.info["models"]` | `annotation.models` |
| `s.info["tags"]` / `@cell(tags=...)` | `annotation.tags`, with a documented merge rule |
| gfp nyanlib `symbol` | `annotation.display` or runtime display asset |

### Annotation patches and providers

The ergonomic API should not require all metadata to live on the original cell
decorator. Geometry, editor metadata, simulation models, and downstream PDK
overlays often have different owners. The better pattern is a layered annotation
registry:

```python
class CellAnnotationPatch(BaseModel):
    device_type: str | None = None
    ports: tuple[AnnotationPort, ...] | None = None
    models: ModelPatch | tuple[ModelSpec, ...] = ()
    tags: tuple[str, ...] = ()
    display: DisplaySpec | None = None
    metadata: dict[str, JSONSerializable] = {}
```

`tuple[ModelSpec, ...]` is shorthand for appending models. For overlays and
preference changes, multi-valued fields should support explicit patch
operations:

```python
class ModelPatch(BaseModel):
    append: tuple[ModelSpec, ...] = ()
    prepend: tuple[ModelSpec, ...] = ()
    replace: tuple[ModelSpec, ...] | None = None
    remove: tuple[ModelSelector, ...] = ()


class ModelSelector(BaseModel):
    language: str | None = None
    simulator: str | None = None
    implementation: str | None = None
    name: str | None = None
```

This makes additions explicit. For example, an overlay can prepend a preferred
SAX model without rewriting the base annotation:

```python
@mmi1x2.models
def preferred_mmi_model(...) -> CellAnnotationPatch:
    return CellAnnotationPatch(
        models=ModelPatch(
            prepend=(
                SaxModelSpec(
                    name="fast_mmi1x2",
                    simulator="sax",
                    module="my_pdk.models",
                    qualname="fast_mmi1x2",
                    port_order=("o1", "o2", "o3"),
                ),
            )
        )
    )
```

Each provider returns a patch, or a narrower value such as `tuple[ModelSpec, ...]`
that kfactory wraps into a patch. kfactory resolves all patches for a factory
and a specific parameter set into one `CellAnnotation`.

Cell-local metadata can still be concise:

```python
@gf.cell
def mmi1x2(...):
    ...


@mmi1x2.annotate
def mmi1x2_symbol(...) -> CellAnnotationPatch:
    return CellAnnotationPatch(
        device_type="mmi-1x2",
        ports=[
            AnnotationPort(name="o1", kind="optical", side="left"),
            AnnotationPort(name="o2", kind="optical", side="right"),
            AnnotationPort(name="o3", kind="optical", side="right"),
        ],
    )
```

Model metadata can live in a different module or package:

```python
@mmi1x2.models
def mmi1x2_sax_models(...) -> tuple[ModelSpec, ...]:
    return (
        SaxModelSpec(
            name="mmi1x2",
            module="cspdk.si220.cband.models",
            qualname="mmi1x2",
            port_order=("o1", "o2", "o3"),
            params={"length_mmi": "length_mmi"},
        ),
    )
```

For components that a PDK does not control, annotation should be attachable by
object reference or fully-qualified name:

```python
@kf.annotate_for(gf.components.mmi1x2)
def add_mmi_metadata(...) -> CellAnnotationPatch:
    return CellAnnotationPatch(device_type="mmi-1x2", ports=[...])


@kf.models_for("gdsfactory.components.mmi1x2")
def add_mmi_models(...) -> tuple[ModelSpec, ...]:
    return (...)
```

This is similar in spirit to defining a property setter outside the getter's
body: the cell remains the anchor, but metadata can be enriched by other owners.

Recommended provider classes:

- `annotation=` / `annotation_function=` on `@cell` for simple local metadata,
- `factory.annotate(...)` for local or adjacent metadata patches,
- `factory.models(...)` for model-only providers,
- `kcl.annotations.annotate_for(...)` for overlays keyed by object or qualified
  name,
- `kcl.annotations.models_for(...)` for model overlays keyed the same way.

Conceptually:

```python
AnnotationProvider = Callable[..., CellAnnotationPatch | tuple[ModelSpec, ...]]
```

Provider functions should accept the same relevant parameters as the cell
factory and should be callable without building layout. This covers parametric
ports and model parameter mappings without reintroducing schematic-shaped
metadata.

Merge rules need to be explicit:

- `device_type`: one value; conflicting values are an error unless a provider is
  explicitly marked as replacing an earlier value.
- `ports`: usually replace as a group, because port count can be parametric; an
  optional merge-by-name policy can exist for overlays.
- `models`: apply `replace`, then `remove`, then `prepend`, then `append`;
  de-duplicate by a stable key such as
  `(language, simulator, implementation, name)`.
- `tags`: set union, preserving deterministic order.
- `display`: one value; conflicts are errors unless replacement is explicit.
- `metadata`: shallow namespaced merge; un-namespaced key conflicts are errors.

The resolved public API remains simple:

```python
factory.get_annotation(**settings) -> CellAnnotation
```

### Device type and display spec

`device_type` should name the semantic/editor glyph kind. Examples from current
PDKs include `mmi-1x2`, `straight`, `grating-coupler`, `nmos`, `resistor`,
`amp`, and `ckt`.

Do not bake Mosaic's current device type list into kfactory core. kfactory
should define a generic string identifier and allow downstream consumers to
register or validate device-type libraries. A Mosaic-specific validator can
live outside core or as an optional registry.

If a future API also wants to carry explicit display assets, keep that separate
from `device_type`:

```python
class DisplaySpec(BaseModel):
    kind: Literal["builtin", "svg", "image"] | str = "builtin"
    name: str | None = None
    path: str | None = None
    library: str | None = None
    parameters: dict[str, JSONSerializable] = {}
```

This separation avoids the current gfp collision where `info["symbol"]`
means nyanlib `type`, while nyanlib `symbol` means an SVG path.

### Port annotation

```python
class AnnotationPort(BaseModel):
    name: str
    kind: Literal["optical", "electrical", "photonic"] | str
    side: Literal["left", "right", "top", "bottom"] | None = None
    orientation: Literal[0, 90, 180, 270] | None = None
    order: int | None = None
    cross_section: str | None = None
    role: str | None = None
    aliases: tuple[str, ...] = ()
```

Recommended semantics:

- `name` binds to a real layout port unless explicitly marked virtual.
- `kind` replaces today's `type`.
- `side` is symbol/editor placement.
- `orientation` can be derived from `side` by default.
- `cross_section` is optional and only needed if a symbolic schematic cell must
  be materialized as geometry.
- `order` can replace list-order-as-coordinate or name-sort semantics for
  consumers that need deterministic side ordering.

This avoids forcing metadata-only annotations to create fake `DSchematic` ports.
It also lets an exporter document exactly how it maps kfactory order to an
editor's rendering order instead of relying on implicit list order.

### Model spec

Use a discriminated union:

```python
class SaxModelSpec(BaseModel):
    language: Literal["sax"] = "sax"
    simulator: str | None = "sax"
    implementation: str | None = None
    name: str
    module: str
    qualname: str
    port_order: tuple[str, ...]
    params: dict[str, ParamExpr] = {}

class SpiceModelSpec(BaseModel):
    language: Literal["spice", "spectre"]
    simulator: str | None = None
    implementation: str | None = None
    name: str
    spice_type: Literal["SUBCKT", "MODEL"] | str
    library: str
    sections: tuple[str, ...] = ()
    port_order: tuple[str, ...]
    params: dict[str, ParamExpr] = {}
```

Do not rely on list order alone to choose a simulator model. Different
simulators and backends should be declared explicitly:

```python
SaxModelSpec(
    simulator="sax",
    name="mmi1x2",
    module="cspdk.si220.cband.models",
    qualname="mmi1x2",
    port_order=("o1", "o2", "o3"),
)

SpiceModelSpec(
    simulator="ngspice",
    implementation="NgSpice",
    name="sg13_lv_nmos",
    spice_type="SUBCKT",
    library="ihp/models/ngspice/models/cornerMOSlv.lib",
    port_order=("D", "G", "S", "B"),
)

SpiceModelSpec(
    simulator="spectre",
    implementation="VACASK",
    name="sg13_lv_nmos",
    spice_type="SUBCKT",
    library="ihp/models/vacask/...",
    port_order=("D", "G", "S", "B"),
)
```

Consumers should select by explicit criteria:

```python
annotation.models.select(simulator="sax")
annotation.models.select(simulator="ngspice")
annotation.models.select(simulator="spectre", implementation="VACASK")
```

Ordering still matters as a preference within one selector result, which is why
`prepend` is useful. It should not be the only way to distinguish simulator
families.

`ParamExpr` should not remain an arbitrary string forever. A pragmatic first
step would be:

```python
ParamExpr = str
```

with validation that referenced names exist in the cell signature. A better
second step would be a small safe expression AST:

```python
class ParamRef(BaseModel):
    param: str

class ParamScale(BaseModel):
    param: str
    factor: float

class ParamConst(BaseModel):
    value: JSONSerializable
```

That would cover the observed patterns without arbitrary expression evaluation.

### Cell-local decorator API

Add decorator arguments independent of schematic-driven layout for the common
case where the cell owner also owns the metadata:

```python
@kcl.cell(annotation=CellAnnotation(...))
def straight(...): ...
```

and/or:

```python
@kcl.cell(annotation_function=straight_annotation)
def straight(...): ...
```

For gdsfactory:

```python
@gf.cell(annotation=...)
@gf.cell(annotation_function=...)
```

The function form is needed for parameter-dependent ports or models. The value
form is better for static symbols and avoids hundreds of tiny closures. Both are
just provider sources that participate in the same annotation resolution as
`factory.annotate`, `factory.models`, and external overlays.

Reserve `schematic_function` for actual schematic-returning functions. Do not
support metadata-only annotations through `schematic_function` in the new API.
If a factory wants symbol/model/editor metadata, it should use `annotation=` or
`annotation_function=`, or register an annotation/model provider elsewhere.

Avoid adding independent top-level decorator kwargs such as `symbol=...`,
`ports=...`, and `models=...` as separate long-term APIs. gfp already indexes
some of those names, but the more maintainable shape is one typed annotation
object with one validation and serialization path.

### Public factory API

Factories should expose annotations without closure unwrapping:

```python
factory.has_annotation() -> bool
factory.get_annotation(*args, **kwargs) -> CellAnnotation
factory.annotation_providers() -> tuple[AnnotationProvider, ...]
factory.has_layout_schematic() -> bool
factory.get_schematic(*args, **kwargs) -> TSchematic
```

Breaking semantics:

- `schematic_driven()` should mean layout-schematic-driven only, or be replaced
  by `has_layout_schematic()`.
- `get_schematic()` should return a real `TSchematic` used as schematic data,
  not a metadata envelope.
- `get_annotation()` should resolve first-class annotation providers. It should
  not call old `schematic_function` hooks as a fallback.
- Metadata-only functions returning `DSchematic(info=...)` should be migrated,
  not adapted.

### Validation helpers in kfactory

kfactory should provide reusable validators so each PDK does not carry its own
private test framework:

```python
validate_annotation(
    factory,
    *,
    build_cell: Callable[..., ProtoTKCell] | None = None,
    settings: dict[str, Any] | None = None,
    symbol_registry: SymbolRegistry | None = None,
    check_ports: bool = True,
    check_port_sides: bool = True,
    check_side_order: bool = True,
    check_models: bool = True,
)
```

Core checks:

- every provider result validates,
- provider merge resolves to a valid `CellAnnotation`,
- provider conflicts are either errors or explicitly marked replacements,
- declared port names exist on the built cell, unless marked virtual,
- side and orientation are consistent,
- side and physical port orientation agree within a tolerance,
- same-side order is deterministic,
- model `port_order` only references declared or real ports,
- model `params` reference real cell parameters,
- model selectors identify zero, one, or many models according to documented
  consumer policy,
- backend library/module references are syntactically valid; optional existence
  checks can be PDK-controlled.

This should work for both `cell` and `vcell`.

### Registry and introspection

PDKs need a stable way to iterate annotated factories without relying on global
name lookup or wrapper closures. Possible API:

```python
kcl.factories.annotated()
pdk.cells.annotated()
kcl.annotations.providers_for(factory_or_fqn)
factory.annotation_function
factory.annotation
factory.annotation_providers()
factory.qualified_name
```

The important requirement is that band/platform-specific cell registries can
return their own wrapped factory even when global kfactory names collide. The
annotation registry also needs deterministic provider ordering so an overlay can
be inspected, validated, and debugged without guessing which package won a
merge.

For gfp specifically, this should replace:

- iterating `kfactory.kcl.factories._all`,
- indexing `gf.kcl.factories[component]._f_schematic()`,
- matching short names and source files to recover a fully-qualified factory.

### Serialization

`CellAnnotation` should serialize to JSON/YAML independently of `TSchematic`.
That gives downstream tools a stable contract after provider resolution:

```yaml
device_type: mmi-1x2
ports:
  - name: o1
    kind: optical
    side: left
  - name: o2
    kind: optical
    side: right
models:
  - language: sax
    name: mmi1x2
    module: cspdk.si220.cband.models
    qualname: mmi1x2
    port_order: [o1, o2, o3]
```

Full schematic YAML remains the format for `TSchematic`.

### gfp / nyanlib export contract

kfactory does not need to know Mosaic internals, but the new annotation model
should make gfp's export straightforward and stable:

```python
annotation.to_dict()
annotation.to_nyanlib_model_def(adapter="mosaic")  # optional downstream helper
```

At minimum, kfactory should provide a typed JSON representation that gfp can map
without calling `get_schematic()` or unpacking `DSchematic.info`. With a breaking
migration, `DSchematic.info` should no longer be part of the gfp metadata path.
The gfp-side mapping would become:

| `CellAnnotation` field | nyanlib field |
| --- | --- |
| `device_type` | `type` |
| `tags` | `tags` |
| `ports` | `ports` |
| `models` | `models` |
| factory signature/default metadata | `props` |
| runtime/generated display asset | `symbol` |

The exporter should make ordering rules explicit. If kfactory emits
`AnnotationPort.order`, gfp can convert from kfactory/editor-neutral ordering to
Mosaic ordering in one documented adapter and Mosaic should not need to recover
intent by sorting names.

### Relationship to existing `ports=` decorator argument

kfactory already has `ports: PortsDefinition` on `@cell`, with:

```python
{"right": [...], "top": [...], "left": [...], "bottom": [...]}
```

That validates a subset of the annotation problem. A future implementation could
reuse it internally, but it is not enough by itself because it lacks:

- port kind,
- device-type/display metadata,
- model metadata,
- parametric annotation functions,
- backend/export metadata,
- exceptions and virtual/model-only ports.

## Breaking Implementation Plan

### Phase 1: Add typed annotation models

Add `CellAnnotation`, `CellAnnotationPatch`, `AnnotationPort`, and `ModelSpec`
types to kfactory. Define validation and serialization on these models from the
start.

```python
annotation.model_validate(...)
annotation.model_dump(...)
```

Do not add `annotation_from_schematic_info(...)` or
`annotation_to_legacy_schematic(...)` as first-class API. Those helpers would
make it too easy for the old `DSchematic.info` convention to survive.

### Phase 2: Add provider registry and factory support

Add `annotation=` and `annotation_function=` to `KCLayout.cell`, `KCLayout.vcell`,
and gdsfactory wrappers. Store them on wrapped factory objects and expose public
getter methods.

Also add provider registration APIs:

```python
factory.annotate(...)
factory.models(...)
kcl.annotations.annotate_for(...)
kcl.annotations.models_for(...)
```

These providers should be keyed by the wrapped factory object and by stable
fully-qualified name, so annotations can be attached both locally and from
external packages.

Change the meaning of factory introspection so metadata and schematic layout are
separate:

- `get_annotation()` returns `CellAnnotation`.
- `has_annotation()` reports first-class metadata annotations.
- `annotation_providers()` exposes the ordered providers used for resolution.
- `get_schematic()` remains for real schematics only.
- `schematic_driven()` is removed, renamed, or redefined so it no longer returns
  true for metadata-only annotations.

Also expose a stable iterator over annotated factories keyed by fully-qualified
name, so downstream indexers can stop relying on private registry storage.

### Phase 3: Add shared validators

Move the common Intel/cspdk validation logic into kfactory or a small companion
module:

- provider result shape,
- provider merge conflicts,
- model patch operations and selector behavior,
- device type present / optional registry membership,
- declared ports subset,
- side-orientation match,
- same-side ordering,
- model reference shape,
- model port-order consistency.

The PDK tests can then become small invocations of shared validators plus
PDK-specific exception lists.

### Phase 4: Migrate gdsfactory, cspdk, Intel, and IHP

Replace current `schematic(...) -> Callable[..., DSchematic]` helpers with
annotation providers:

```python
@straight.annotate
def straight_symbol(...) -> CellAnnotationPatch:
    return CellAnnotationPatch(
        device_type="straight",
        ports=[
            AnnotationPort(name="o1", kind="optical", side="left"),
            AnnotationPort(name="o2", kind="optical", side="right"),
        ],
    )
```

For IHP, keep per-device functions where parameter-dependent model metadata is
real, but return `CellAnnotationPatch` or model specs instead of a `DSchematic`.

Move model metadata into model providers when that is cleaner than placing it
next to geometry:

```python
@straight.models
def straight_models(...) -> tuple[ModelSpec, ...]:
    return (...)
```

For third-party components, use external overlays:

```python
@gf.kcl.annotations.annotate_for("gdsfactory.components.mmi1x2")
def annotate_builtin_mmi(...) -> CellAnnotationPatch:
    return CellAnnotationPatch(device_type="mmi-1x2", ports=[...])
```

During this phase, remove `schematic_function=...` from metadata-only cells
rather than keeping both declarations. A cell should have either real schematic
behavior or metadata annotation behavior, not both through the same old hook.

### Phase 5: Migrate gfp readers

Teach gfp to prefer `factory.get_annotation()` or serialized annotation data.
Remove the current `get_schematic().info` metadata path once PDK annotations are
moved to `CellAnnotation`.

After that migration, nyanlib generation should read:

- `annotation.device_type` for nyanlib `type`,
- `annotation.ports` for nyanlib `ports`,
- `annotation.models` for nyanlib `models`,
- `annotation.tags` or a documented factory-tag merge for nyanlib `tags`.

SAX model lookup should use the same annotation API instead of `_f_schematic()`.

### Phase 6: Remove metadata-only `schematic_function`

Remove support for metadata-only `schematic_function` usage from the target
stack. `schematic_function` can remain only for actual `TSchematic` behavior, if
that name is still useful. New metadata should fail validation if it is hidden
inside `DSchematic.info` instead of attached as a `CellAnnotation`.

## Design Principles For The PR

1. Keep full schematic-driven layout and symbol/model annotation separate.
2. Make the current `info["symbol"]`, `info["ports"]`, and `info["models"]`
   schema explicit and typed.
3. Prefer `device_type` or another explicit metadata name over carrying forward
   overloaded `symbol` terminology.
4. Do not hard-code one editor's symbol vocabulary in kfactory core.
5. Do not require fake schematic geometry or cross-sections for metadata-only
   annotations.
6. Support static annotation values as well as parameter-dependent annotation
   functions.
7. Allow metadata and models to be registered outside the original cell
   definition, including overlays for third-party components.
8. Provide public introspection so PDKs and gfp do not unwrap closures or touch
   `WrappedKCellFunc`, `_f_schematic`, or private factory registry internals.
9. Put common validation in kfactory so PDK tests can focus on PDK-specific
   exceptions.
10. Prefer a breaking but coherent API over preserving the current
   `DSchematic.info` convention.

## Open Questions

- Should the primary new term be `annotation`, `cell_metadata`,
  `component_metadata`, or something else? `annotation` is broad but accurate;
  `symbol` should probably be avoided as the primary term because it is already
  overloaded.
- Should current `info["symbol"]` map to `device_type`, `glyph_type`,
  `model_type`, or another name in the new API? `device_type` matches current
  Mosaic usage, but may sound too editor-specific for pure simulation metadata.
- Should port kind use `optical` or preserve current `photonic`? kfactory ports
  often use `optical`, while current annotations use `photonic`.
- Should `side` be required, or can consumers derive it from physical port
  orientation by default?
- Should port ordering be represented by list order, per-side `order`, or both?
  Mosaic currently sorts by name during placement, so an explicit future
  contract would help.
- Should model `params` initially stay as strings for implementation simplicity,
  or should kfactory introduce a safe expression representation immediately?
- Should `simulator` be a free string, an enum provided by downstream packages,
  or a structured target like `{engine, dialect, version}`?
- Should model selection return all matching models ordered by preference, or
  should common consumers require exactly one selected model?
- Should decorator tags and annotation tags be merged, or should one be
  authoritative?
- What is the provider precedence order across cell-local metadata, model
  providers, active-PDK overlays, and user/project overlays?
- Should external overlays bind primarily by object identity, qualified name, or
  both? Qualified names are serializable but can drift during refactors.
- Should `ports` be replace-only by default, or should an overlay be allowed to
  enrich individual ports by name?
- Should model patch operations exist only for `models`, or should similar
  `prepend`/`append`/`remove` operations also be available for tags and other
  repeated fields?
- Should a Mosaic/nyanlib exporter live in gfp only, or should kfactory provide
  a generic export adapter interface?
- Should `CellAnnotation` live in `kfactory.schematic`, a new
  `kfactory.annotation` module, or a more neutral metadata module?
- How should annotations attach to imported/static GDS cells with no Python cell
  function?
- Should layout cells created by `@cell(annotation_function=...)` store a copy of
  the resolved annotation on `cell.info`, `cell.annotation`, both, or neither?

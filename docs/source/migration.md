# Migration

## kfactory 3.0

### What's New in 3.0

#### New Features

- **Routing constraints & path-length matching** — the new `PathLengthMatch` constraint API enables length-matched bundle routing directly.
  See [Path-Length Matching](routing/path_length.md).
- **Asymmetrical cross-sections** — `AsymmetricCrossSection` allows non-symmetric waveguide profiles.
  See [Cross-Sections](components/cross_sections.md).
- **Netlist extraction as a separate package** — netlist generation now lives in [kfnetlist](https://github.com/gdsfactory/kfnetlist), a standalone package that is pulled in as a dependency.
  See [Netlist & I/O](schematics/netlist.md).
- **Factory metadata** — the new `FactoryMetadata` / `PortSpec` API captures structured metadata (including port specs) for factories.
- **Connectivity checks module** — connectivity checking now lives in its own `kfactory.checks` module.

#### Behavior Changes

- **`connect()` ignores port mirror flags by default** — `config.connect_use_mirror` now defaults to `False` (was `True` in 2.x). See [Default `connect()` mirror behavior](#default-connect-mirror-behavior).

#### Improved Features

- **Schematics** — tighter pin integration, virtual schematic connections, and the `@kcl.routing_strategy` registry for schematic-driven routing.
  See [Schematics Overview](schematics/overview.md).
- **Bundle routing** — expanded documentation and tutorial.
  See [Bundle Routing Tutorial](routing/bundle.md).

#### Infrastructure

- **Python 3.12+** is now required (up from 3.11).
- Complete **documentation overhaul** — new zensical-based build, restructured navigation, and auto-generated API reference.

---

### Migrating from 2.5.x or 2.6.x

The sections below cover breaking changes and how to update your code. All of them
apply when upgrading from either 2.5.x or 2.6.x. Changes that landed specifically in
the 2.6.x → 3.0 window (and so are new relative to a 2.6.x code base) are marked
**(new in 3.0)**.

#### Change Summary

| Area | What changed | Before (2.x) | After (3.0) |
|---|---|---|---|
| **Python** | Minimum version raised **(new in 3.0)** | Python 3.11 | Python 3.12 |
| **Module** | `virtual.utils` moved | `kfactory.factories.virtual.utils` | `kfactory.factories.utils` |
| **Routing** | `route_L` / `route_elec` removed | `route_elec(cell, p1, p2)` | `route_bundle(cell, [p1], [p2])` |
| **Routing** | `routing.optical.route` removed | `route(cell, p1, p2, ...)` | `route_bundle(cell, [p1], [p2], ...)` |
| **Routing** | `place90` removed | `place90(cell, p1, p2, pts)` | `place_manhattan(cell, p1, p2, pts)` |
| **Parameters** | `start_straights` removed | `start_straights=100` | `starts=100` |
| **Parameters** | `end_straights` removed | `end_straights=100` | `ends=100` |
| **Instances** | `connect()` ignores mirror by default **(new in 3.0)** | mirror flag applied | `use_mirror=True` / `config.connect_use_mirror=True` |
| **Netlist** | `kfactory.netlist` module removed **(new in 3.0)** | `from kfactory.netlist import Netlist` | `from kfnetlist import Netlist` (or `kf.Netlist`) |
| **Schematics** | `get_schematic` removed **(new in 3.0)** | `kf.get_schematic(...)` | use `Schematic` directly |
| **Schematics** | Routing via `KCLayout` registry | — | `@kcl.routing_strategy` + `schematic.add_route(...)` |

#### Module Reorganization

- `kfactory.factories.virtual.utils` has been moved to `kfactory.factories.utils` to unify it with other factory utilities.

```python
# Before (2.x)
from kfactory.factories.virtual.utils import extrude_backbone, extrude_backbone_dynamic

# After (3.0)
from kfactory.factories.utils import extrude_backbone, extrude_backbone_dynamic
```

#### Removed Routing Functions

The following routing functions have been removed. Use `route_bundle` instead.

- `routing.electrical.route_L` — removed
- `routing.electrical.route_elec` — removed
- `routing.optical.route` — removed

```python
# Before (2.x) — electrical
from kfactory.routing.electrical import route_L, route_elec
route_elec(cell, port1, port2, ...)

# After (3.0) — electrical
from kfactory.routing.electrical import route_bundle
route_bundle(cell, start_ports=[port1], end_ports=[port2], separation=..., ...)

# Before (2.x) — optical
from kfactory.routing.optical import route
route(cell, port1, port2, straight_factory=..., bend90_cell=..., ...)

# After (3.0) — optical
from kfactory.routing.optical import route_bundle
route_bundle(
    cell,
    start_ports=[port1],
    end_ports=[port2],
    separation=...,
    straight_factory=...,
    bend90_cell=...,
)
```

#### Removed Parameters in `route_bundle`

In both `routing.optical.route_bundle` and `routing.electrical.route_bundle`, the
parameters that were deprecated in 2.x have been removed:

- `start_straights` removed — use `starts` instead
- `end_straights` removed — use `ends` instead

```python
# Before (2.x)
route_bundle(cell, start_ports, end_ports, separation=..., start_straights=100, end_straights=100, ...)

# After (3.0)
route_bundle(cell, start_ports, end_ports, separation=..., starts=100, ends=100, ...)
```

#### Removed `place90`

`routing.optical.place90` has been removed. Use `place_manhattan` instead.

```python
# Before (2.x)
from kfactory.routing.optical import place90
place90(cell, p1, p2, pts, ...)

# After (3.0)
from kfactory.routing.optical import place_manhattan
place_manhattan(cell, p1, p2, pts, ...)
```

#### Default `connect()` mirror behavior

`config.connect_use_mirror` now defaults to `False` (it was `True` in 2.x). This means
`Instance.connect(...)` no longer applies the mirror flag carried by the target port by
default. Connections that previously relied on that implicit mirroring will place
instances differently.

To restore the old behavior, either opt in per call or flip the global config:

```python
import kfactory as kf

# Per connection
inst.connect("o1", other_inst, "o2", use_mirror=True)

# Globally (matches 2.x default)
kf.config.connect_use_mirror = True
```

#### `kfactory.netlist` module removed

Netlist extraction moved to the standalone [kfnetlist](https://github.com/gdsfactory/kfnetlist)
package (installed automatically as a dependency). The in-tree `kfactory.netlist` module
no longer exists. `kf.Netlist` is still re-exported for convenience.

```python
# Before (2.x)
from kfactory.netlist import Netlist

# After (3.0)
from kfnetlist import Netlist
# or
import kfactory as kf
kf.Netlist
```

#### Removed `get_schematic`

The `get_schematic` helper has been removed from the public API. Construct a `Schematic`
directly instead.

```python
# Before (2.x)
import kfactory as kf
schematic = kf.get_schematic(...)

# After (3.0)
import kfactory as kf
schematic = kf.Schematic(kcl=kcl)
```

#### Routing Interface for Schematics

In order to enable routing in schematics, routing strategy functions must be registered
on the `KCLayout` instance. Registered strategies can then be referenced by name in
`Schematic.add_route`.

##### Registering a Routing Strategy

Use the `@kcl.routing_strategy` decorator or assign directly to `kcl.routing_strategies`:

```python
import kfactory as kf

kcl = kf.KCLayout("MY_PDK")

@kcl.routing_strategy
def route_bundle(cell, start_ports, end_ports, **kwargs):
    ...

# Or register directly:
kcl.routing_strategies["my_custom_route"] = my_routing_function
```

##### Using Routes in a Schematic

The `Schematic.add_route` method creates a route bundle connecting start and end ports
using a named routing strategy:

```python
schematic = kf.Schematic(kcl=kcl)

# Add instances
mmi1 = schematic.add_instance("mmi1", mmi_factory, settings={...})
mmi2 = schematic.add_instance("mmi2", mmi_factory, settings={...})

# Place instances
mmi1.place(...)
mmi2.place(...)

# Route between instances
schematic.add_route(
    name="optical_route",
    start_ports=[mmi1.ports["o2"]],
    end_ports=[mmi2.ports["o1"]],
    routing_strategy="route_bundle",
    separation=10_000,
    # additional **settings are forwarded to the routing strategy function
)

# Build the cell
cell = schematic.create_cell(output_type=kf.KCell)
```

When `create_cell` is called, the schematic looks up the routing strategy by name from
`kcl.routing_strategies` (or from the `routing_strategies` argument to `create_cell`)
and calls it with the resolved ports and settings.

---

## kfactory 2.0

kfactory 2.0 was a full rewrite of the library on top of [KLayout](https://klayout.de), replacing the earlier 1.x codebase. There is no supported migration path from 1.x to 2.0.

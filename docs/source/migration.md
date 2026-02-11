# Migration

## kfactory 3.0

With kfactory 3.0, several modules, functions, and interfaces have changed.

### Module Reorganization

- `kfactory.factories.virtual.utils` has been moved to `kfactory.factories.utils` to unify it with other factory utilities.

```python
# Before (2.x)
from kfactory.factories.virtual.utils import extrude_backbone, extrude_backbone_dynamic

# After (3.0)
from kfactory.factories.utils import extrude_backbone, extrude_backbone_dynamic
```

### Removed Routing Functions

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

### Deprecated Parameters in `route_bundle`

In both `routing.optical.route_bundle` and `routing.electrical.route_bundle`:

- `start_straights` is deprecated — use `starts` instead
- `end_straights` is deprecated — use `ends` instead

```python
# Before (2.x)
route_bundle(cell, start_ports, end_ports, separation=..., start_straights=100, end_straights=100, ...)

# After (3.0)
route_bundle(cell, start_ports, end_ports, separation=..., starts=100, ends=100, ...)
```

### Deprecated `place90`

`routing.optical.place90` is deprecated. Use `place_manhattan` instead.

```python
# Before (2.x)
from kfactory.routing.optical import place90
place90(cell, p1, p2, pts, ...)

# After (3.0)
from kfactory.routing.optical import place_manhattan
place_manhattan(cell, p1, p2, pts, ...)
```

### Routing Interface for Schematics

In order to enable routing in schematics, routing strategy functions must be registered
on the `KCLayout` instance. Registered strategies can then be referenced by name in
`Schematic.add_route`.

#### Registering a Routing Strategy

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

#### Using Routes in a Schematic

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

# Factory Functions

A **factory** in kfactory is a function that returns another function — a *cell-making function* bound to a specific `KCLayout`. Factories are the recommended way to build production PDKs because they:

- **Tie cells to a specific layout** — every cell built by the factory lives in the same `KCLayout`, so layer indices are consistent.
- **Cache automatically** — the returned function is decorated with `@kcl.cell`, so repeated calls with the same arguments return the *same* cell object.
- **Carry typed protocols** — each factory returns a typed `Protocol` callable, so IDEs and type-checkers can validate arguments at the call site.
- **Enable routing** — the built-in routers (`route_bundle`, `place_manhattan`) require factory functions, not raw cells, so they can create bend/straight geometry on demand.

## Available factories

| Factory | Module | Page |
| --- | --- | --- |
| `straight_dbu_factory` | `kf.factories.straight` | [Straight](<https://gdsfactory.github.io/kfactory/3.4.0/components/cells/factories/straight/index.md>) |
| `bend_euler_factory` / `bend_s_euler_factory` | `kf.factories.euler` | [Euler](<https://gdsfactory.github.io/kfactory/3.4.0/components/cells/factories/euler/index.md>) |
| `bend_circular_factory` | `kf.factories.circular` | [Circular](<https://gdsfactory.github.io/kfactory/3.4.0/components/cells/factories/circular/index.md>) |
| `bend_s_bezier_factory` | `kf.factories.bezier` | [Bezier](<https://gdsfactory.github.io/kfactory/3.4.0/components/cells/factories/bezier/index.md>) |
| `taper_factory` | `kf.factories.taper` | [Taper](<https://gdsfactory.github.io/kfactory/3.4.0/components/cells/factories/taper/index.md>) |

## Factories and routing

The built-in optical router (`kf.routing.optical.route_bundle`) requires factory callables — it uses them to instantiate bends and straights while building a route. Passing cells directly is not supported.

```
routes = kf.routing.optical.route_bundle(
    c,
    start_ports=[...],
    end_ports=[...],
    bend90_cell=bend_euler,      # factory callable
    straight_factory=straight,   # factory callable
)
```

Because each factory is bound to a `KCLayout`, all route geometry automatically lands in the correct layout and uses the correct layer indices.

## Bundling factories in a PDK module

The recommended pattern for a production PDK is to define all factories in one place and import them wherever routing or assembly is needed:

```
# my_pdk/factories.py
import kfactory as kf
from kfactory.factories.straight import straight_dbu_factory
from kfactory.factories.euler import bend_euler_factory
from kfactory.factories.taper import taper_factory
from my_pdk.layers import LAYER

pdk = kf.KCLayout("MY_PDK", infos=LAYER)

straight = straight_dbu_factory(pdk)
bend_euler = bend_euler_factory(pdk)
taper = taper_factory(pdk)

__all__ = ["pdk", "straight", "bend_euler", "taper"]
```

## Key rules

- `straight_dbu_factory` / `taper_factory` — arguments in **DBU**
- `bend_euler_factory` / `bend_circular_factory` — `width` and `radius` in **µm**
- Always bind the factory to the same `KCLayout` that owns the cells being routed

## See Also

| Topic | Where |
| --- | --- |
| PCells &amp; caching | [Components: PCells](<https://gdsfactory.github.io/kfactory/3.4.0/components/cells/pcells/index.md>) |
| Cross-sections | [Cross-Sections](<https://gdsfactory.github.io/kfactory/3.4.0/components/cross_sections/index.md>) |
| Routing integration | [Routing: Overview](<https://gdsfactory.github.io/kfactory/3.4.0/routing/overview/index.md>) |
| PDK bundling pattern | [PDK: Creating a PDK](<https://gdsfactory.github.io/kfactory/3.4.0/pdk/creating_pdk/index.md>) |

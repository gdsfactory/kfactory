# RouteDebug in the Routing Pipeline

## Overview

`RouteDebug` (defined in `utils.py`) holds three `kdb.Region` fields that capture
path geometry from the routing pipeline so users can visualize which segments of a
bundle route correspond to fan-in, waypoints, and fan-out.

The regions are populated with `kdb.PathWithProperties` objects so each polygon
carries user-defined metadata:
- Fan-in: `{0: "(port_trans, 'fan_in - port_name')"}`
- Fan-out: `{0: "(port_trans, 'fan_out - port_name')"}`
- Waypoints: `{i: "(kdb.Trans(0, False, wp.x, wp.y), 'waypoints')"}`

| Field              | Meaning                                  |
|--------------------|------------------------------------------|
| `fan_in_region`    | Start ports to waypoint entry            |
| `waypoints_region` | Backbone through waypoints               |
| `fan_out_region`   | Waypoint exit to end ports               |

## Threading

The `route_debug: RouteDebug | None = None` parameter is threaded through:

```
electrical.route_bundle / optical.route_bundle / electrical.route_bundle_dual_rails / electrical.route_bundle_rf
  -> generic.route_bundle  (injects into routing_kwargs)
    -> manhattan.route_smart  (builds port name maps)
      -> manhattan._route_waypoints  (populates the regions with PathWithProperties)
```

All parameters default to `None`, so existing callers are unaffected.

## Region Population

Inside `_route_waypoints()`, after the fan-in/fan-out/backbone routers are computed
but before they are merged into final `ManhattanRouter` objects:

- **Sequence[kdb.Point] waypoints case**: all three regions are populated from
  `start_manhattan_routers`, `bundle_points`, and `end_manhattan_routers`.
  Each inserted `PathWithProperties` carries metadata about port transforms and names.
- **kdb.Trans waypoints case**: `fan_in_region` and `fan_out_region` are populated;
  `waypoints_region` stays empty (zero-length tunnel).
- **No waypoints**: `_route_waypoints` is never called, so all regions stay empty.

## Usage

```python
from kfactory.routing.utils import RouteDebug

debug = RouteDebug()
routes = electrical.route_bundle(c, start_ports, end_ports, ..., route_debug=debug)
# debug.fan_in_region, debug.waypoints_region, debug.fan_out_region are now populated
# Each polygon in the regions carries properties from PathWithProperties
```

# manhattan

Can calculate manhattan routes based on ports/transformations.

## ManhattanRoutePathFunction

Bases: `Protocol`

Minimal signature of a manhattan function.

### \_\_call\_\_

```
__call__(port1: Port | Trans, port2: Port | Trans, bend90_radius: int, start_steps: Sequence[Step] | None = None, end_steps: Sequence[Step] | None = None) -> list[kdb.Point]
```

Minimal kwargs of a manhattan route function.

## ManhattanRoutePathFunction180

Bases: `Protocol`

Minimal signature of a manhattan function with 180° bend routing.

### \_\_call\_\_

```
__call__(port1: Port | Trans, port2: Port | Trans, bend90_radius: int, bend180_radius: int, start_steps: list[Step] | None = None, end_steps: list[Step] | None = None) -> list[kdb.Point]
```

Minimal kwargs of a manhattan route function with 180° bend.

## ManhattanRouter

Class to store state of a routing between two ports or transformations.

### auto\_route

```
auto_route(max_try: int = 20, straight_s_bend_strategy: Literal['short', 'long'] = 'short', bbox: Box | None = None) -> list[kdb.Point]
```

Automatically determine a route from start to end.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `max_try` | `int` | Maximum number of routing steps it can take. This is a security measure to stop infinite loops. This should never trigger an error. | `20` |
| `straight_s_bend_strategy` | `Literal['short', 'long']` | When emulating an s-bend (build a large S out of 90deg bends), use the short or the longer route. | `'short'` |

### collisions

```
collisions(log_errors: Literal['warn', 'error'] | None = 'error') -> tuple[kdb.Edges, kdb.Edges]
```

Finds collisions.

A collision is if the router crosses itself in it's route (`self.start.pts`).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `log_errors` | `Literal['warn', 'error'] \| None` | sends the an error or a warning to the kfactory logger if not `None`. | `'error'` |

Returns:

| Type | Description |
| --- | --- |
| `tuple[Edges, Edges]` | tuple containing the collisions and all edges of the router |

### finish

```
finish() -> list[kdb.Point]
```

Determines whether the routing was successful.

If it was successful and the start and end are facing each other, store all the points of `self.end.pts` in `self.start.pts` in reversed order.

## ManhattanRouterSide

A simple manhattan point router.

Keeps track of the target and stores the points and transformation of the past routing.

## clean\_points

```
clean_points(points: Sequence[TPoint]) -> list[TPoint]
```

Remove useless points from a manhattan type of list.

Keeps the first and last points and every point where the direction changes, dropping the middle points that are on a straight line as well as duplicates.

## droute\_manhattan

```
droute_manhattan(port1: DTrans, port2: DTrans, bend90_radius: int, start_straight: int, end_straight: int, layout: KCLayout | Layout, invert: bool = False) -> list[kdb.Point]
```

Calculate manhattan route using um based points.

Doesn't use any non-90° bends.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port1` | `DTrans` | Transformation of start port. | *required* |
| `port2` | `DTrans` | Transformation of end port. | *required* |
| `bend90_radius` | `int` | The radius or (symmetrical) dimension of 90° bend. \[um\] | *required* |
| `start_straight` | `int` | Minimum straight after the starting port. \[um\] | *required* |
| `end_straight` | `int` | Minimum straight before the end port. \[um\] | *required* |
| `layout` | `KCLayout \| Layout` | Layout/KCLayout object where to get the dbu info from. | *required* |
| `invert` | `bool` | Invert the direction in which to route. In the normal behavior, route manhattan will try to take turns first. If true, it will try to route straight as long as possible | `False` |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `route` | `list[Point]` | Calculated route in points in dbu. |

## droute\_manhattan\_180

```
droute_manhattan_180(port1: DTrans, port2: DTrans, bend90_radius: float, bend180_radius: float, start_straight: float, end_straight: float, layout: KCLayout) -> list[kdb.Point]
```

Calculate manhattan route using um based points.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port1` | `DTrans` | Transformation of start port. | *required* |
| `port2` | `DTrans` | Transformation of end port. | *required* |
| `bend90_radius` | `float` | The radius or (symmetrical) dimension of 90° bend. \[um\] | *required* |
| `bend180_radius` | `float` | The distance between the two ports of the 180° bend. \[um\] | *required* |
| `start_straight` | `float` | Minimum straight after the starting port. \[um\] | *required* |
| `end_straight` | `float` | Minimum straight before the end port. \[um\] | *required* |
| `layout` | `KCLayout` | Layout/KCLayout object where to get the dbu info from. | *required* |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `route` | `list[Point]` | Calculated route in points in dbu. |

## path\_length\_match\_manhattan\_route

```
path_length_match_manhattan_route(*, routers: Sequence[ManhattanRouter], bend90_radius: int | None = None, separation: int | None = None, path_length: int | None = None) -> None
```

Simple path length matching router postprocess.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `routers` | `Sequence[ManhattanRouter]` | List of the manhattan routers to be modified. | *required* |
| `bend90_radius` | `int \| None` | Radius of a bend in the routes. | `None` |
| `separation` | `int \| None` | Separation between the routes. | `None` |
| `path_length` | `int \| None` | Match to a certain path length instead of the maximum of all routers. | `None` |

## route\_loosely

```
route_loosely(routers: Sequence[ManhattanRouter], separation: int, bbox_routing: Literal['minimal', 'full'], start_bbox: Box | None = None, end_bbox: Box | None = None, allow_sbend: bool = False) -> None
```

Route two port banks (all ports same direction) to the end.

This will not result in a tight bundle but use all the space available and choose the shortest path.

## route\_manhattan

```
route_manhattan(port1: Port | Trans, port2: Port | Trans, bend90_radius: int, start_steps: Sequence[Step] | None = None, end_steps: Sequence[Step] | None = None, invert: bool = False) -> list[kdb.Point]
```

Calculate manhattan route using um based points.

Only uses 90° bends.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port1` | `Port \| Trans` | Transformation of start port. | *required* |
| `port2` | `Port \| Trans` | Transformation of end port. | *required* |
| `bend90_radius` | `int` | The radius or (symmetrical) dimension of 90° bend. \[dbu\] | *required* |
| `start_steps` | `Sequence[Step] \| None` | Steps to take at the beginning of the route. \[dbu\] | `None` |
| `end_steps` | `Sequence[Step] \| None` | Steps to take at the end of the route. \[dbu\] | `None` |
| `invert` | `bool` | Invert the direction in which to route. In the normal behavior, route manhattan will try to take turns first. If true, it will try to route straight as long as possible | `False` |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `route` | `list[Point]` | Calculated route in dbu points. |

## route\_manhattan\_180

```
route_manhattan_180(port1: Port | Trans, port2: Port | Trans, bend90_radius: int, bend180_radius: int, start_straight: int, end_straight: int) -> list[kdb.Point]
```

Calculate manhattan route using um based points.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port1` | `Port \| Trans` | Transformation of start port. | *required* |
| `port2` | `Port \| Trans` | Transformation of end port. | *required* |
| `bend90_radius` | `int` | The radius or (symmetrical) dimension of 90° bend. \[dbu\] | *required* |
| `bend180_radius` | `int` | The distance between the two ports of the 180° bend. \[dbu\] | *required* |
| `start_straight` | `int` | Minimum straight after the starting port. \[dbu\] | *required* |
| `end_straight` | `int` | Minimum straight before the end port. \[dbu\] | *required* |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `route` | `list[Point]` | Calculated route in points in dbu. |

## route\_smart

```
route_smart(*, start_ports: Sequence[BasePort | Trans], end_ports: Sequence[BasePort | Trans], widths: Sequence[int] | None = None, bend90_radius: int | None = None, separation: int | None = None, starts: Sequence[Sequence[Step]] = [], ends: Sequence[Sequence[Step]] = [], bboxes: Sequence[Box] | None = None, sort_ports: bool = False, waypoints: Sequence[Point] | Trans | None = None, bbox_routing: Literal['minimal', 'full'] = 'minimal', allow_sbend: bool = False, route_debug: RouteDebug | None = None, **kwargs: Any) -> list[ManhattanRouter]
```

Route around start or end bboxes (obstacles on the way not implemented yet).

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `start_ports` | `Sequence[BasePort \| Trans]` | Ports where the routing should start. | *required* |
| `end_ports` | `Sequence[BasePort \| Trans]` | Ports denoting the end of the routes. Per bundle (separate bbox from any other router bundles, i.e. routers are not interacting in any way with other routers of the other groups) they must have the same angle. | *required* |
| `bend90_radius` | `int \| None` | The radius for 90° bends in dbu. | `None` |
| `separation` | `int \| None` | Separation which should be maintained between the routers in dbu. | `None` |
| `starts` | `Sequence[Sequence[Step]]` | Add straights at the beginning of each route in dbu. | `[]` |
| `ends` | `Sequence[Sequence[Step]]` | Add straights in dbu at the end of all routes. | `[]` |
| `bboxes` | `Sequence[Box] \| None` | List of bounding boxes used to denote obstacles. | `None` |
| `widths` | `Sequence[int] \| None` | Defines the width of the core material of each route. | `None` |
| `sort_ports` | `bool` | Whether to allow rearranging of ports given as inputs or outputs. | `False` |
| `waypoints` | `Sequence[Point] \| Trans \| None` | Bundle the ports and route them with minimal separation through the waypoints. The waypoints can either be a list of at least two points or a single transformation. If it's a transformation, the points will be routed through it as if it were a tunnel with length 0. | `None` |
| `bbox_routing` | `Literal['minimal', 'full']` | "minimal": only route to the bbox so that it can be safely routed around, but start or end bends might encroach on the bounding boxes when leaving them. | `'minimal'` |
| `allow_sbend` | `bool` | Allows the router to route the final pieces with sbends. | `False` |
| `kwargs` | `Any` | Additional kwargs. Compatibility for type checking. If any kwargs are passed an error is raised. | `{}` |

Raises: ValueError: If the route cannot conform to bend radius and other routing restrictions a value error is raised. Returns: List of ManhattanRoute objects which contain all the instances in the route as well as the route info.

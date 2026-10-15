# electrical

Utilities for automatically routing electrical connections.

## place\_asymmetric\_wire

```
place_asymmetric_wire(c: KCell, p1: Port, p2: Port, pts: Sequence[Point], route_width: int | None = None, layer_info: LayerInfo | None = None, **kwargs: Any) -> ManhattanRoute
```

Draw every signed band of an asymmetric profile along a Manhattan backbone.

Bands are joined with mitered corners in integer coordinates and merged per layer. The start port's mirror flag determines the transverse orientation. Endpoints must carry the same profile with opposite mirror flags. Changing width requires an explicit transition rather than discarding auxiliary bands.

## place\_dual\_rails

```
place_dual_rails(c: KCell, p1: Port, p2: Port, pts: Sequence[Point], route_width: int | None = None, layer_info: LayerInfo | None = None, separation_rails: int | None = None, **kwargs: Any) -> ManhattanRoute
```

Placer function for a single wire.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | KCell to place the route in. | *required* |
| `p1` | `Port` | Start port. | *required* |
| `p2` | `Port` | End port. | *required* |
| `pts` | `Sequence[Point]` | Route backbone. | *required* |
| `route_width` | `int \| None` | Overwrite automatic detection of wire width. Total width of all rails. | `None` |
| `layer_info` | `LayerInfo \| None` | Place on a specific layer. Otherwise, use `p1.layer_info`. | `None` |
| `separation_rails` | `int \| None` | Separation between the two rails. | `None` |
| `kwargs` | `Any` | Compatibility for type checkers. Throws an error if not empty. | `{}` |

## place\_rf\_rails

```
place_rf_rails(c: KCell, p1: Port, p2: Port, pts: Sequence[Point], route_width: int | None = None, *, center_trans: Trans | None = None, layer_info: LayerInfo | None = None, enclosure: LayerEnclosure | None = None, center_radius: dbu = 0, bend_factory: BendFactory | None = None, wire_factory: WireFactory | None = None, port_type: str = 'electrical', allow_small_routes: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, purpose: str | None = 'routing', **kwargs: Any) -> ManhattanRoute
```

Placer function for a single wire.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | KCell to place the route in. | *required* |
| `p1` | `Port` | Start port. | *required* |
| `p2` | `Port` | End port. | *required* |
| `pts` | `Sequence[Point]` | Route backbone. | *required* |
| `route_width` | `int \| None` | Overwrite automatic detection of wire width. Total width of all rails. | `None` |
| `layer_info` | `LayerInfo \| None` | Place on a specific layer. Otherwise, use `p1.layer_info`. | `None` |
| `enclosure` | `LayerEnclosure \| None` | Apply an enclosure to the rail. | `None` |
| `center_radius` | `dbu` | The radius at the center of the rails. | `0` |
| `bend_factory` | `BendFactory \| None` | The function to call to create the rail bends. | `None` |
| `wire_factory` | `WireFactory \| None` | The function to call to create the straights of the rails. | `None` |
| `port_type` | `str` | Which port\_type to filter the bend for. | `'electrical'` |
| `allow_small_routes` | `bool` | Proceed with placing even if there is not enough space. | `False` |
| `allow_width_mismatch` | `bool \| None` | Allow to place even if port widths do not match. | `None` |
| `allow_layer_mismatch` | `bool \| None` | Allow to place even if port layers do not match. | `None` |
| `allow_type_mismatch` | `bool \| None` | Allow to place even if port port\_type do not match. | `None` |
| `purpose` | `str \| None` | Which `Instance.purpose` to assign to the created instances of the placer. | `'routing'` |
| `kwargs` | `Any` | Compatibility for type checkers. Throws an error if not empty. | `{}` |

## place\_single\_wire

```
place_single_wire(c: KCell, p1: Port, p2: Port, pts: Sequence[Point], route_width: int | None = None, layer_info: LayerInfo | None = None, **kwargs: Any) -> ManhattanRoute
```

Placer function for a single wire.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | KCell to place the route in. | *required* |
| `p1` | `Port` | Start port. | *required* |
| `p2` | `Port` | End port. | *required* |
| `pts` | `Sequence[Point]` | Route backbone. | *required* |
| `route_width` | `int \| None` | Overwrite automatic detection of wire width. | `None` |
| `layer_info` | `LayerInfo \| None` | Place on a specific layer. Otherwise, use `p1.layer_info`. | `None` |
| `kwargs` | `Any` | Compatibility for type checkers. Throws an error if not empty. | `{}` |

## route\_bundle

```
route_bundle(c: KCell, start_ports: Sequence[Port], end_ports: Sequence[Port], separation: dbu, place_layer: LayerInfo | None = None, route_width: dbu | list[dbu] | None = None, bboxes: Sequence[Box] | None = None, bbox_routing: Literal['minimal', 'full'] = 'minimal', sort_ports: bool = False, collision_check_layers: Sequence[LayerInfo] | None = None, on_collision: Literal['error', 'show_error'] | None = 'show_error', on_placer_error: Literal['error', 'show_error'] | None = 'show_error', waypoints: Trans | list[Point] | None = None, starts: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None, ends: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None, start_angles: int | list[int] | None = None, end_angles: int | list[int] | None = None, purpose: str | None = 'routing', constraints: Sequence[Constraint] | None = None, route_debug: RouteDebug | None = None) -> list[ManhattanRoute]
```

```
route_bundle(c: DKCell, start_ports: Sequence[DPort], end_ports: Sequence[DPort], separation: um, place_layer: LayerInfo | None = None, route_width: um | list[um] | None = None, bboxes: Sequence[DBox] | None = None, bbox_routing: Literal['minimal', 'full'] = 'minimal', sort_ports: bool = False, collision_check_layers: Sequence[LayerInfo] | None = None, on_collision: Literal['error', 'show_error'] | None = 'show_error', on_placer_error: Literal['error', 'show_error'] | None = 'show_error', waypoints: DTrans | list[DPoint] | None = None, starts: um | list[um] | list[Step] | list[list[Step]] | None = None, ends: um | list[um] | list[Step] | list[list[Step]] | None = None, start_angles: float | list[float] | None = None, end_angles: float | list[float] | None = None, purpose: str | None = 'routing', constraints: Sequence[Constraint] | None = None, route_debug: RouteDebug | None = None) -> list[ManhattanRoute]
```

```
route_bundle(c: KCell | DKCell, start_ports: Sequence[Port] | Sequence[DPort], end_ports: Sequence[Port] | Sequence[DPort], separation: dbu | um, place_layer: LayerInfo | None = None, route_width: dbu | um | list[dbu] | list[um] | None = None, bboxes: Sequence[Box] | Sequence[DBox] | None = None, bbox_routing: Literal['minimal', 'full'] = 'minimal', sort_ports: bool = False, collision_check_layers: Sequence[LayerInfo] | None = None, on_collision: Literal['error', 'show_error'] | None = 'show_error', on_placer_error: Literal['error', 'show_error'] | None = 'show_error', waypoints: Trans | list[Point] | DTrans | list[DPoint] | None = None, starts: dbu | list[dbu] | um | list[um] | list[Step] | list[list[Step]] | None = None, ends: dbu | list[dbu] | um | list[um] | list[Step] | list[list[Step]] | None = None, start_angles: list[int] | float | list[float] | None = None, end_angles: list[int] | float | list[float] | None = None, purpose: str | None = 'routing', constraints: Sequence[Constraint] | None = None, route_debug: RouteDebug | None = None) -> list[ManhattanRoute]
```

Connect multiple input ports to output ports.

This function takes a list of input ports and assume they are all oriented in the same direction (could be any of W, S, E, N). The target ports have the opposite orientation, i.e. if input ports are oriented to north, and target ports should be oriented to south. The function will produce a routing to connect input ports to output ports without any crossings.

Waypoints will create a front which will create ports in a 1D array. If waypoints are a transformation it will be like a point with a direction. If multiple points are passed, the direction will be invfered. For orientation of 0 degrees it will create the following front for 4 ports:

```
      │
      │
      │
      p1 ->
      │
      │
      │


      │
      │
      │
      p2 ->
      │
      │
      │
  ___\waypoint
     /
      │
      │
      │
      p3 ->
      │
      │
      │


      │
      │
      │
      p4 ->
      │
      │
      │
```

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell \| DKCell` | KCell to place the routes in. | *required* |
| `start_ports` | `Sequence[Port] \| Sequence[DPort]` | List of start ports. | *required* |
| `end_ports` | `Sequence[Port] \| Sequence[DPort]` | List of end ports. | *required* |
| `separation` | `dbu \| um` | Minimum space between wires. \[dbu\] | *required* |
| `starts` | `dbu \| list[dbu] \| um \| list[um] \| list[Step] \| list[list[Step]] \| None` | Minimal straight segment after `start_ports`. | `None` |
| `ends` | `dbu \| list[dbu] \| um \| list[um] \| list[Step] \| list[list[Step]] \| None` | Minimal straight segment before `end_ports`. | `None` |
| `place_layer` | `LayerInfo \| None` | Override automatic detection of layers with specific layer. | `None` |
| `route_width` | `dbu \| um \| list[dbu] \| list[um] \| None` | Width of the route. If None, the width of the ports is used. | `None` |
| `bboxes` | `Sequence[Box] \| Sequence[DBox] \| None` | List of boxes to consider. Currently only boxes overlapping ports will be considered. | `None` |
| `bbox_routing` | `Literal['minimal', 'full']` | "minimal": only route to the bbox so that it can be safely routed around, but start or end bends might encroach on the bounding boxes when leaving them. | `'minimal'` |
| `sort_ports` | `bool` | Automatically sort ports. | `False` |
| `collision_check_layers` | `Sequence[LayerInfo] \| None` | Layers to check for actual errors if manhattan routes detect potential collisions. | `None` |
| `on_collision` | `Literal['error', 'show_error'] \| None` | Define what to do on routing collision. Default behaviour is to open send the layout of c to klive and open an error lyrdb with the collisions. "error" will simply raise an error. None will ignore any error. | `'show_error'` |
| `on_placer_error` | `Literal['error', 'show_error'] \| None` | If a placing of the components fails, use the strategy above to handle the error. show\_error will visualize it in klayout with the intended route along the already placed parts of c. Error will just throw an error. None will ignore the error. | `'show_error'` |
| `waypoints` | `Trans \| list[Point] \| DTrans \| list[DPoint] \| None` | Bundle the ports and route them with minimal separation through the waypoints. The waypoints can either be a list of at least two points or a single transformation. If it's a transformation, the points will be routed through it as if it were a tunnel with length 0. | `None` |
| `start_angles` | `list[int] \| float \| list[float] \| None` | Overwrite the port orientation of all start\_ports together (single value) or each one (list of values which is as long as start\_ports). | `None` |
| `end_angles` | `list[int] \| float \| list[float] \| None` | Overwrite the port orientation of all start\_ports together (single value) or each one (list of values which is as long as end\_ports). If no waypoints are set, the target angles of all ends muts be the same (after the steps). | `None` |
| `purpose` | `str \| None` | Purpose of the routes. (Unused) | `'routing'` |

## route\_bundle\_dual\_rails

```
route_bundle_dual_rails(c: KCell, start_ports: list[Port], end_ports: list[Port], separation: dbu, place_layer: LayerInfo | None = None, width_rails: dbu | None = None, separation_rails: dbu | None = None, bboxes: list[Box] | None = None, bbox_routing: Literal['minimal', 'full'] = 'minimal', sort_ports: bool = False, collision_check_layers: Sequence[LayerInfo] | None = None, on_collision: Literal['error', 'show_error'] | None = 'show_error', on_placer_error: Literal['error', 'show_error'] | None = 'show_error', waypoints: Trans | list[Point] | None = None, starts: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None, ends: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None, start_angles: int | list[int] | None = None, end_angles: int | list[int] | None = None, constraints: Sequence[Constraint] | None = None, route_debug: RouteDebug | None = None) -> list[ManhattanRoute]
```

Connect multiple input ports to output ports.

This function takes a list of input ports and assume they are all oriented in the same direction (could be any of W, S, E, N). The target ports have the opposite orientation, i.e. if input ports are oriented to north, and target ports should be oriented to south. The function will produce a routing to connect input ports to output ports without any crossings.

Waypoints will create a front which will create ports in a 1D array. If waypoints are a transformation it will be like a point with a direction. If multiple points are passed, the direction will be invfered. For orientation of 0 degrees it will create the following front for 4 ports:

```
      │
      │
      │
      p1 ->
      │
      │
      │


      │
      │
      │
      p2 ->
      │
      │
      │
  ___\waypoint
     /
      │
      │
      │
      p3 ->
      │
      │
      │


      │
      │
      │
      p4 ->
      │
      │
      │
```

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | KCell to place the routes in. | *required* |
| `start_ports` | `list[Port]` | List of start ports. | *required* |
| `end_ports` | `list[Port]` | List of end ports. | *required* |
| `separation` | `dbu` | Minimum space between wires. \[dbu\] | *required* |
| `starts` | `dbu \| list[dbu] \| list[Step] \| list[list[Step]] \| None` | Minimal straight segment after `start_ports`. | `None` |
| `ends` | `dbu \| list[dbu] \| list[Step] \| list[list[Step]] \| None` | Minimal straight segment before `end_ports`. | `None` |
| `place_layer` | `LayerInfo \| None` | Override automatic detection of layers with specific layer. | `None` |
| `width_rails` | `dbu \| None` | Total width of the rails. | `None` |
| `separation_rails` | `dbu \| None` | Separation between the two rails. | `None` |
| `bboxes` | `list[Box] \| None` | List of boxes to consider. Currently only boxes overlapping ports will be considered. | `None` |
| `bbox_routing` | `Literal['minimal', 'full']` | "minimal": only route to the bbox so that it can be safely routed around, but start or end bends might encroach on the bounding boxes when leaving them. | `'minimal'` |
| `sort_ports` | `bool` | Automatically sort ports. | `False` |
| `collision_check_layers` | `Sequence[LayerInfo] \| None` | Layers to check for actual errors if manhattan routes detect potential collisions. | `None` |
| `on_collision` | `Literal['error', 'show_error'] \| None` | Define what to do on routing collision. Default behaviour is to open send the layout of c to klive and open an error lyrdb with the collisions. "error" will simply raise an error. None will ignore any error. | `'show_error'` |
| `on_placer_error` | `Literal['error', 'show_error'] \| None` | If a placing of the components fails, use the strategy above to handle the error. show\_error will visualize it in klayout with the intended route along the already placed parts of c. Error will just throw an error. None will ignore the error. | `'show_error'` |
| `waypoints` | `Trans \| list[Point] \| None` | Bundle the ports and route them with minimal separation through the waypoints. The waypoints can either be a list of at least two points or a single transformation. If it's a transformation, the points will be routed through it as if it were a tunnel with length 0. | `None` |
| `start_angles` | `int \| list[int] \| None` | Overwrite the port orientation of all start\_ports together (single value) or each one (list of values which is as long as start\_ports). | `None` |
| `end_angles` | `int \| list[int] \| None` | Overwrite the port orientation of all start\_ports together (single value) or each one (list of values which is as long as end\_ports). If no waypoints are set, the target angles of all ends muts be the same (after the steps). | `None` |

## route\_bundle\_rf

```
route_bundle_rf(c: KCell, start_ports: Sequence[Port] | Sequence[DPort], end_ports: Sequence[Port] | Sequence[DPort], wire_factory: WireFactory, bend_factory: BendFactory, place_port_type: str = 'electrical', place_allow_small_routes: bool = False, collision_check_layers: Sequence[LayerInfo] | None = None, on_collision: Literal['error', 'show_error'] | None = 'show_error', on_placer_error: Literal['error', 'show_error'] | None = 'show_error', allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, sort_ports: bool = False, waypoints: Trans | list[Point] | DCplxTrans | list[DPoint] | None = None, starts: dbu | list[dbu] | um | list[um] | list[Step] | list[list[Step]] | None = None, ends: dbu | list[dbu] | um | list[um] | list[Step] | list[list[Step]] | None = None, start_angles: list[int] | float | list[float] | None = None, end_angles: list[int] | float | list[float] | None = None, purpose: str | None = 'routing', minimum_radius: int = 0, constraints: Sequence[Constraint] | None = None, route_debug: RouteDebug | None = None, *, layer: LayerInfo, enclosure: LayerEnclosure | None = None, bboxes: list[Box] | None = None) -> list[ManhattanRoute]
```

Route a bundle from starting ports to end\_ports.

Waypoints will create a front which will create ports in a 1D array. If waypoints are a transformation it will be like a point with a direction. If multiple points are passed, the direction will be invfered. For orientation of 0 degrees it will create the following front for 4 ports:

```
      │
      │
      │
      p1 ->
      │
      │
      │


      │
      │
      │
      p2 ->
      │
      │
      │
  ___\waypoint
     /
      │
      │
      │
      p3 ->
      │
      │
      │


      │
      │
      │
      p4 ->
      │
      │
      │
```

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | Cell to place the route in. | *required* |
| `start_ports` | `Sequence[Port] \| Sequence[DPort]` | List of start ports. | *required* |
| `end_ports` | `Sequence[Port] \| Sequence[DPort]` | List of end ports. | *required* |
| `starts` | `dbu \| list[dbu] \| um \| list[um] \| list[Step] \| list[list[Step]] \| None` | Minimal straight segment after `start_ports`. | `None` |
| `ends` | `dbu \| list[dbu] \| um \| list[um] \| list[Step] \| list[list[Step]] \| None` | Minimal straight segment before `end_ports`. | `None` |
| `bend_factory` | `BendFactory` | The function to call to create the rail bends. | *required* |
| `wire_factory` | `WireFactory` | The function to call to create the straights of the rails. | *required* |
| `place_port_type` | `str` | Port type to use for the bend90\_cell. | `'electrical'` |
| `place_allow_small_routes` | `bool` | Don't throw an error if two corners cannot be placed. | `False` |
| `collision_check_layers` | `Sequence[LayerInfo] \| None` | Layers to check for actual errors if manhattan routes detect potential collisions. | `None` |
| `on_collision` | `Literal['error', 'show_error'] \| None` | Define what to do on routing collision. Default behaviour is to open send the layout of c to klive and open an error lyrdb with the collisions. "error" will simply raise an error. None will ignore any error. | `'show_error'` |
| `on_placer_error` | `Literal['error', 'show_error'] \| None` | If a placing of the components fails, use the strategy above to handle the error. show\_error will visualize it in klayout with the intended route along the already placed parts of c. Error will just throw an error. None will ignore the error. | `'show_error'` |
| `bboxes` | `list[Box] \| None` | List of boxes to consider. Currently only boxes overlapping ports will be considered. | `None` |
| `allow_width_mismatch` | `bool \| None` | If True, the width of the ports is ignored (config default: False). | `None` |
| `allow_layer_mismatch` | `bool \| None` | If True, the layer of the ports is ignored (config default: False). | `None` |
| `allow_type_mismatch` | `bool \| None` | If True, the type of the ports is ignored (config default: False). | `None` |
| `sort_ports` | `bool` | Automatically sort ports. | `False` |
| `waypoints` | `Trans \| list[Point] \| DCplxTrans \| list[DPoint] \| None` | Bundle the ports and route them with minimal separation through the waypoints. The waypoints can either be a list of at least two points or a single transformation. If it's a transformation, the points will be routed through it as if it were a tunnel with length 0. | `None` |
| `start_angles` | `list[int] \| float \| list[float] \| None` | Overwrite the port orientation of all start\_ports together (single value) or each one (list of values which is as long as start\_ports). | `None` |
| `end_angles` | `list[int] \| float \| list[float] \| None` | Overwrite the port orientation of all start\_ports together (single value) or each one (list of values which is as long as end\_ports). If no waypoints are set, the target angles of all ends muts be the same (after the steps). | `None` |
| `purpose` | `str \| None` | Set the property "purpose" (at id kf.kcell.PROPID.PURPOSE) to the value. Not set if None. | `'routing'` |

Returns:

| Type | Description |
| --- | --- |
| `list[ManhattanRoute]` | list\[ManhattanRoute\]: The route object with the placed components. |

## route\_dual\_rails

```
route_dual_rails(c: KCell, p1: Port, p2: Port, start_straight: dbu | None = None, end_straight: dbu | None = None, route_path_function: Callable[..., list[Point]] = route_manhattan, width: dbu | None = None, hole_width: dbu | None = None, layer: int | None = None) -> None
```

Connect ports with a dual-wire rail.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | KCell to place the connection in. | *required* |
| `p1` | `Port` | Start port. | *required* |
| `p2` | `Port` | End port. | *required* |
| `start_straight` | `dbu \| None` | Minimum straight after the start port. | `None` |
| `end_straight` | `dbu \| None` | Minimum straight before end port. | `None` |
| `route_path_function` | `Callable[..., list[Point]]` | Function to calculate the path. Signature: `route_path_function(p1, p2, bend90_radius, start_straight, end_straight)` | `route_manhattan` |
| `width` | `dbu \| None` | Width of the rail (total). \[dbu\] | `None` |
| `hole_width` | `dbu \| None` | Width of the space between the rails. \[dbu\] | `None` |
| `layer` | `int \| None` | layer to place the rail in. | `None` |

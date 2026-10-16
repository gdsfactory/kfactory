# optical

Optical routing allows the creation of photonic (or any route using bends).

## get\_radius

```
get_radius(ports: Sequence[ProtoPort[Any]]) -> dbu
```

Calculates a radius between two ports.

This can be used to determine the radius of two bend ports.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `ports` | `Sequence[ProtoPort[Any]]` | A sequence of exactly two ports. | *required* |

Returns:

| Type | Description |
| --- | --- |
| `dbu` | Radius in dbu. |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | Radius cannot be determined |

## place\_manhattan

```
place_manhattan(c: ProtoTKCell[Any], p1: Port, p2: Port, pts: Sequence[Point], route_width: dbu | None = None, straight_factory: StraightFactoryDBU | None = None, bend90_cell: ProtoTKCell[Any] | None = None, taper_cell: ProtoTKCell[Any] | None = None, port_type: str = 'optical', min_straight_taper: dbu = 0, allow_small_routes: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, purpose: str | None = 'routing', **kwargs: Any) -> ManhattanRoute
```

Place a symmetric backbone using straight or tapered segments and 90° bends.

Bend geometry and taper ports are resolved once. Each connection between bends uses the same segment selection, including the final connection. Symmetric connection rules and area-based route length are preserved.

## place\_manhattan\_asymmetric

```
place_manhattan_asymmetric(c: ProtoTKCell[Any], p1: Port, p2: Port, pts: Sequence[Point], route_width: dbu | None = None, *, straight_factory: StraightFactoryDBU | None = None, bend90_cell: tuple[ProtoTKCell[Any], ProtoTKCell[Any]] | None = None, taper_cell: ProtoTKCell[Any] | None = None, port_type: str = 'optical', min_straight_taper: dbu = 0, allow_small_routes: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, purpose: str | None = 'routing', **kwargs: Any) -> ManhattanRoute
```

Place an asymmetric profile using two opposite-handed 90° bends.

Both bends must carry the endpoint cross section and have the same radius. Classify the bends once by input orientation, then select directly at each corner to preserve the incoming transverse profile. Straight and taper connections preserve all bands, not just the core width. Width/profile changes require explicit transitions; mismatch flags cannot override profile compatibility. S-bend factories are not supported here. The returned route's default length is its Manhattan backbone length, not optical path length: area divided by core width is invalid for these profiles.

## place\_manhattan\_with\_sbends

```
place_manhattan_with_sbends(c: ProtoTKCell[Any], p1: Port, p2: Port, pts: Sequence[Point], route_width: dbu | None = None, straight_factory: StraightFactoryDBU | None = None, bend90_cell: ProtoTKCell[Any] | None = None, taper_cell: ProtoTKCell[Any] | None = None, port_type: str = 'optical', min_straight_taper: dbu = 0, allow_small_routes: bool = False, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, purpose: str | None = 'routing', *, sbend_factory: SBendFactoryDBU | None = None, **kwargs: Any) -> ManhattanRoute
```

Place a symmetric backbone using straight, tapered and S-bend segments.

Bend geometry and taper ports are resolved once. Each connection between bends uses the same segment selection, including the final connection. Symmetric connection rules and area-based route length are preserved.

## route\_bundle

```
route_bundle(c: KCell, start_ports: Sequence[Port], end_ports: Sequence[Port], separation: dbu, straight_factory: StraightFactoryDBU, bend90_cell: KCell | tuple[KCell, KCell], taper_cell: KCell | None = None, min_straight_taper: dbu = 0, place_port_type: str = 'optical', place_allow_small_routes: bool = False, collision_check_layers: Sequence[LayerInfo] | None = None, on_collision: Literal['error', 'show_error'] | None = 'show_error', on_placer_error: Literal['error', 'show_error'] | None = 'show_error', bboxes: list[Box] | None = None, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, route_width: dbu | list[dbu] | None = None, sort_ports: bool = False, bbox_routing: Literal['minimal', 'full'] = 'minimal', waypoints: Trans | list[Point] | None = None, starts: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None, ends: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None, start_angles: int | list[int] | None = None, end_angles: int | list[int] | None = None, purpose: str | None = 'routing', sbend_factory: SBendFactoryDBU | None = None, constraints: Sequence[Constraint] | None = None, route_debug: RouteDebug | None = None, route_name: str | None = None) -> list[ManhattanRoute]
```

```
route_bundle(c: DKCell, start_ports: Sequence[DPort], end_ports: Sequence[DPort], separation: um, straight_factory: StraightFactoryUM, bend90_cell: DKCell | tuple[DKCell, DKCell], taper_cell: DKCell | None = None, min_straight_taper: um = 0, place_port_type: str = 'optical', place_allow_small_routes: bool = False, collision_check_layers: Sequence[LayerInfo] | None = None, on_collision: Literal['error', 'show_error'] | None = 'show_error', on_placer_error: Literal['error', 'show_error'] | None = 'show_error', bboxes: list[DBox] | None = None, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, route_width: um | list[um] | None = None, sort_ports: bool = False, bbox_routing: Literal['minimal', 'full'] = 'minimal', waypoints: Trans | list[DPoint] | None = None, starts: um | list[um] | list[Step] | list[list[Step]] | None = None, ends: um | list[um] | list[Step] | list[list[Step]] | None = None, start_angles: float | list[float] | None = None, end_angles: float | list[float] | None = None, purpose: str | None = 'routing', sbend_factory: SBendFactoryUM | None = None, constraints: Sequence[Constraint] | None = None, route_debug: RouteDebug | None = None, route_name: str | None = None) -> list[ManhattanRoute]
```

```
route_bundle(c: KCell | DKCell, start_ports: Sequence[Port] | Sequence[DPort], end_ports: Sequence[Port] | Sequence[DPort], separation: dbu | um, straight_factory: StraightFactoryDBU | StraightFactoryUM, bend90_cell: KCell | DKCell | tuple[KCell, KCell] | tuple[DKCell, DKCell], taper_cell: KCell | DKCell | None = None, min_straight_taper: dbu | float = 0, place_port_type: str = 'optical', place_allow_small_routes: bool = False, collision_check_layers: Sequence[LayerInfo] | None = None, on_collision: Literal['error', 'show_error'] | None = 'show_error', on_placer_error: Literal['error', 'show_error'] | None = 'show_error', bboxes: list[Box] | list[DBox] | None = None, allow_width_mismatch: bool | None = None, allow_layer_mismatch: bool | None = None, allow_type_mismatch: bool | None = None, route_width: dbu | list[dbu] | um | list[um] | None = None, sort_ports: bool = False, bbox_routing: Literal['minimal', 'full'] = 'minimal', waypoints: Trans | list[Point] | DCplxTrans | list[DPoint] | None = None, starts: dbu | list[dbu] | um | list[um] | list[Step] | list[list[Step]] | None = None, ends: dbu | list[dbu] | um | list[um] | list[Step] | list[list[Step]] | None = None, start_angles: list[int] | float | list[float] | None = None, end_angles: list[int] | float | list[float] | None = None, purpose: str | None = 'routing', sbend_factory: SBendFactoryDBU | SBendFactoryUM | None = None, constraints: Sequence[Constraint] | None = None, route_debug: RouteDebug | None = None, route_name: str | None = None) -> list[ManhattanRoute]
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
| `c` | `KCell \| DKCell` | Cell to place the route in. | *required* |
| `start_ports` | `Sequence[Port] \| Sequence[DPort]` | List of start ports. | *required* |
| `end_ports` | `Sequence[Port] \| Sequence[DPort]` | List of end ports. | *required* |
| `separation` | `dbu \| um` | Separation between the routes. | *required* |
| `straight_factory` | `StraightFactoryDBU \| StraightFactoryUM` | Factory function for straight cells. in DBU. | *required* |
| `bend90_cell` | `KCell \| DKCell \| tuple[KCell, KCell] \| tuple[DKCell, DKCell]` | 90° bend cell, or a pair of opposite-handed bends with the same cross section and radius. Asymmetric profiles need both hands to support arbitrary turns without swapping their transverse sections. | *required* |
| `taper_cell` | `KCell \| DKCell \| None` | Taper cell. | `None` |
| `starts` | `dbu \| list[dbu] \| um \| list[um] \| list[Step] \| list[list[Step]] \| None` | Minimal straight segment after `start_ports`. | `None` |
| `ends` | `dbu \| list[dbu] \| um \| list[um] \| list[Step] \| list[list[Step]] \| None` | Minimal straight segment before `end_ports`. | `None` |
| `min_straight_taper` | `dbu \| float` | Minimum straight \[dbu\] before attempting to place tapers. | `0` |
| `place_port_type` | `str` | Port type to use for the bend90\_cell. | `'optical'` |
| `place_allow_small_routes` | `bool` | Don't throw an error if two corners cannot be placed. | `False` |
| `collision_check_layers` | `Sequence[LayerInfo] \| None` | Layers to check for actual errors if manhattan routes detect potential collisions. | `None` |
| `on_collision` | `Literal['error', 'show_error'] \| None` | Define what to do on routing collision. Default behaviour is to open send the layout of c to klive and open an error lyrdb with the collisions. "error" will simply raise an error. None will ignore any error. | `'show_error'` |
| `on_placer_error` | `Literal['error', 'show_error'] \| None` | If a placing of the components fails, use the strategy above to handle the error. show\_error will visualize it in klayout with the intended route along the already placed parts of c. Error will just throw an error. None will ignore the error. | `'show_error'` |
| `bboxes` | `list[Box] \| list[DBox] \| None` | List of boxes to consider. Currently only boxes overlapping ports will be considered. | `None` |
| `allow_width_mismatch` | `bool \| None` | If True, the width of the ports is ignored (config default: False). | `None` |
| `allow_layer_mismatch` | `bool \| None` | If True, the layer of the ports is ignored (config default: False). | `None` |
| `allow_type_mismatch` | `bool \| None` | If True, the type of the ports is ignored (config default: False). | `None` |
| `route_width` | `dbu \| list[dbu] \| um \| list[um] \| None` | Width of the route. If None, the width of the ports is used. | `None` |
| `sort_ports` | `bool` | Automatically sort ports. | `False` |
| `bbox_routing` | `Literal['minimal', 'full']` | "minimal": only route to the bbox so that it can be safely routed around, but start or end bends might encroach on the bounding boxes when leaving them. | `'minimal'` |
| `waypoints` | `Trans \| list[Point] \| DCplxTrans \| list[DPoint] \| None` | Bundle the ports and route them with minimal separation through the waypoints. The waypoints can either be a list of at least two points or a single transformation. If it's a transformation, the points will be routed through it as if it were a tunnel with length 0. | `None` |
| `start_angles` | `list[int] \| float \| list[float] \| None` | Overwrite the port orientation of all start\_ports together (single value) or each one (list of values which is as long as start\_ports). | `None` |
| `end_angles` | `list[int] \| float \| list[float] \| None` | Overwrite the port orientation of all start\_ports together (single value) or each one (list of values which is as long as end\_ports). If no waypoints are set, the target angles of all ends muts be the same (after the steps). | `None` |
| `purpose` | `str \| None` | Set the property "purpose" (at id kf.kcell.PROPID.PURPOSE) to the value. Not set if None. | `'routing'` |

Returns:

| Type | Description |
| --- | --- |
| `list[ManhattanRoute]` | list\[ManhattanRoute\]: The route object with the placed components. |

## route\_loopback

```
route_loopback(port1: Port | Trans, port2: Port | Trans, bend90_radius: dbu, bend180_radius: dbu | None = None, start_straight: dbu = 0, end_straight: dbu = 0, d_loop: dbu = 200000, inside: bool = False) -> list[kdb.Point]
```

Create a loopback on two parallel ports.

```
inside == False
╭----╮            ╭----╮
|    |            |    |
|  -----        -----  |
|  port1        port2  |
╰----------------------╯
inside == True
    ╭---╮     ╭---╮
    |   |     |   |
  ----- |     | -----
  port1 |     | port2
        ╰-----╯
```

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `port1` | `Port \| Trans` | Start port. | *required* |
| `port2` | `Port \| Trans` | End port. | *required* |
| `bend90_radius` | `dbu` | Radius of 90° bend. \[dbu\] | *required* |
| `bend180_radius` | `dbu \| None` | Optional use of 180° bend, distance between two parallel ports. \[dbu\] | `None` |
| `start_straight` | `dbu` | Minimal straight segment after `p1`. | `0` |
| `end_straight` | `dbu` | Minimal straight segment before `p2`. | `0` |
| `d_loop` | `dbu` | Distance of the (vertical) offset of the back of the ports | `200000` |
| `inside` | `bool` | Route the loopback inside the array or outside | `False` |

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `points` | `list[Point]` | List of the calculated points (starting/ending at p1/p2). |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If the ports are not parallel or point in the same direction. |

## vec\_angle

```
vec_angle(v: Vector) -> int
```

Determine vector angle in increments of 90°.

Returns:

| Type | Description |
| --- | --- |
| `int` | The angle of the vector in increments of 90° (0, 1, 2, 3). |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | If the vector is not a manhattan vector. |

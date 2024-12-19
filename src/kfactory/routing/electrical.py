"""Utilities for automatically routing electrical connections."""

from collections.abc import Callable, Sequence
from typing import Any, Literal

from .. import kdb
from ..conf import logger
from ..kcell import KCell, Port
from ..kf_types import dbu
from .generic import ManhattanRoute
from .generic import route_bundle as route_bundle_generic
from .manhattan import ManhattanRoutePathFunction, route_manhattan, route_smart
from .steps import Step, Straight

__all__ = [
    "route_elec",
    "route_L",
    "route_bundle",
    "route_bundle_dual_rails",
    "route_dual_rails",
    "place_single_wire",
    "place_dual_rails",
]


def route_elec(
    c: KCell,
    p1: Port,
    p2: Port,
    start_straight: int | None = None,
    end_straight: int | None = None,
    route_path_function: ManhattanRoutePathFunction = route_manhattan,
    width: dbu | None = None,
    layer: int | None = None,
    minimum_straight: int | None = None,
) -> None:
    """Connect two ports with a wire.

    A wire is a path object on a usually metal layer.


    Args:
        c: KCell to place the wire in.
        p1: Beginning
        p2: End
        start_straight: Minimum length of straight at start port.
        end_straight: Minimum length of straight at end port.
        route_path_function: Function to calculate the path. Signature:
            `route_path_function(p1, p2, bend90_radius, start_straight,
            end_straight)`
        width: Overwrite the width of the wire. Calculated by the width of the start
            port if `None`.
        layer: Layer to place the wire on. Calculated from the start port if `None`.
        minimum_straight: require a minimum straight
    """
    if width is None:
        width = p1.width
    if layer is None:
        layer = p1.layer
    if start_straight is None:
        start_straight = round(width / 2)
    if end_straight is None:
        end_straight = round(width / 2)

    if minimum_straight is not None:
        start_straight = min(minimum_straight // 2, start_straight)
        end_straight = min(minimum_straight // 2, end_straight)

        pts = route_path_function(
            p1.copy(),
            p2.copy(),
            bend90_radius=minimum_straight,
            start_steps=[Straight(dist=start_straight)],
            end_steps=[Straight(dist=end_straight)],
        )
    else:
        pts = route_path_function(
            p1.copy(),
            p2.copy(),
            bend90_radius=0,
            start_steps=[Straight(dist=start_straight)],
            end_steps=[Straight(dist=end_straight)],
        )

    path = kdb.Path(pts, width)
    c.shapes(layer).insert(path.polygon())


def route_L(
    c: KCell,
    input_ports: list[Port],
    output_orientation: int = 1,
    wire_spacing: dbu = 10000,
) -> list[Port]:
    """Route ports towards a bundle in an L shape.

    This function takes a list of input ports and assume they are oriented in the west.
    The output will be a list of ports that have the same y coordinates.
    The function will produce a L-shape routing to connect input ports to output ports
    without any crossings.
    """
    input_ports.sort(key=lambda p: p.y)

    y_max = input_ports[-1].y
    y_min = input_ports[0].y
    x_max = max(p.x for p in input_ports)

    output_ports = []
    if output_orientation == 1:
        for i, p in enumerate(input_ports[::-1]):
            temp_port = p.copy()
            temp_port.trans = kdb.Trans(
                3, False, x_max - wire_spacing * (i + 1), y_max + wire_spacing
            )

            route_elec(c, p, temp_port)
            temp_port.trans.angle = 1
            output_ports.append(temp_port)
    elif output_orientation == 3:
        for i, p in enumerate(input_ports):
            temp_port = p.copy()
            temp_port.trans = kdb.Trans(
                1, False, x_max - wire_spacing * (i + 1), y_min - wire_spacing
            )
            route_elec(c, p, temp_port)
            temp_port.trans.angle = 3
            output_ports.append(temp_port)
    else:
        raise ValueError(
            "Invalid L-shape routing. Please change output_orientaion to 1 or 3."
        )
    return output_ports


def route_bundle(
    c: KCell,
    start_ports: list[Port],
    end_ports: list[Port],
    separation: dbu,
    start_straights: dbu | list[dbu] = 0,
    end_straights: dbu | list[dbu] = 0,
    place_layer: kdb.LayerInfo | None = None,
    route_width: dbu | None = None,
    bboxes: list[kdb.Box] = [],
    bbox_routing: Literal["minimal", "full"] = "minimal",
    sort_ports: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    waypoints: kdb.Trans | list[kdb.Point] | None = None,
    starts: dbu | list[dbu] | list[Step] | list[list[Step]] = [],
    ends: dbu | list[dbu] | list[Step] | list[list[Step]] = [],
    start_angles: int | list[int] | None = None,
    end_angles: int | list[int] | None = None,
) -> list[ManhattanRoute]:
    r"""Connect multiple input ports to output ports.

    This function takes a list of input ports and assume they are all oriented in the
    same direction (could be any of W, S, E, N). The target ports have the opposite
    orientation, i.e. if input ports are oriented to north, and target ports should
    be oriented to south. The function will produce a routing to connect input ports
    to output ports without any crossings.

    Waypoints will create a front which will create ports in a 1D array. If waypoints
    are a transformation it will be like a point with a direction. If multiple points
    are passed, the direction will be invfered.
    For orientation of 0 degrees it will create the following front for 4 ports:

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

    Args:
        c: KCell to place the routes in.
        start_ports: List of start ports.
        end_ports: List of end ports.
        separation: Minimum space between wires. [dbu]
        starts: Minimal straight segment after `start_ports`.
        ends: Minimal straight segment before `end_ports`.
        start_straights: Deprecated, use starts instead.
        end_straights: Deprecated, use ends instead.
        place_layer: Override automatic detection of layers with specific layer.
        route_width: Width of the route. If None, the width of the ports is used.
        bboxes: List of boxes to consider. Currently only boxes overlapping ports will
            be considered.
        bbox_routing: "minimal": only route to the bbox so that it can be safely routed
            around, but start or end bends might encroach on the bounding boxes when
            leaving them.
        sort_ports: Automatically sort ports.
        collision_check_layers: Layers to check for actual errors if manhattan routes
            detect potential collisions.
        on_collision: Define what to do on routing collision. Default behaviour is to
            open send the layout of c to klive and open an error lyrdb with the
            collisions. "error" will simply raise an error. None will ignore any error.
        on_placer_error: If a placing of the components fails, use the strategy above to
            handle the error. show_error will visualize it in klayout with the intended
            route along the already placed parts of c. Error will just throw an error.
            None will ignore the error.
        waypoints: Bundle the ports and route them with minimal separation through
            the waypoints. The waypoints can either be a list of at least two points
            or a single transformation. If it's a transformation, the points will be
            routed through it as if it were a tunnel with length 0.
        start_angles: Overwrite the port orientation of all start_ports together
            (single value) or each one (list of values which is as long as start_ports).
        end_angles: Overwrite the port orientation of all start_ports together
            (single value) or each one (list of values which is as long as end_ports).
            If no waypoints are set, the target angles of all ends muts be the same
            (after the steps).
    """
    return route_bundle_generic(
        c=c,
        start_ports=start_ports,
        end_ports=end_ports,
        starts=starts,
        ends=ends,
        routing_function=route_smart,
        routing_kwargs={
            "separation": separation,
            "sort_ports": sort_ports,
            "bbox_routing": bbox_routing,
            "bboxes": list(bboxes),
            "bend90_radius": 0,
            "waypoints": waypoints,
        },
        placer_function=place_single_wire,
        placer_kwargs={
            "route_width": route_width,
        },
        sort_ports=sort_ports,
        on_collision=on_collision,
        on_placer_error=on_placer_error,
        collision_check_layers=collision_check_layers,
        start_angles=start_angles,
        end_angles=end_angles,
    )


def route_bundle_dual_rails(
    c: KCell,
    start_ports: list[Port],
    end_ports: list[Port],
    separation: dbu,
    start_straights: dbu | list[dbu] | None = None,
    end_straights: dbu | list[dbu] | None = None,
    place_layer: kdb.LayerInfo | None = None,
    width_rails: dbu | None = None,
    separation_rails: dbu | None = None,
    bboxes: list[kdb.Box] = [],
    bbox_routing: Literal["minimal", "full"] = "minimal",
    sort_ports: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    waypoints: kdb.Trans | list[kdb.Point] | None = None,
    starts: dbu | list[dbu] | list[Step] | list[list[Step]] = [],
    ends: dbu | list[dbu] | list[Step] | list[list[Step]] = [],
    start_angles: int | list[int] | None = None,
    end_angles: int | list[int] | None = None,
) -> list[ManhattanRoute]:
    r"""Connect multiple input ports to output ports.

    This function takes a list of input ports and assume they are all oriented in the
    same direction (could be any of W, S, E, N). The target ports have the opposite
    orientation, i.e. if input ports are oriented to north, and target ports should
    be oriented to south. The function will produce a routing to connect input ports
    to output ports without any crossings.

    Waypoints will create a front which will create ports in a 1D array. If waypoints
    are a transformation it will be like a point with a direction. If multiple points
    are passed, the direction will be invfered.
    For orientation of 0 degrees it will create the following front for 4 ports:

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

    Args:
        c: KCell to place the routes in.
        start_ports: List of start ports.
        end_ports: List of end ports.
        separation: Minimum space between wires. [dbu]
        starts: Minimal straight segment after `start_ports`.
        ends: Minimal straight segment before `end_ports`.
        start_straights: Deprecated, use starts instead.
        end_straights: Deprecated, use ends instead.
        place_layer: Override automatic detection of layers with specific layer.
        width_rails: Total width of the rails.
        separation_rails: Separation between the two rails.
        bboxes: List of boxes to consider. Currently only boxes overlapping ports will
            be considered.
        bbox_routing: "minimal": only route to the bbox so that it can be safely routed
            around, but start or end bends might encroach on the bounding boxes when
            leaving them.
        sort_ports: Automatically sort ports.
        collision_check_layers: Layers to check for actual errors if manhattan routes
            detect potential collisions.
        on_collision: Define what to do on routing collision. Default behaviour is to
            open send the layout of c to klive and open an error lyrdb with the
            collisions. "error" will simply raise an error. None will ignore any error.
        on_placer_error: If a placing of the components fails, use the strategy above to
            handle the error. show_error will visualize it in klayout with the intended
            route along the already placed parts of c. Error will just throw an error.
            None will ignore the error.
        waypoints: Bundle the ports and route them with minimal separation through
            the waypoints. The waypoints can either be a list of at least two points
            or a single transformation. If it's a transformation, the points will be
            routed through it as if it were a tunnel with length 0.
        start_angles: Overwrite the port orientation of all start_ports together
            (single value) or each one (list of values which is as long as start_ports).
        end_angles: Overwrite the port orientation of all start_ports together
            (single value) or each one (list of values which is as long as end_ports).
            If no waypoints are set, the target angles of all ends muts be the same
            (after the steps).
    """
    if start_straights is not None:
        logger.warning("start_straights is deprecated. Use `starts` instead.")
        starts = start_straights
    if end_straights is not None:
        logger.warning("end_straights is deprecated. Use `starts` instead.")
        ends = end_straights
    return route_bundle_generic(
        c=c,
        start_ports=start_ports,
        end_ports=end_ports,
        routing_function=route_smart,
        starts=starts,
        ends=ends,
        routing_kwargs={
            "separation": separation,
            "sort_ports": sort_ports,
            "bbox_routing": bbox_routing,
            "bboxes": list(bboxes),
            "bend90_radius": 0,
            "waypoints": waypoints,
        },
        placer_function=place_dual_rails,
        placer_kwargs={
            "separation_rails": separation_rails,
            "route_width": width_rails,
        },
        sort_ports=sort_ports,
        on_collision=on_collision,
        on_placer_error=on_placer_error,
        collision_check_layers=collision_check_layers,
        start_angles=start_angles,
        end_angles=end_angles,
    )


def route_dual_rails(
    c: KCell,
    p1: Port,
    p2: Port,
    start_straight: dbu | None = None,
    end_straight: dbu | None = None,
    route_path_function: Callable[..., list[kdb.Point]] = route_manhattan,
    width: dbu | None = None,
    hole_width: dbu | None = None,
    layer: int | None = None,
) -> None:
    """Connect ports with a dual-wire rail.

    Args:
        c: KCell to place the connection in.
        p1: Start port.
        p2: End port.
        start_straight: Minimum straight after the start port.
        end_straight: Minimum straight before end port.
        route_path_function: Function to calculate the path. Signature:
            `route_path_function(p1, p2, bend90_radius, start_straight,
            end_straight)`
        width: Width of the rail (total). [dbu]
        hole_width: Width of the space between the rails. [dbu]
        layer: layer to place the rail in.
    """
    _width = width or p1.width
    _hole_width = hole_width or p1.width // 2
    _layer = layer or p1.layer

    pts = route_path_function(
        p1.copy(),
        p2.copy(),
        bend90_radius=0,
        start_straight=start_straight,
        end_straight=end_straight,
    )

    path = kdb.Path(pts, _width)
    hole_path = kdb.Path(pts, _hole_width)
    final_poly = kdb.Region(path.polygon()) - kdb.Region(hole_path.polygon())
    c.shapes(_layer).insert(final_poly)


def place_single_wire(
    c: KCell,
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    route_width: dbu | None = None,
    layer_info: kdb.LayerInfo | None = None,
    **kwargs: Any,
) -> ManhattanRoute:
    """Placer function for a single wire.

    Args:
        c: KCell to place the route in.
        p1: Start port.
        p2: End port.
        pts: Route backbone.
        route_width: Overwrite automatic detection of wire width.
        layer_info: Place on a specific layer. Otherwise, use
            `p1.layer_info`.
        width: Place a route with a specific width. Otherwise, use
            `p2.width`.
        kwargs: Compatibility for type checkers. Throws an error if not empty.
    """
    if layer_info is None:
        layer_info = p1.layer_info
    if route_width is None:
        route_width = p1.width
    if kwargs:
        raise ValueError(
            f"Additional kwargs aren't supported in route_single_wire {kwargs=}"
        )

    shape = (
        c.shapes(c.layer(layer_info))
        .insert(kdb.Path(pts, width=route_width).polygon())
        .polygon
    )

    _length = 0.0
    pt1 = pts[0]
    for pt2 in pts[1:]:
        _length += (pt2 - pt1).length()

    return ManhattanRoute(
        backbone=pts,
        start_port=p1,
        end_port=p2,
        taper_length=0,
        bend90_radius=0,
        polygons={layer_info: [shape]},
        instances=[],
        length=round(_length),
        length_straight=round(_length),
    )


def place_dual_rails(
    c: KCell,
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    route_width: dbu | None = None,
    layer_info: kdb.LayerInfo | None = None,
    separation_rails: dbu | None = None,
    **kwargs: Any,
) -> ManhattanRoute:
    """Placer function for a single wire.

    Args:
        c: KCell to place the route in.
        p1: Start port.
        p2: End port.
        pts: Route backbone.
        route_width: Overwrite automatic detection of wire width.
            Total width of all rails.
        layer_info: Place on a specific layer. Otherwise, use
            `p1.layer_info`.
        width_rails: Total width of the rails.
        separation_rails: Separation between the two rails.
        kwargs: Compatibility for type checkers. Throws an error if not empty.
    """
    if kwargs:
        raise ValueError(
            f"Additional kwargs aren't supported in route_dual_rails {kwargs=}"
        )
    if layer_info is None:
        layer_info = p1.layer_info
    if route_width is None:
        route_width = p1.width
    if separation_rails is None:
        raise ValueError("Must specify a separation between the two rails.")
    if separation_rails >= route_width:
        raise ValueError(f"{separation_rails=} must be smaller than the {route_width}")

    region = kdb.Region(kdb.Path(pts, route_width)) - kdb.Region(
        kdb.Path(pts, separation_rails)
    )

    shapes = [
        c.shapes(c.layer(layer_info)).insert(region[0]).polygon,
        c.shapes(c.layer(layer_info)).insert(region[1]).polygon,
    ]

    return ManhattanRoute(
        backbone=pts,
        start_port=p1,
        end_port=p2,
        taper_length=0,
        bend90_radius=0,
        polygons={layer_info: shapes},
        instances=[],
    )

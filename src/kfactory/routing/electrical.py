"""Utilities for automatically routing electrical connections."""

from collections.abc import Callable, Sequence
from typing import Any, Literal, Protocol, cast, overload

import klayout.db as kdb
import numpy as np

from ..conf import (
    ANGLE_270,
    MIN_POINTS_FOR_PLACEMENT,
    NUM_PORTS_FOR_ROUTING,
    config,
    logger,
)
from ..cross_section import CrossSection, SymmetricalCrossSection
from ..enclosure import LayerEnclosure
from ..kcell import DKCell, KCell, ProtoTKCell
from ..port import DPort, Port
from ..typings import dbu, um
from .generic import ManhattanRoute
from .generic import route_bundle as route_bundle_generic
from .length_functions import get_length_from_backbone
from .manhattan import (
    ManhattanRoutePathFunction,
    route_manhattan,
    route_smart,
)
from .optical import vec_angle
from .steps import Step, Straight

__all__ = [
    "place_dual_rails",
    "place_single_wire",
    "route_L",
    "route_bundle",
    "route_bundle_dual_rails",
    "route_bundle_rf",
    "route_dual_rails",
    "route_elec",
]


def route_elec(
    c: KCell,
    p1: Port,
    p2: Port,
    start_straight: int | None = None,
    end_straight: int | None = None,
    route_path_function: ManhattanRoutePathFunction = route_manhattan,
    width: int | None = None,
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
    c_ = c.to_itype()
    p1_ = p1.to_itype()
    p2_ = p2.to_itype()
    if width is None:
        width = p1_.width
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
            p1_.copy(),
            p2_.copy(),
            bend90_radius=minimum_straight,
            start_steps=[Straight(dist=start_straight)],
            end_steps=[Straight(dist=end_straight)],
        )
    else:
        pts = route_path_function(
            p1_.copy(),
            p2_.copy(),
            bend90_radius=0,
            start_steps=[Straight(dist=start_straight)],
            end_steps=[Straight(dist=end_straight)],
        )

    path = kdb.Path(pts, width)
    c_.shapes(layer).insert(path.polygon())


def route_L(  # noqa: N802
    c: KCell,
    input_ports: Sequence[Port],
    output_orientation: int = 1,
    wire_spacing: int = 10000,
) -> list[Port]:
    """Route ports towards a bundle in an L shape.

    This function takes a list of input ports and assume they are oriented in the west.
    The output will be a list of ports that have the same y coordinates.
    The function will produce a L-shape routing to connect input ports to output ports
    without any crossings.
    """
    input_ports_ = [p.to_itype() for p in input_ports]
    c_ = c.to_itype()
    input_ports_.sort(key=lambda p: p.y)

    y_max = input_ports_[-1].y
    y_min = input_ports_[0].y
    x_max = max(p.x for p in input_ports_)

    output_ports: list[Port] = []
    if output_orientation == 1:
        for i, p in enumerate(input_ports_[::-1]):
            temp_port = p.copy()
            temp_port.trans = kdb.Trans(
                3, False, x_max - wire_spacing * (i + 1), y_max + wire_spacing
            )

            route_elec(c_, p, temp_port)
            temp_port.trans.angle = 1
            output_ports.append(temp_port)
    elif output_orientation == ANGLE_270:
        for i, p in enumerate(input_ports_):
            temp_port = p.copy()
            temp_port.trans = kdb.Trans(
                1, False, x_max - wire_spacing * (i + 1), y_min - wire_spacing
            )
            route_elec(c_, p, temp_port)
            temp_port.trans.angle = 3
            output_ports.append(temp_port)
    else:
        raise ValueError(
            "Invalid L-shape routing. Please change output_orientaion to 1 or 3."
        )
    return output_ports


@overload
def route_bundle(
    c: KCell,
    start_ports: Sequence[Port],
    end_ports: Sequence[Port],
    separation: dbu,
    start_straights: dbu | list[dbu] = 0,
    end_straights: dbu | list[dbu] = 0,
    place_layer: kdb.LayerInfo | None = None,
    route_width: dbu | list[dbu] | None = None,
    bboxes: Sequence[kdb.Box] | None = None,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    sort_ports: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    waypoints: kdb.Trans | list[kdb.Point] | None = None,
    starts: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None,
    ends: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None,
    start_angles: int | list[int] | None = None,
    end_angles: int | list[int] | None = None,
    purpose: str | None = "routing",
) -> list[ManhattanRoute]: ...


@overload
def route_bundle(
    c: DKCell,
    start_ports: Sequence[DPort],
    end_ports: Sequence[DPort],
    separation: um,
    start_straights: um | list[um] = 0,
    end_straights: um | list[um] = 0,
    place_layer: kdb.LayerInfo | None = None,
    route_width: um | list[um] | None = None,
    bboxes: Sequence[kdb.DBox] | None = None,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    sort_ports: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    waypoints: kdb.DTrans | list[kdb.DPoint] | None = None,
    starts: um | list[um] | list[Step] | list[list[Step]] | None = None,
    ends: um | list[um] | list[Step] | list[list[Step]] | None = None,
    start_angles: float | list[float] | None = None,
    end_angles: float | list[float] | None = None,
    purpose: str | None = "routing",
) -> list[ManhattanRoute]: ...


def route_bundle(
    c: KCell | DKCell,
    start_ports: Sequence[Port] | Sequence[DPort],
    end_ports: Sequence[Port] | Sequence[DPort],
    separation: dbu | um,
    start_straights: dbu | list[dbu] | um | list[um] = 0,
    end_straights: dbu | list[dbu] | um | list[um] = 0,
    place_layer: kdb.LayerInfo | None = None,
    route_width: dbu | um | list[dbu] | list[um] | None = None,
    bboxes: Sequence[kdb.Box] | Sequence[kdb.DBox] | None = None,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    sort_ports: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    waypoints: kdb.Trans
    | list[kdb.Point]
    | kdb.DTrans
    | list[kdb.DPoint]
    | None = None,
    starts: dbu
    | list[dbu]
    | um
    | list[um]
    | list[Step]
    | list[list[Step]]
    | None = None,
    ends: dbu | list[dbu] | um | list[um] | list[Step] | list[list[Step]] | None = None,
    start_angles: list[int] | float | list[float] | None = None,
    end_angles: list[int] | float | list[float] | None = None,
    purpose: str | None = "routing",
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
        purpose: Purpose of the routes. (Unused)
    """
    if ends is None:
        ends = []
    if starts is None:
        starts = []
    if bboxes is None:
        bboxes = []

    if isinstance(c, KCell):
        return route_bundle_generic(
            c=c,
            start_ports=[p.base for p in start_ports],
            end_ports=[p.base for p in end_ports],
            starts=cast("dbu | list[dbu] | list[Step] | list[list[Step]]", starts),
            ends=cast("dbu | list[dbu] | list[Step] | list[list[Step]]", ends),
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
            start_angles=cast("int | list[int] | None", start_angles),
            end_angles=cast("int | list[int]", end_angles),
        )

    if route_width is not None:
        if isinstance(route_width, list):
            route_width = [c.kcl.to_dbu(width) for width in route_width]
        else:
            route_width = c.kcl.to_dbu(route_width)
    angles: dict[int | float, int] = {0: 0, 90: 1, 180: 2, 270: 30}
    if start_angles is not None:
        if isinstance(start_angles, list):
            start_angles = [angles[angle] for angle in start_angles]
        else:
            start_angles = angles[start_angles]
    if end_angles is not None:
        if isinstance(end_angles, list):
            end_angles = [angles[angle] for angle in end_angles]
        else:
            end_angles = angles[end_angles]

    if isinstance(starts, int | float):
        starts = c.kcl.to_dbu(starts)
    elif isinstance(starts, list):
        if isinstance(starts[0], int | float):
            starts = [c.kcl.to_dbu(start) for start in starts]  # type: ignore[arg-type]
        starts = cast("int | list[int] | list[Step] | list[list[Step]]", starts)
    if isinstance(ends, int | float):
        ends = c.kcl.to_dbu(ends)
    elif isinstance(ends, list):
        if isinstance(ends[0], int | float):
            ends = [c.kcl.to_dbu(end) for end in ends]  # type: ignore[arg-type]
        ends = cast("int | list[int] | list[Step] | list[list[Step]]", ends)
    if waypoints is not None:
        if isinstance(waypoints, list):
            waypoints = [
                p.to_itype(c.kcl.dbu) for p in cast("list[kdb.DPoint]", waypoints)
            ]
        else:
            waypoints = cast("kdb.DCplxTrans", waypoints).s_trans().to_itype(c.kcl.dbu)
    return route_bundle_generic(
        c=c.kcl[c.cell_index()],
        start_ports=[p.base for p in start_ports],
        end_ports=[p.base for p in end_ports],
        starts=starts,
        ends=ends,
        routing_function=route_smart,
        routing_kwargs={
            "separation": c.kcl.to_dbu(separation),
            "sort_ports": sort_ports,
            "bbox_routing": bbox_routing,
            "bboxes": [bb.to_itype(c.kcl.dbu) for bb in cast("list[kdb.DBox]", bboxes)],
            "bend90_radius": 0,
            "waypoints": waypoints,
        },
        placer_function=place_single_wire,
        placer_kwargs={
            "route_width": route_width,
            "layer_info": place_layer,
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
    bboxes: list[kdb.Box] | None = None,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    sort_ports: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    waypoints: kdb.Trans | list[kdb.Point] | None = None,
    starts: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None,
    ends: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None,
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
    if ends is None:
        ends = []
    if starts is None:
        starts = []
    if bboxes is None:
        bboxes = []
    if start_straights is not None:
        logger.warning("start_straights is deprecated. Use `starts` instead.")
        starts = start_straights
    if end_straights is not None:
        logger.warning("end_straights is deprecated. Use `starts` instead.")
        ends = end_straights
    return route_bundle_generic(
        c=c,
        start_ports=[p.base for p in start_ports],
        end_ports=[p.base for p in end_ports],
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
            "layer_info": place_layer,
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
    width_ = width or p1.width
    hole_width_ = hole_width or p1.width // 2
    layer_ = layer or p1.layer

    pts = route_path_function(
        p1.copy(),
        p2.copy(),
        bend90_radius=0,
        start_steps=[Straight(dist=start_straight)],
        end_steps=[Straight(dist=end_straight)],
    )

    path = kdb.Path(pts, width_)
    hole_path = kdb.Path(pts, hole_width_)
    final_poly = kdb.Region(path.polygon()) - kdb.Region(hole_path.polygon())
    c.shapes(layer_).insert(final_poly)


def place_single_wire(
    c: KCell,
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    route_width: int | None = None,
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

    length = 0.0
    pt1 = pts[0]
    for pt2 in pts[1:]:
        length += (pt2 - pt1).length()

    return ManhattanRoute(
        backbone=list(pts),
        start_port=p1,
        end_port=p2,
        taper_length=0,
        bend90_radius=0,
        polygons={layer_info: [shape]},
        instances=[],
        length_straights=round(length),
        length_function=get_length_from_backbone,
    )


def place_dual_rails(
    c: KCell,
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    route_width: int | None = None,
    layer_info: kdb.LayerInfo | None = None,
    separation_rails: int | None = None,
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
        backbone=list(pts),
        start_port=p1,
        end_port=p2,
        taper_length=0,
        bend90_radius=0,
        polygons={layer_info: shapes},
        instances=[],
    )


class BendFactory(Protocol):
    def __call__(
        self, *, radius: int, cross_section: CrossSection
    ) -> ProtoTKCell[Any]: ...


class WireFactory(Protocol):
    def __call__(
        self, *, length: int, cross_section: CrossSection
    ) -> ProtoTKCell[Any]: ...


def place_rf_rails(
    c: KCell,
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    route_width: int | None = None,
    *,
    center_trans: kdb.Trans | None = None,
    layer_info: kdb.LayerInfo | None = None,
    enclosure: LayerEnclosure | None = None,
    center_radius: dbu = 0,
    bend_factory: BendFactory | None = None,
    wire_factory: WireFactory | None = None,
    port_type: str = "electrical",
    allow_small_routes: bool = False,
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    purpose: str | None = "routing",
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
        enclosure: Enclosure the placed_rails with an enclosure.
        kwargs: Compatibility for type checkers. Throws an error if not empty.
    """
    if kwargs:
        raise ValueError(
            f"Additional kwargs aren't supported in route_dual_rails {kwargs=}"
        )

    if center_trans is None:
        raise ValueError("For placing rf rails, center_radius must be defined")
    if wire_factory is None:
        raise ValueError("for placing rf rails a wire factory must be supplied")
    if bend_factory is None:
        raise ValueError("for placing rf rails a bend factory must be supplied")

    if len(kwargs) > 0:
        raise ValueError(
            f"Additional args and kwargs are not allowed for route_smart.{kwargs=}"
        )
    if allow_width_mismatch is None:
        allow_width_mismatch = config.allow_width_mismatch
    if allow_layer_mismatch is None:
        allow_layer_mismatch = config.allow_layer_mismatch
    if allow_type_mismatch is None:
        allow_type_mismatch = config.allow_type_mismatch
    if wire_factory is None:
        raise ValueError(
            "place_rf_rails needs to have a wire_factory set. Please pass a "
            "wire_factory which takes kwargs 'width: int' and 'length: int'."
        )
    cross_section = p1.kcl.get_icross_section(
        SymmetricalCrossSection(
            width=p1.width,
            enclosure=enclosure or LayerEnclosure(sections=[], main_layer=layer_info),
        )
    )
    route_start_port = p1.copy()
    route_start_port.name = None
    route_start_port.trans.angle = (route_start_port.angle + 2) % 4
    route_end_port = p2.copy()
    route_end_port.name = None
    route_end_port.trans.angle = (route_end_port.angle + 2) % 4

    old_pt = pts[0]
    old_bend_port = p1

    offset = (center_trans.inverted() * p1.trans).disp.y
    inner_radius = center_radius - abs(offset)
    if inner_radius < 0:
        raise ValueError(
            "Radius for inner turns is below 0. Please increase center radius to get"
            " a radius >= 0."
        )
    outer_radius = center_radius + abs(offset)

    bend90_inner = bend_factory(cross_section=cross_section, radius=inner_radius)
    bend90_outer = bend_factory(cross_section=cross_section, radius=outer_radius)

    bend90_inner_ports = [p for p in bend90_inner.ports if p.port_type == port_type]
    bend90_outer_ports = [p for p in bend90_outer.ports if p.port_type == port_type]

    # test for outer same port names
    bend_outer_ports = [p for p in bend90_outer.ports if p.port_type == port_type]
    for p_in, p_out in zip(bend90_inner_ports, bend_outer_ports, strict=True):
        if not p_in.name == p_out.name:
            raise ValueError(
                "The bend port names and order must be consistent for different radii"
            )
        if not p_in.angle == p_out.angle:
            raise ValueError(
                "The bend port angles must be consistent for different radii"
            )

    if len(bend90_inner_ports) != NUM_PORTS_FOR_ROUTING:
        raise AttributeError(
            f"{bend90_inner.name} should have 2 ports but has "
            f"{len(bend90_inner_ports)} ports"
            f"with {port_type=}"
        )
    if (
        abs((bend90_inner_ports[0].trans.angle - bend90_inner_ports[1].trans.angle) % 4)
        != 1
    ):
        raise AttributeError(
            f"{bend90_inner.name} bend ports should be 90° apart from each other"
        )

    if (
        bend90_inner_ports[1].trans.angle - bend90_inner_ports[0].trans.angle
    ) % 4 == ANGLE_270:
        b90p1_inner = bend90_inner_ports[1]
        b90p2_inner = bend90_inner_ports[0]
    else:
        b90p1_inner = bend90_inner_ports[0]
        b90p2_inner = bend90_inner_ports[1]
    assert b90p1_inner.name is not None, logger.error(
        "bend90 needs named ports, {}", b90p1_inner
    )
    assert b90p2_inner.name is not None, logger.error(
        "bend90 needs named ports, {}", b90p2_inner
    )
    b90c_inner = kdb.Trans(
        b90p1_inner.trans.rot,
        b90p1_inner.trans.is_mirror(),
        b90p1_inner.trans.disp.x
        if b90p1_inner.trans.angle % 2
        else b90p2_inner.trans.disp.x,
        b90p2_inner.trans.disp.y
        if b90p1_inner.trans.angle % 2
        else b90p1_inner.trans.disp.y,
    )
    if (
        bend90_outer_ports[1].trans.angle - bend90_outer_ports[0].trans.angle
    ) % 4 == ANGLE_270:
        b90p1_outer = bend90_outer_ports[1]
        b90p2_outer = bend90_outer_ports[0]
    else:
        b90p1_outer = bend90_outer_ports[0]
        b90p2_outer = bend90_outer_ports[1]
    b90c_outer = kdb.Trans(
        b90p1_outer.trans.rot,
        b90p1_outer.trans.is_mirror(),
        b90p1_outer.trans.disp.x
        if b90p1_outer.trans.angle % 2
        else b90p2_outer.trans.disp.x,
        b90p2_outer.trans.disp.y
        if b90p1_outer.trans.angle % 2
        else b90p1_outer.trans.disp.y,
    )
    b90r_inner = round(
        max(
            (b90p1_inner.trans.disp - b90c_inner.disp).length(),
            (b90p2_inner.trans.disp - b90c_inner.disp).length(),
        )
    )
    b90r_outer = round(
        max(
            (b90p1_outer.trans.disp - b90c_outer.disp).length(),
            (b90p2_outer.trans.disp - b90c_outer.disp).length(),
        )
    )
    route = ManhattanRoute(
        backbone=list(pts).copy(),
        start_port=route_start_port,
        end_port=route_end_port,
        instances=[],
        bend90_radius=center_radius,
        taper_length=0,
    )

    if not pts or len(pts) < MIN_POINTS_FOR_PLACEMENT:
        # Nothing to be placed
        return route

    if len(pts) == MIN_POINTS_FOR_PLACEMENT:
        length = int((pts[1] - pts[0]).length())
        wg = c << wire_factory(
            cross_section=cross_section, length=int((pts[1] - pts[0]).length())
        )
        wg.purpose = purpose
        wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
        wg.connect(
            wg_p1,
            p1,
            allow_width_mismatch=route_width is not None or allow_width_mismatch,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
        )
        route.instances.append(wg)
        route.start_port = Port(base=wg_p1.base.transformed())
        route.start_port.name = None
        route.length_straights += int(length)
        return route
    for i in range(1, len(pts) - 1):
        pt = pts[i]
        new_pt = pts[i + 1]

        if (pt.distance(old_pt) < b90r_inner) and not allow_small_routes:
            raise ValueError(
                f"distance between points {old_pt!s} and {pt!s} is too small to"
                f" safely place bends {pt.to_s()=}, {old_pt.to_s()=},"
                f" {pt.distance(old_pt)=} < {b90r_inner=}"
            )
        if (
            pt.distance(old_pt) < b90r_inner + b90r_outer
            and i not in {1, len(pts) - 1}
            and not allow_small_routes
        ):
            raise ValueError(
                f"distance between points {old_pt!s} and {pt!s} is too small to"
                f" safely place bends {pt=!s}, {old_pt=!s},"
                f" {pt.distance(old_pt)=} < {b90r_inner + b90r_outer=}"
            )

        vec = pt - old_pt
        vec_n = new_pt - pt
        old_angle = vec_angle(vec)
        angle = vec_angle(vec_n)

        sign = int(np.sign(offset)) or 1

        d_angle = (sign * (angle - old_angle)) % 4
        if d_angle == 1:
            bend90 = c << bend_factory(cross_section=cross_section, radius=inner_radius)
            b90c = b90c_inner
        elif d_angle == 3:  # noqa: PLR2004
            bend90 = c << bend_factory(cross_section=cross_section, radius=outer_radius)
            b90c = b90c_outer
        else:
            raise ValueError(
                "Points are not clean. Make sure to clean the points before supplying "
                "them to the multi rail placer"
            )

        bend90.purpose = purpose
        route.n_bend90 += 1
        mirror = (vec_angle(vec_n) - vec_angle(vec)) % 4 != ANGLE_270
        if (vec.y != 0) and (vec.x != 0):
            raise ValueError(
                f"The vector between manhattan points is not manhattan {old_pt}, {pt}"
            )
        ang = (vec_angle(vec) + 2) % 4
        if ang is None:
            raise ValueError(
                f"The vector between manhattan points is not manhattan {old_pt}, {pt}"
            )
        bend90.transform(kdb.Trans(ang, mirror, pt.x, pt.y) * b90c.inverted())
        length = int(
            (
                bend90.ports[b90p1_inner.name].trans.disp - old_bend_port.trans.disp
            ).length()
        )
        if length > 0:
            wg = c << wire_factory(cross_section=cross_section, length=length)
            wg.purpose = purpose
            wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
            wg.connect(
                wg_p1,
                bend90,
                b90p1_inner.name,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
            route.instances.append(wg)
            route.length_straights += int(length)
        route.instances.append(bend90)
        old_pt = pt
        old_bend_port = bend90.ports[b90p2_inner.name]
    length = int((bend90.ports[b90p2_inner.name].trans.disp - p2.trans.disp).length())
    if length > 0:
        wg = c << wire_factory(cross_section=cross_section, length=length)
        wg.purpose = purpose
        wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
        wg.connect(
            wg_p1.name,
            bend90,
            b90p2_inner.name,
            allow_width_mismatch=allow_width_mismatch,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
        )
        route.instances.append(wg)
        route.end_port = wg.ports[wg_p2.name].copy()
        route.end_port.name = None
        route.length_straights += int(length)

    else:
        route.end_port = old_bend_port.copy()
        route.end_port.name = None
    return route


def route_bundle_rf(
    c: KCell,
    start_ports: Sequence[Port] | Sequence[DPort],
    end_ports: Sequence[Port] | Sequence[DPort],
    wire_factory: WireFactory,
    bend_factory: BendFactory,
    place_port_type: str = "electrical",
    place_allow_small_routes: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    sort_ports: bool = False,
    waypoints: kdb.Trans
    | list[kdb.Point]
    | kdb.DCplxTrans
    | list[kdb.DPoint]
    | None = None,
    starts: dbu
    | list[dbu]
    | um
    | list[um]
    | list[Step]
    | list[list[Step]]
    | None = None,
    ends: dbu | list[dbu] | um | list[um] | list[Step] | list[list[Step]] | None = None,
    start_angles: list[int] | float | list[float] | None = None,
    end_angles: list[int] | float | list[float] | None = None,
    purpose: str | None = "routing",
    minimum_radius: int = 0,
    *,
    layer: kdb.LayerInfo,
    enclosure: LayerEnclosure | None = None,
    bboxes: list[kdb.Box] | None = None,
) -> list[ManhattanRoute]:
    r"""Route a bundle from starting ports to end_ports.

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
        c: Cell to place the route in.
        start_ports: List of start ports.
        end_ports: List of end ports.
        separation: Separation between the routes.
        straight_factory: Factory function for straight cells. in DBU.
        bend90_cell: 90° bend cell.
        taper_cell: Taper cell.
        start_straights: DEPRECATED[Use starts instead]
            `p1`.
        end_straights: DEPRECATED[Use ends instead]
            `p2`.
        starts: Minimal straight segment after `start_ports`.
        ends: Minimal straight segment before `end_ports`.
        min_straight_taper: Minimum straight [dbu] before attempting to place tapers.
        place_port_type: Port type to use for the bend90_cell.
        place_allow_small_routes: Don't throw an error if two corners cannot be placed.
        collision_check_layers: Layers to check for actual errors if manhattan routes
            detect potential collisions.
        on_collision: Define what to do on routing collision. Default behaviour is to
            open send the layout of c to klive and open an error lyrdb with the
            collisions. "error" will simply raise an error. None will ignore any error.
        on_placer_error: If a placing of the components fails, use the strategy above to
            handle the error. show_error will visualize it in klayout with the intended
            route along the already placed parts of c. Error will just throw an error.
            None will ignore the error.
        bboxes: List of boxes to consider. Currently only boxes overlapping ports will
            be considered.
        allow_width_mismatch: If True, the width of the ports is ignored
            (config default: False).
        allow_layer_mismatch: If True, the layer of the ports is ignored
            (config default: False).
        allow_type_mismatch: If True, the type of the ports is ignored
            (config default: False).
        route_width: Width of the route. If None, the width of the ports is used.
        sort_ports: Automatically sort ports.
        bbox_routing: "minimal": only route to the bbox so that it can be safely routed
            around, but start or end bends might encroach on the bounding boxes when
            leaving them.
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
        purpose: Set the property "purpose" (at id kf.kcell.PROPID.PURPOSE) to the
            value. Not set if None.

    Returns:
        list[ManhattanRoute]: The route object with the placed components.
    """
    p1 = Port(base=start_ports[0].base)
    port_angle = p1.angle

    for port in start_ports[1:]:
        if not port.angle == port_angle:
            raise ValueError(
                "All ports must have the same orientation and separation between their "
                f"core material Orientations: {[p.orientation for p in start_ports]}"
            )
    separation = 0
    if len(start_ports) > 1:
        p2 = Port(base=start_ports[1].base)
        separation = (
            round(p2.trans.disp.to_p().distance(p1.trans.disp.to_p()))
            - (p1.width + p2.width) // 2
        )

    points = [
        p1.trans.inverted() * Port(base=port.base).trans.disp.to_p()
        for port in start_ports
    ]
    min_ = min(points, key=lambda p: p.y)
    max_ = max(points, key=lambda p: p.y)

    center_radius = abs(max_.y - min_.y) // 2 + minimum_radius
    bboxes = bboxes or []
    if ends is None:
        ends = []
    if starts is None:
        starts = []

    start_ports_ = [p.base for p in start_ports]
    end_ports_ = [p.base for p in end_ports]

    p1t = p1.trans
    u = kdb.Vector()
    for p in start_ports:
        u += p.trans.disp
    u /= len(start_ports)
    center_trans = kdb.Trans(rot=p1t.angle, mirrx=p1t.mirror, x=u.x, y=u.y)

    return route_bundle_generic(
        c=c,
        start_ports=start_ports_,
        end_ports=end_ports_,
        starts=cast("dbu | list[dbu] | list[Step] | list[list[Step]]", starts),
        ends=cast("dbu | list[dbu] | list[Step] | list[list[Step]]", ends),
        route_width=None,
        sort_ports=sort_ports,
        on_collision=on_collision,
        on_placer_error=on_placer_error,
        collision_check_layers=collision_check_layers,
        routing_function=route_smart,
        routing_kwargs={
            "bend90_radius": center_radius,
            "separation": separation,
            "sort_ports": sort_ports,
            "bbox_routing": "minimal",
            "bboxes": list(bboxes),
            "waypoints": waypoints,
        },
        placer_function=place_rf_rails,
        placer_kwargs={
            "center_trans": center_trans,
            "layer_info": layer,
            "enclosure": enclosure,
            "center_radius": center_radius,
            "bend_factory": bend_factory,
            "wire_factory": wire_factory,
            "port_type": "electrical",
            "route_width": None,
            "allow_small_routes": False,
            "allow_width_mismatch": None,
            "allow_layer_mismatch": None,
            "allow_type_mismatch": None,
            "purpose": purpose,
        },
        start_angles=cast("list[int] | int", start_angles),
        end_angles=cast("list[int] | int", end_angles),
    )

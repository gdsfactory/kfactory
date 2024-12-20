"""Optical routing allows the creation of photonic (or any route using bends)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from .. import kdb
from ..conf import config, logger
from ..factories import StraightFactory
from ..kcell import KCell, Port
from ..kf_types import dbu
from .generic import (
    ManhattanRoute,
    get_radius,
)
from .generic import (
    route_bundle as route_bundle_generic,
)
from .manhattan import (
    # ManhattanBundleRoutingFunction,
    ManhattanRoutePathFunction,
    route_manhattan,
    route_smart,
)
from .steps import Step, Straight

__all__ = [
    "get_radius",
    "place90",
    "route_loopback",
    "route",
    "route_bundle",
    "vec_angle",
]


def route_bundle(
    c: KCell,
    start_ports: list[Port],
    end_ports: list[Port],
    separation: dbu,
    straight_factory: StraightFactory,
    bend90_cell: KCell,
    taper_cell: KCell | None = None,
    start_straights: dbu | list[dbu] | None = None,
    end_straights: dbu | list[dbu] | None = None,
    min_straight_taper: dbu = 0,
    place_port_type: str = "optical",
    place_allow_small_routes: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    bboxes: list[kdb.Box] = [],
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    route_width: dbu | list[dbu] | None = None,
    sort_ports: bool = False,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    waypoints: kdb.Trans | list[kdb.Point] | None = None,
    starts: dbu | list[dbu] | list[Step] | list[list[Step]] = [],
    ends: dbu | list[dbu] | list[Step] | list[list[Step]] = [],
    start_angles: int | list[int] | None = None,
    end_angles: int | list[int] | None = None,
    purpose: str | None = "routing",
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
    """
    if start_straights is not None:
        logger.warning("start_straights is deprecated. Use `starts` instead.")
        starts = start_straights
    if end_straights is not None:
        logger.warning("end_straights is deprecated. Use `ends` instead.")
        ends = end_straights
    bend90_radius = get_radius(bend90_cell.ports.filter(port_type=place_port_type))
    return route_bundle_generic(
        c=c,
        start_ports=start_ports,
        end_ports=end_ports,
        starts=starts,
        ends=ends,
        route_width=route_width,
        sort_ports=sort_ports,
        on_collision=on_collision,
        on_placer_error=on_placer_error,
        collision_check_layers=collision_check_layers,
        routing_function=route_smart,
        routing_kwargs={
            "bend90_radius": bend90_radius,
            "separation": separation,
            "sort_ports": sort_ports,
            "bbox_routing": bbox_routing,
            "bboxes": list(bboxes),
            "waypoints": waypoints,
        },
        placer_function=place90,
        placer_kwargs={
            "straight_factory": straight_factory,
            "bend90_cell": bend90_cell,
            "taper_cell": taper_cell,
            "port_type": place_port_type,
            "min_straight_taper": min_straight_taper,
            "allow_small_routes": False,
            "allow_width_mismatch": allow_width_mismatch,
            "allow_layer_mismatch": allow_width_mismatch,
            "allow_type_mismatch": allow_type_mismatch,
            "purpose": purpose,
        },
        start_angles=start_angles,
        end_angles=end_angles,
    )


def place90(
    c: KCell,
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    route_width: dbu | None = None,
    straight_factory: StraightFactory | None = None,
    bend90_cell: KCell | None = None,
    taper_cell: KCell | None = None,
    port_type: str = "optical",
    min_straight_taper: dbu = 0,
    allow_small_routes: bool = False,
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    purpose: str | None = "routing",
    **kwargs: Any,
) -> ManhattanRoute:
    """Place bends and straight waveguides based on a sequence of points.

    This version will not take any non-90° bends. If the taper is not `None`, tapers
    will be added to straights that fulfill the minimum length.

    This function will throw an error in case it cannot place bends due to too small
    routings, E.g. two corner are too close for two bends to be safely placed.


    Args:
        c: Cell in which the route should be placed.
        p1: Start port.
        p2: End port.
        pts: The points
        straight_factory: A function which takes two keyword arguments `width`
            and `length`. It returns a :py:class:~`KCell` with two named ports with
            port_type `port_type` and matching layer as the `bend90_cell` ports.
        bend90_cell: Bend to use in corners of the `pts`. Must have two named ports on
            `port_type`
        taper_cell: Optional taper cell to use if straights and bends should have a
            different width on the connection layer. Must have two named ports on
            `port_type` and share the port layer with `bend90_cell` and
            `straight_factory`.
        port_type: Filter the port type by this to e.g. ignore potential electrical
            ports.
        min_straight_taper: Do not put tapers on a straight if its length
            is below this minimum length.
        allow_small_routes: Don't throw an error if two corners cannot be safely placed
            due to small space and place them anyway.
        allow_width_mismatch: If True, the width of the ports is ignored
            (config default: False).
        allow_layer_mismatch: If True, the layer of the ports is ignored
            (config default: False).
        allow_type_mismatch: If True, the type of the ports is ignored
            (config default: False).
        route_width: Width of the route. If None, the width of the ports is used.
        purpose: Set the property "purpose" (at id kf.kcell.PROPID.PURPOSE) to the
            value. Not set if None.
        args: Additional args. Compatibility for type checking. If any args are passed
            an error is raised.
        kwargs: Additional kwargs. Compatibility for type checking. If any kwargs are
            passed an error is raised.
    """
    if len(kwargs) > 0:
        raise ValueError(
            "Additional args and kwargs are not allowed for route_smart." f"{kwargs=}"
        )
    if allow_width_mismatch is None:
        allow_width_mismatch = config.allow_width_mismatch
    if allow_layer_mismatch is None:
        allow_layer_mismatch = config.allow_layer_mismatch
    if allow_type_mismatch is None:
        allow_type_mismatch = config.allow_type_mismatch
    if straight_factory is None:
        raise ValueError(
            "place90 needs to have a straight_factory set. Please pass a "
            "straight_factory which takes kwargs 'width: int' and 'length: int'."
        )
    if bend90_cell is None:
        raise ValueError(
            "place90 needs to be passed a fixed bend90 cell with two optical"
            " ports which are 90° apart from each other with port_type 'port_type'."
        )
    route_start_port = p1.copy()
    route_start_port.name = None
    route_start_port.trans.angle = (route_start_port.angle + 2) % 4
    route_end_port = p2.copy()
    route_end_port.name = None
    route_end_port.trans.angle = (route_end_port.angle + 2) % 4

    w = route_width or p1.width
    old_pt = pts[0]
    old_bend_port = p1
    bend90_ports = [p for p in bend90_cell.ports if p.port_type == port_type]

    if len(bend90_ports) != 2:
        raise AttributeError(
            f"{bend90_cell.name} should have 2 ports but has {len(bend90_ports)} ports"
            f"with {port_type=}"
        )
    if abs((bend90_ports[0].trans.angle - bend90_ports[1].trans.angle) % 4) != 1:
        raise AttributeError(
            f"{bend90_cell.name} bend ports should be 90° apart from each other"
        )

    if (bend90_ports[1].trans.angle - bend90_ports[0].trans.angle) % 4 == 3:
        b90p1 = bend90_ports[1]
        b90p2 = bend90_ports[0]
    else:
        b90p1 = bend90_ports[0]
        b90p2 = bend90_ports[1]
    assert b90p1.name is not None, logger.error(
        "bend90_cell needs named ports, {}", b90p1
    )
    assert b90p2.name is not None, logger.error(
        "bend90_cell needs named ports, {}", b90p2
    )
    b90c = kdb.Trans(
        b90p1.trans.rot,
        b90p1.trans.is_mirror(),
        b90p1.trans.disp.x if b90p1.trans.angle % 2 else b90p2.trans.disp.x,
        b90p2.trans.disp.y if b90p1.trans.angle % 2 else b90p1.trans.disp.y,
    )
    b90r = max(
        (b90p1.trans.disp - b90c.disp).length(), (b90p2.trans.disp - b90c.disp).length()
    )
    if taper_cell is not None:
        taper_ports = [p for p in taper_cell.ports if p.port_type == "optical"]
        if (
            len(taper_ports) != 2
            or (taper_ports[1].trans.angle + 2) % 4 != taper_ports[0].trans.angle
        ):
            raise AttributeError(
                "Taper must have only two optical ports that are 180° oriented to each"
                " other"
            )
        if taper_ports[1].width == b90p1.width:
            taperp2, taperp1 = taper_ports
        elif taper_ports[0].width == b90p1.width:
            taperp1, taperp2 = taper_ports
        else:
            raise AttributeError(
                "At least one of the taper's optical ports must be the same width as"
                " the bend's ports"
            )
        route = ManhattanRoute(
            backbone=list(pts).copy(),
            start_port=route_start_port,
            end_port=route_end_port,
            instances=[],
            bend90_radius=b90r,
            taper_length=int((taperp1.trans.disp - taperp2.trans.disp).length()),
        )
    else:
        route = ManhattanRoute(
            backbone=list(pts).copy(),
            start_port=route_start_port,
            end_port=route_end_port,
            instances=[],
            bend90_radius=b90r,
            taper_length=0,
        )

    if not pts or len(pts) < 2:
        # Nothing to be placed
        return route

    if len(pts) == 2:
        length = int((pts[1] - pts[0]).length())
        route.length += int(length)
        if (
            taper_cell is None
            or length
            < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
            + min_straight_taper
        ):
            wg = c << straight_factory(width=w, length=int((pts[1] - pts[0]).length()))
            wg.purpose = purpose
            wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
            wg.connect(
                wg_p1,
                p1,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
            route.instances.append(wg)
            route.start_port = wg_p1.copy()
            route.start_port.name = None
            route.length_straights += int(length)
        else:
            t1 = c << taper_cell
            t1.purpose = purpose
            t1.connect(
                taperp1.name,
                p1,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
            route.instances.append(t1)
            route.start_port = t1.ports[taperp1.name].copy()
            route.start_port.name = None
            _l = int(length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2)
            if _l != 0:
                wg = c << straight_factory(
                    width=taperp2.width,
                    length=length
                    - int((taperp1.trans.disp - taperp2.trans.disp).length() * 2),
                )
                wg.purpose = purpose
                wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                wg.connect(
                    wg_p1,
                    t1,
                    taperp2.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
                route.instances.append(wg)
                t2 = c << taper_cell
                t2.purpose = purpose
                t2.connect(
                    taperp2.name,
                    wg_p2,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
                route.length_straights += _l
                route.n_taper += 2
            else:
                t2 = c << taper_cell
                t2.purpose = purpose
                t2.connect(
                    taperp2.name,
                    t1,
                    taperp2.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            route.instances.append(t2)
            route.end_port = t2.ports[taperp1.name]
        return route
    for i in range(1, len(pts) - 1):
        pt = pts[i]
        new_pt = pts[i + 1]

        if (pt.distance(old_pt) < b90r) and not allow_small_routes:
            raise ValueError(
                f"distance between points {str(old_pt)} and {str(pt)} is too small to"
                f" safely place bends {pt.to_s()=}, {old_pt.to_s()=},"
                f" {pt.distance(old_pt)=} < {b90r=}"
            )
        elif (
            pt.distance(old_pt) < 2 * b90r
            and i not in [1, len(pts) - 1]
            and not allow_small_routes
        ):
            raise ValueError(
                f"distance between points {str(old_pt)} and {str(pt)} is too small to"
                f" safely place bends {str(pt)=}, {str(old_pt)=},"
                f" {pt.distance(old_pt)=} < {2 * b90r=}"
            )

        vec = pt - old_pt
        vec_n = new_pt - pt

        bend90 = c << bend90_cell
        bend90.purpose = purpose
        route.n_bend90 += 1
        mirror = (vec_angle(vec_n) - vec_angle(vec)) % 4 != 3
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
            (bend90.ports[b90p1.name].trans.disp - old_bend_port.trans.disp).length()
        )
        route.length += int(length)
        if length > 0:
            if (
                taper_cell is None
                or length
                < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                + min_straight_taper
            ):
                wg = c << straight_factory(width=w, length=length)
                wg.purpose = purpose
                wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                wg.connect(
                    wg_p1,
                    bend90,
                    b90p1.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
                route.instances.append(wg)
                route.length_straights += int(length)
            else:
                t1 = c << taper_cell
                t1.purpose = purpose
                t1.connect(
                    taperp1.name,
                    bend90,
                    b90p1.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
                route.instances.append(t1)
                _l = int(
                    length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                )
                if length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2 != 0:
                    wg = c << straight_factory(
                        width=taperp2.width,
                        length=int(
                            length
                            - (taperp1.trans.disp - taperp2.trans.disp).length() * 2,
                        ),
                    )
                    wg.purpose = purpose
                    wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                    wg.connect(
                        wg_p1.name,
                        t1,
                        taperp2.name,
                        allow_width_mismatch=allow_width_mismatch,
                        allow_layer_mismatch=allow_layer_mismatch,
                        allow_type_mismatch=allow_type_mismatch,
                    )
                    route.instances.append(wg)
                    t2 = c << taper_cell
                    t2.purpose = purpose
                    t2.connect(
                        taperp2.name,
                        wg,
                        wg_p2.name,
                        allow_width_mismatch=allow_width_mismatch,
                        allow_layer_mismatch=allow_layer_mismatch,
                        allow_type_mismatch=allow_type_mismatch,
                    )
                    route.length_straights += _l
                else:
                    t2 = c << taper_cell
                    t2.purpose = purpose
                    t2.connect(
                        taperp2.name,
                        t1,
                        taperp2.name,
                        allow_width_mismatch=allow_width_mismatch,
                        allow_layer_mismatch=allow_layer_mismatch,
                        allow_type_mismatch=allow_type_mismatch,
                    )
                route.n_taper += 2
                route.instances.append(t2)
        route.instances.append(bend90)
        old_pt = pt
        old_bend_port = bend90.ports[b90p2.name]
    length = int((bend90.ports[b90p2.name].trans.disp - p2.trans.disp).length())
    route.length += int(length)
    if length > 0:
        if (
            taper_cell is None
            or length
            < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
            + min_straight_taper
        ):
            wg = c << straight_factory(width=w, length=length)
            wg.purpose = purpose
            wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
            wg.connect(
                wg_p1.name,
                bend90,
                b90p2.name,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
            route.instances.append(wg)
            route.end_port = wg.ports[wg_p2.name].copy()
            route.end_port.name = None
            route.length_straights += int(length)
        else:
            t1 = c << taper_cell
            t1.purpose = purpose
            t1.connect(
                taperp1.name,
                bend90,
                b90p2.name,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
            route.instances.append(t1)
            if length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2 != 0:
                _l = int(
                    length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                )
                wg = c << straight_factory(
                    width=taperp2.width,
                    length=_l,
                )
                wg.purpose = purpose
                route.instances.append(wg)
                wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                wg.connect(
                    wg_p1.name,
                    t1,
                    taperp2.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
                t2 = c << taper_cell
                t2.purpose = purpose
                t2.connect(
                    taperp2.name,
                    wg,
                    wg_p2.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
                route.length_straights += int(_l)
            else:
                t2 = c << taper_cell
                t2.purpose = purpose
                t2.connect(
                    taperp2.name,
                    t1,
                    taperp2.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            route.n_taper += 2
            route.instances.append(t2)
            route.end_port = t2.ports[taperp1.name].copy()
            route.end_port.name = None
    else:
        route.end_port = old_bend_port.copy()
        route.end_port.name = None
    return route


def route_loopback(
    port1: Port | kdb.Trans,
    port2: Port | kdb.Trans,
    bend90_radius: dbu,
    bend180_radius: dbu | None = None,
    start_straight: dbu = 0,
    end_straight: dbu = 0,
    d_loop: dbu = 200000,
    inside: bool = False,
) -> list[kdb.Point]:
    r"""Create a loopback on two parallel ports.

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


    Args:
        port1: Start port.
        port2: End port.
        bend90_radius: Radius of 90° bend. [dbu]
        bend180_radius: Optional use of 180° bend, distance between two parallel ports.
            [dbu]
        start_straight: Minimal straight segment after `p1`.
        end_straight: Minimal straight segment before `p2`.
        d_loop: Distance of the (vertical) offset of the back of the ports
        inside: Route the loopback inside the array or outside

    Returns:
        points: List of the calculated points (starting/ending at p1/p2).
    """
    t1 = port1 if isinstance(port1, kdb.Trans) else port1.trans
    t2 = port2 if isinstance(port2, kdb.Trans) else port2.trans

    if (t1.angle != t2.angle) and (
        (t1.disp.x == t2.disp.x) or (t1.disp.y == t2.disp.y)
    ):
        raise ValueError(
            "for a standard loopback the ports must point in the same direction and"
            "have to be parallel"
        )

    pz = kdb.Point(0, 0)

    if (
        start_straight > 0
        and bend180_radius is None
        or start_straight <= 0
        and bend180_radius is None
    ):
        pts_start = [
            t1 * pz,
            t1 * kdb.Trans(0, False, start_straight + bend90_radius, 0) * pz,
        ]
    elif start_straight > 0:
        pts_start = [t1 * pz, t1 * kdb.Trans(0, False, start_straight, 0) * pz]
    else:
        pts_start = [t1 * pz]
    if (
        end_straight > 0
        and bend180_radius is None
        or end_straight <= 0
        and bend180_radius is None
    ):
        pts_end = [
            t2 * kdb.Trans(0, False, end_straight + bend90_radius, 0) * pz,
            t2 * pz,
        ]
    elif end_straight > 0:
        pts_end = [t2 * kdb.Trans(0, False, end_straight, 0) * pz, t2 * pz]
    else:
        pts_end = [t2 * pz]

    if inside:
        if bend180_radius is not None:
            t1 *= kdb.Trans(2, False, start_straight, -bend180_radius)
            t2 *= kdb.Trans(2, False, end_straight, bend180_radius)
        else:
            t1 *= kdb.Trans(
                2, False, start_straight + bend90_radius, -2 * bend90_radius
            )
            t2 *= kdb.Trans(2, False, end_straight + bend90_radius, 2 * bend90_radius)
    else:
        if bend180_radius is not None:
            t1 *= kdb.Trans(2, False, start_straight, bend180_radius)
            t2 *= kdb.Trans(2, False, end_straight, -bend180_radius)
        else:
            t1 *= kdb.Trans(2, False, start_straight + bend90_radius, 2 * bend90_radius)
            t2 *= kdb.Trans(2, False, end_straight + bend90_radius, -2 * bend90_radius)

    return (
        pts_start
        + route_manhattan(
            t1,
            t2,
            bend90_radius,
            start_steps=[Straight(dist=start_straight + d_loop)],
        )
        + pts_end
    )


def route(
    c: KCell,
    p1: Port,
    p2: Port,
    straight_factory: StraightFactory,
    bend90_cell: KCell,
    bend180_cell: KCell | None = None,
    taper_cell: KCell | None = None,
    start_straight: dbu = 0,
    end_straight: dbu = 0,
    route_path_function: ManhattanRoutePathFunction = route_manhattan,
    port_type: str = "optical",
    allow_small_routes: bool = False,
    route_kwargs: dict[str, Any] | None = {},
    route_width: dbu | None = None,
    min_straight_taper: dbu = 0,
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    purpose: str | None = "routing",
) -> ManhattanRoute:
    """Places a route.

    Args:
        c: Cell to place the route in.
        p1: Start port.
        p2: End port.
        straight_factory: Factory function for straight cells. in DBU.
        bend90_cell: 90° bend cell.
        bend180_cell: 180° bend cell.
        taper_cell: Taper cell.
        start_straight: Minimal straight segment after `p1`.
        end_straight: Minimal straight segment before `p2`.
        route_path_function: Function to calculate the route path. If bend180_cell is
            not None, this function must also take the kwargs `bend180_radius` as
            specified in
            [ManhattanRoutePathFunction180][kfactory.routing.manhattan.ManhattanRoutePathFunction180]
        port_type: Port type to use for the bend90_cell.
        allow_small_routes: Don't throw an error if two corners cannot be safely placed
            due to small space and place them anyway.
        route_kwargs: Additional keyword arguments for the route_path_function.
        route_width: Width of the route. If None, the width of the ports is used.
        min_straight_taper: Minimum straight [dbu] before attempting to place tapers.
        allow_width_mismatch: If True, the width of the ports is ignored
            (config default: False).
        allow_layer_mismatch: If True, the layer of the ports is ignored
            (config default: False).
        allow_type_mismatch: If True, the type of the ports is ignored
            (config default: False).
        purpose: Set the property "purpose" (at id kf.kcell.PROPID.PURPOSE) to the
            value. Not set if None.
    """
    if allow_width_mismatch is None:
        allow_width_mismatch = config.allow_width_mismatch
    if allow_layer_mismatch is None:
        allow_layer_mismatch = config.allow_layer_mismatch
    if allow_type_mismatch is None:
        allow_type_mismatch = config.allow_type_mismatch
    if p1.width != p2.width and not allow_width_mismatch:
        raise ValueError(
            f"The ports have different widths {p1.width=} {p2.width=}. If this is"
            "intentional, add `allow_width_mismatch=True` to override this."
        )

    p1 = p1.copy()
    p1.trans.mirror = False
    p2 = p2.copy()
    p2.trans.mirror = False

    # determine bend90_radius
    bend90_ports = [p for p in bend90_cell.ports if p.port_type == port_type]

    if len(bend90_ports) != 2:
        raise ValueError(
            f"{bend90_cell.name} should have 2 ports but has {len(bend90_ports)} ports"
        )

    if abs((bend90_ports[0].trans.angle - bend90_ports[1].trans.angle) % 4) != 1:
        raise ValueError(
            f"{bend90_cell.name} bend ports should be 90° apart from each other. "
            f"{bend90_ports[0]=} {bend90_ports[1]=}"
        )
    if (bend90_ports[1].trans.angle - bend90_ports[0].trans.angle) % 4 == 3:
        b90p1 = bend90_ports[1]
        b90p2 = bend90_ports[0]
    else:
        b90p1 = bend90_ports[0]
        b90p2 = bend90_ports[1]

    b90c = kdb.Trans(
        b90p1.trans.rot,
        b90p1.trans.is_mirror(),
        b90p1.trans.disp.x if b90p1.trans.angle % 2 else b90p2.trans.disp.x,
        b90p2.trans.disp.y if b90p1.trans.angle % 2 else b90p1.trans.disp.y,
    )

    start_port: Port = p1.copy()
    end_port: Port = p2.copy()
    b90r = int(
        max(
            (b90p1.trans.disp - b90c.disp).length(),
            (b90p2.trans.disp - b90c.disp).length(),
        )
    )

    if bend180_cell is not None:
        # Bend 180 is available
        bend180_ports = [p for p in bend180_cell.ports.filter(port_type=port_type)]
        if len(bend180_ports) != 2:
            raise AttributeError(
                f"{bend180_cell.name} should have 2 ports but has {len(bend180_ports)}"
                " ports"
            )
        if abs((bend180_ports[0].trans.angle - bend180_ports[1].trans.angle) % 4) != 0:
            raise AttributeError(
                f"{bend180_cell.name} bend ports for bend180 should be 0° apart from"
                f" each other, {bend180_ports[0]=} {bend180_ports[1]=}"
            )
        d = 1 if bend180_ports[0].trans.angle in [0, 3] else -1
        b180p1, b180p2 = list(
            sorted(
                bend180_ports,
                key=lambda port: (d * port.trans.disp.x, d * port.trans.disp.y),
            )
        )

        b180r = int((b180p2.trans.disp - b180p1.trans.disp).length())
        start_port = p1.copy()
        end_port = p2.copy()
        pts = route_path_function(  # type: ignore[call-arg]
            port1=start_port,
            port2=end_port,
            bend90_radius=b90r,
            bend180_radius=b180r,
            start_straight=start_straight,
            end_straight=end_straight,
        )

        if len(pts) > 2:
            if (vec := pts[1] - pts[0]).length() == b180r:
                match (p1.trans.angle - vec_angle(vec)) % 4:
                    case 1:
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.connect(b180p1.name, p1)
                        start_port = bend180.ports[b180p2.name]
                        pts = pts[1:]
                    case 3:
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.connect(b180p2.name, p1)
                        start_port = bend180.ports[b180p1.name]
                        pts = pts[1:]
            if (vec := pts[-1] - pts[-2]).length() == b180r:
                match (vec_angle(vec) - p2.trans.angle) % 4:
                    case 1:
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.connect(b180p1.name, p2)
                        end_port = bend180.ports[b180p2.name]
                        pts = pts[:-1]
                    case 3:
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        # bend180.mirror = True
                        bend180.connect(b180p2.name, p2)
                        end_port = bend180.ports[b180p1.name]
                        pts = pts[:-1]

            if len(pts) > 3:
                pt1, pt2, pt3 = pts[:3]
                j = 0
                for i in range(3, len(pts) - 2):
                    pt4 = pts[i]
                    vecp = pt2 - pt1
                    vec = pt3 - pt2
                    vecn = pt4 - pt3

                    ang1 = vec_angle(vecp)
                    ang2 = vec_angle(vec)
                    ang3 = vec_angle(vecn)

                    if vecp == vec and ang2 - ang1 == 0:
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        if start_port.name == b180p2.name:
                            bend180.connect(b180p1.name, start_port)
                            start_port = bend180.ports[b180p2.name]
                        else:
                            bend180.connect(b180p2.name, start_port)
                            start_port = bend180.ports[b180p1.name]
                        j = i - 1
                    elif (
                        vec.length() == b180r
                        and (ang2 - ang1) % 4 == 1
                        and (ang3 - ang2) % 4 == 1
                    ):
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.transform(
                            kdb.Trans((ang1 + 2) % 4, False, pt2.x, pt2.y)
                            * b180p1.trans.inverted()
                        )
                        place90(
                            c=c,
                            p1=start_port.copy(),
                            p2=bend180.ports[b180p1.name],
                            pts=pts[j : i - 2],
                            straight_factory=straight_factory,
                            bend90_cell=bend90_cell,
                            taper_cell=taper_cell,
                            port_type=port_type,
                            allow_small_routes=allow_small_routes,
                            allow_width_mismatch=allow_width_mismatch,
                            allow_layer_mismatch=allow_layer_mismatch,
                            allow_type_mismatch=allow_type_mismatch,
                            route_width=route_width,
                        )
                        j = i - 1
                        start_port = bend180.ports[b180p2.name]
                    elif (
                        vec.length() == b180r
                        and (ang2 - ang1) % 4 == 3
                        and (ang3 - ang2) % 4 == 3
                    ):
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.transform(
                            kdb.Trans((ang1 + 2) % 4, False, pt2.x, pt2.y)
                            * b180p2.trans.inverted()
                        )
                        place90(
                            c=c,
                            p1=start_port.copy(),
                            p2=bend180.ports[b180p2.name],
                            pts=pts[j : i - 2],
                            straight_factory=straight_factory,
                            bend90_cell=bend90_cell,
                            taper_cell=taper_cell,
                            port_type=port_type,
                            allow_small_routes=allow_small_routes,
                            allow_width_mismatch=allow_width_mismatch,
                            route_width=route_width,
                        )
                        j = i - 1
                        start_port = bend180.ports[b180p1.name]

                    pt1 = pt2
                    pt2 = pt3
                    pt3 = pt4

        route = place90(
            c=c,
            p1=start_port.copy(),
            p2=end_port.copy(),
            pts=pts,
            straight_factory=straight_factory,
            bend90_cell=bend90_cell,
            taper_cell=taper_cell,
            min_straight_taper=min_straight_taper,
            port_type=port_type,
            allow_small_routes=allow_small_routes,
            allow_width_mismatch=allow_width_mismatch,
            route_width=route_width,
        )

    else:
        start_port = p1.copy()
        end_port = p2.copy()
        if not route_kwargs:
            pts = route_path_function(
                start_port,
                end_port,
                bend90_radius=b90r,
                start_steps=[Straight(dist=start_straight)],
                end_steps=[Straight(dist=end_straight)],
            )
        else:
            pts = route_path_function(
                start_port,
                end_port,
                bend90_radius=b90r,
                start_steps=[Straight(dist=start_straight)],
                end_steps=[Straight(dist=end_straight)],
                **route_kwargs,
            )

        route = place90(
            c=c,
            p1=p1.copy(),
            p2=p2.copy(),
            pts=pts,
            straight_factory=straight_factory,
            bend90_cell=bend90_cell,
            taper_cell=taper_cell,
            allow_small_routes=allow_small_routes,
            min_straight_taper=min_straight_taper,
            port_type=port_type,
            allow_width_mismatch=allow_width_mismatch,
            route_width=route_width,
        )
    return route


def vec_angle(v: kdb.Vector) -> int:
    """Determine vector angle in increments of 90°."""
    if v.x != 0 and v.y != 0:
        raise ValueError("Non-manhattan vectors are not supported")

    match (v.x, v.y):
        case (x, 0) if x > 0:
            return 0
        case (x, 0) if x < 0:
            return 2
        case (0, y) if y > 0:
            return 1
        case (0, y) if y < 0:
            return 3
        case _:
            logger.warning(f"{v} is not a manhattan, cannot determine direction")
    return -1

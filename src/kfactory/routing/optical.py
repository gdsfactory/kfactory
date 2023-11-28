"""Optical routing allows the creation of photonic (or any route using bends)."""

from collections.abc import Callable, Sequence
from typing import Any

from pydantic import BaseModel

from .. import kdb
from ..conf import config
from ..kcell import Instance, KCell, Port
from .manhattan import (
    backbone2bundle,
    clean_points,
    route_manhattan,
    route_ports_to_bundle,
)


class OpticalManhattanRoute(BaseModel, arbitrary_types_allowed=True):
    """Optical route containing a connection between two ports.

    Attrs:
        backbone: backbone points
        start_port: port at the first instance denoting the start of the route
        end_port: port at the last instance denoting the end of the route
        instances: list of the instances in order from start to end of the route
        n_bend90: number of bends used
        length: length of the route without the bends
        length_straights: length of the straight_factory elements
    """

    backbone: list[kdb.Point]
    start_port: Port
    end_port: Port
    instances: list[Instance]
    n_bend90: int = 0
    length: int = 0
    length_straights: int = 0

    @property
    def length_backbone(self) -> int:
        """Length of the backbone in dbu."""
        length = 0
        p_old = self.backbone[0]
        for p in self.backbone[1:]:
            length += int((p - p_old).length())
            p_old = p
        return length


def vec_angle(v: kdb.Vector) -> int:
    """Determine vector angle in increments of 90°."""
    if v.x != 0 and v.y != 0:
        raise NotImplementedError("only manhattan vectors supported")

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
            config.logger.warning(f"{v} is not a manhattan, cannot determine direction")
    return -1


def route_loopback(
    p1: Port | kdb.Trans,
    p2: Port | kdb.Trans,
    bend90_radius: int,
    bend180_radius: int | None = None,
    start_straight: int = 0,
    end_straight: int = 0,
    d_loop: int = 200000,
) -> list[kdb.Point]:
    r"""Create a loopback on two parallel ports.

        ╭----╮            ╭----╮
        |    |            |    |
        |  -----        -----  |
        |  port1        port2  |
        ╰----------------------╯


    Args:
        p1: Start port.
        p2: End port.
        bend90_radius: Radius of 90° bend. [dbu]
        bend180_radius: Optional use of 180° bend, distance between two parallel ports.
            [dbu]
        start_straight: Minimal straight segment after `p1`.
        end_straight: Minimal straight segment before `p2`.
        d_loop: Distance of the (vertical) offset of the back of the ports

    Returns:
        points: List of the calculated points (starting/ending at p1/p2).
    """
    t1 = p1 if isinstance(p1, kdb.Trans) else p1.trans
    t2 = p2 if isinstance(p2, kdb.Trans) else p2.trans

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
            start_straight=start_straight + d_loop,
            end_straight=0,
        )
        + pts_end
    )


@config.logger.catch
def route(
    c: KCell,
    p1: Port,
    p2: Port,
    straight_factory: Callable[[int, int], KCell],
    bend90_cell: KCell,
    bend180_cell: KCell | None = None,
    taper_cell: KCell | None = None,
    start_straight: int = 0,
    end_straight: int = 0,
    route_path_function: Callable[
        ...,
        list[kdb.Point],
    ] = route_manhattan,
    port_type: str = "optical",
    allow_small_routes: bool = False,
    different_port_width: int = False,
    route_kwargs: dict[str, Any] | None = {},
    min_straight_taper: int = 0,
) -> OpticalManhattanRoute:
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
        route_path_function: Function to calculate the route path.
        port_type: Port type to use for the bend90_cell.
        allow_small_routes: Don't throw an error if two corners cannot be safely placed
            due to small space and place them anyway.
        different_port_width: If True, the width of the ports is ignored.
        route_kwargs: Additional keyword arguments for the route_path_function.
        min_straight_taper: Minimum straight [dbu] before attempting to place tapers.

    """
    if p1.width != p2.width and not different_port_width:
        raise ValueError(
            f"The ports have different widths {p1.width=} {p2.width=}. If this is"
            "intentional, add `different_port_width=True` to override this."
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
            f"{bend90_cell.name} bend ports should be 90° apart from each other"
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
        bend180_ports = [p for p in bend180_cell.ports if p.port_type == port_type]
        if len(bend180_ports) != 2:
            raise AttributeError(
                f"{bend180_cell.name} should have 2 ports but has {len(bend180_ports)}"
                " ports"
            )
        if abs((bend180_ports[0].trans.angle - bend180_ports[1].trans.angle) % 4) != 0:
            raise AttributeError(
                f"{bend180_cell.name} bend ports for bend180 should be 0° apart from"
                " each other"
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
        pts = route_path_function(
            start_port,
            end_port,
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
                        bend180.connect(b180p1.name, p1)
                        start_port = bend180.ports[b180p2.name]
                        pts = pts[1:]
                    case 3:
                        bend180 = c << bend180_cell
                        bend180.connect(b180p2.name, p1)
                        start_port = bend180.ports[b180p1.name]
                        pts = pts[1:]
            if (vec := pts[-1] - pts[-2]).length() == b180r:
                match (vec_angle(vec) - p2.trans.angle) % 4:
                    case 1:
                        bend180 = c << bend180_cell
                        bend180.connect(b180p1.name, p2)
                        end_port = bend180.ports[b180p2.name]
                        pts = pts[:-1]
                    case 3:
                        bend180 = c << bend180_cell
                        # bend180.mirror = True
                        bend180.connect(b180p2.name, p2)
                        end_port = bend180.ports[b180p1.name]
                        pts = pts[:-1]

            if len(pts) > 3:
                # TODO 180 stuff
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
                        bend180.transform(
                            kdb.Trans((ang1 + 2) % 4, False, pt2.x, pt2.y)
                            * b180p1.trans.inverted()
                        )
                        place90(
                            c,
                            start_port.copy(),
                            bend180.ports[b180p1.name],
                            pts[j : i - 2],
                            straight_factory,
                            bend90_cell,
                            taper_cell,
                        )
                        j = i - 1
                        start_port = bend180.ports[b180p2.name]
                    elif (
                        vec.length() == b180r
                        and (ang2 - ang1) % 4 == 3
                        and (ang3 - ang2) % 4 == 3
                    ):
                        bend180 = c << bend180_cell
                        bend180.transform(
                            kdb.Trans((ang1 + 2) % 4, False, pt2.x, pt2.y)
                            * b180p2.trans.inverted()
                        )
                        place90(
                            c,
                            start_port.copy(),
                            bend180.ports[b180p2.name],
                            pts[j : i - 2],
                            straight_factory,
                            bend90_cell,
                            taper_cell,
                        )
                        j = i - 1
                        start_port = bend180.ports[b180p1.name]

                    pt1 = pt2
                    pt2 = pt3
                    pt3 = pt4

        route = place90(
            c,
            start_port.copy(),
            end_port.copy(),
            pts,
            straight_factory,
            bend90_cell,
            taper_cell,
            min_straight_taper=min_straight_taper,
        )

    else:
        start_port = p1.copy()
        end_port = p2.copy()
        if not route_kwargs:
            pts = route_path_function(
                start_port,
                end_port,
                bend90_radius=b90r,
                start_straight=start_straight,
                end_straight=end_straight,
            )
        else:
            pts = route_path_function(
                start_port,
                end_port,
                bend90_radius=b90r,
                start_straight=start_straight,
                end_straight=end_straight,
                **route_kwargs,
            )

        route = place90(
            c,
            p1.copy(),
            p2.copy(),
            pts,
            straight_factory,
            bend90_cell,
            taper_cell,
            allow_small_routes=allow_small_routes,
            min_straight_taper=min_straight_taper,
        )
    return route


def route_bundle(
    c: KCell,
    start_ports: list[Port],
    end_ports: list[Port],
    spacing: int,
    straight_factory: Callable[[int, int], KCell],
    bend90_cell: KCell,
    start_straight: int = 0,
    end_straight: int = 0,
    route_path_function: Callable[
        ...,
        list[kdb.Point],
    ] = route_manhattan,
    bundle_backbone: list[kdb.Point] | None = None,
) -> list[OpticalManhattanRoute]:
    """Route a bundle from starting ports to end_ports."""
    radius = max(
        abs(bend90_cell.ports[0].x - bend90_cell.ports[1].x),
        abs(bend90_cell.ports[0].y - bend90_cell.ports[1].y),
    )

    sp_dict = {p.trans: i for i, p in enumerate(start_ports)}

    if not (len(start_ports) == len(end_ports) and len(start_ports) > 0):
        raise ValueError(
            "For bundle routing the input port list must have"
            " the same size as the end ports and be the same length."
        )

    bundle_point_start = start_ports[0].trans.disp.to_p()
    for p in start_ports[1:]:
        bundle_point_start += p.trans.disp
    bundle_point_start /= len(start_ports)
    bundle_point_end = end_ports[0].trans.disp.to_p()
    for p in end_ports[1:]:
        bundle_point_end += p.trans.disp
    bundle_point_end /= len(end_ports)

    bundle_width = sum(p.width for p in start_ports) + len(start_ports) * spacing

    start_routes, bundle_start = route_ports_to_bundle(
        ports_to_route=[(p.trans, p.width) for p in start_ports],
        bend_radius=radius,
        bbox=c.bbox(),
        bundle_base_point=bundle_point_start,
        start_straight=start_straight,
        spacing=spacing,
    )

    end_routes, bundle_end = route_ports_to_bundle(
        ports_to_route=[(p.trans, p.width) for p in end_ports],
        bend_radius=radius,
        bbox=c.bbox(),
        bundle_base_point=bundle_point_end,
        start_straight=end_straight,
        spacing=spacing,
    )

    start_widths = [start_ports[sp_dict[t]].width for t in start_routes]
    bundle_radius = bundle_width - start_widths[-1] // 2 - start_widths[0] // 2 + radius

    start_angle = start_ports[0].angle
    end_angle = end_ports[0].angle

    bundle_start_port = Port(
        layer=start_ports[0].layer,
        width=bundle_width,
        trans=kdb.Trans(start_angle, False, bundle_start.to_v()),
    )

    bundle_end_port = Port(
        layer=end_ports[0].layer,
        width=bundle_width,
        trans=kdb.Trans(end_angle, False, bundle_end.to_v()),
    )

    backbone_points = backbone2bundle(
        backbone=route_manhattan(
            port1=bundle_start_port,
            port2=bundle_end_port,
            bend90_radius=bundle_radius,
            start_straight=0,
            end_straight=0,
        ),
        port_widths=start_widths,
        spacings=[spacing] * len(start_widths),
    )

    routes: list[OpticalManhattanRoute] = []

    end_routes_values = list(end_routes.values())

    for i, (t, start_pts) in enumerate(start_routes.items()):
        bundle_pts = backbone_points[i]
        end_pts = list(reversed(end_routes_values[-(i + 1)]))

        pts = clean_points(start_pts + bundle_pts + end_pts)

        s_idx = sp_dict[t]
        sp = start_ports[s_idx].copy()
        sp.angle = (sp.trans.angle + 2) % 4
        ep = end_ports[s_idx].copy()
        ep.angle = (ep.trans.angle + 2) % 4
        routes.append(
            place90(
                c=c,
                p1=sp,
                p2=ep,
                pts=pts,
                straight_factory=straight_factory,
                bend90_cell=bend90_cell,
            )
        )

    return routes


def place90(
    c: KCell,
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    straight_factory: Callable[..., KCell],
    bend90_cell: KCell,
    taper_cell: KCell | None = None,
    port_type: str = "optical",
    min_straight_taper: int = 0,
    allow_small_routes: bool = False,
) -> OpticalManhattanRoute:
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
    """
    route_start_port = p1.copy()
    route_start_port.name = None
    route_start_port.trans.angle = (route_start_port.angle + 2) % 4
    route_end_port = p2.copy()
    route_end_port.name = None
    route_end_port.trans.angle = (route_end_port.angle + 2) % 4
    route = OpticalManhattanRoute(
        parent=c,
        backbone=list(pts).copy(),
        start_port=route_start_port,
        end_port=route_end_port,
        instances=[],
    )
    if not pts or len(pts) < 2:
        # Nothing to be placed
        return route

    w = p1.width
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
    assert b90p1.name is not None, config.logger.error(
        "bend90_cell needs named ports, {}", b90p1
    )
    assert b90p2.name is not None, config.logger.error(
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
                "At least one optical ports of the taper must be the same width as"
                " the bend's ports"
            )

    if len(pts) == 2:
        length = (pts[1] - pts[0]).length()
        route.length += int(length)
        if (
            taper_cell is None
            or length
            < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
            + min_straight_taper
        ):
            wg = c << straight_factory(width=w, length=(pts[1] - pts[0]).length())
            wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
            wg.connect(wg_p1, p1)
            route.instances.append(wg)
            route.start_port = wg_p1.copy()
            route.start_port.name = None
            route.length_straights += int(length)
        else:
            t1 = c << taper_cell
            t1.connect(taperp1.name, p1)
            route.instances.append(t1)
            route.start_port = t1.ports[taperp1.name].copy()
            route.start_port.name = None
            _l = int(length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2)
            if _l != 0:
                wg = c << straight_factory(
                    width=taperp2.width,
                    length=length
                    - (taperp1.trans.disp - taperp2.trans.disp).length() * 2,
                )
                wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                wg.connect(wg_p1, t1, taperp2.name)
                route.instances.append(wg)
                t2 = c << taper_cell
                t2.connect(taperp2.name, wg_p2)
                route.length_straights += _l
            else:
                t2 = c << taper_cell
                t2.connect(taperp2.name, t1, taperp2.name)
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
        length = (
            bend90.ports[b90p1.name].trans.disp - old_bend_port.trans.disp
        ).length()
        route.length += int(length)
        if length > 0:
            if (
                taper_cell is None
                or length
                < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                + min_straight_taper
            ):
                wg = c << straight_factory(width=w, length=length)
                wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                wg.connect(wg_p1, bend90, b90p1.name)
                route.instances.append(wg)
                route.length_straights += int(length)
            else:
                t1 = c << taper_cell
                t1.connect(taperp1.name, bend90, b90p1.name)
                route.instances.append(t1)
                _l = int(
                    length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                )
                if length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2 != 0:
                    wg = c << straight_factory(
                        width=taperp2.width,
                        length=length
                        - (taperp1.trans.disp - taperp2.trans.disp).length() * 2,
                    )
                    wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                    wg.connect(wg_p1.name, t1, taperp2.name)
                    route.instances.append(wg)
                    t2 = c << taper_cell
                    t2.connect(taperp2.name, wg, wg_p2.name)
                    route.length_straights += _l
                else:
                    t2 = c << taper_cell
                    t2.connect(taperp2.name, t1, taperp2.name)
                route.instances.append(t2)
        route.instances.append(bend90)
        old_pt = pt
        old_bend_port = bend90.ports[b90p2.name]
    length = (bend90.ports[b90p2.name].trans.disp - p2.trans.disp).length()
    route.length += int(length)
    if length > 0:
        if (
            taper_cell is None
            or length
            < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
            + min_straight_taper
        ):
            wg = c << straight_factory(width=w, length=length)
            wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
            wg.connect(wg_p1.name, bend90, b90p2.name)
            route.instances.append(wg)
            route.end_port = wg.ports[wg_p2.name].copy()
            route.end_port.name = None
            route.length_straights += int(length)
        else:
            t1 = c << taper_cell
            t1.connect(taperp1.name, bend90, b90p2.name)
            route.instances.append(t1)
            if length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2 != 0:
                _l = int(
                    length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                )
                wg = c << straight_factory(
                    width=taperp2.width,
                    length=_l,
                )
                route.instances.append(wg)
                wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                wg.connect(wg_p1.name, t1, taperp2.name)
                t2 = c << taper_cell
                t2.connect(taperp2.name, wg, wg_p2.name)
                route.length_straights += int(_l)
            else:
                t2 = c << taper_cell
                t2.connect(taperp2.name, t1, taperp2.name)
            route.instances.append(t2)
            route.end_port = t2.ports[taperp1.name].copy()
            route.end_port.name = None
    else:
        route.end_port = old_bend_port.copy()
        route.end_port.name = None
    return route

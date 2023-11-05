"""Can calculate manhattan routes based on ports/transformations."""

from typing import Literal

import numpy as np

from .. import kdb
from ..conf import config
from ..enclosure import clean_points
from ..kcell import KCLayout, Port

__all__ = ["route_manhattan", "route_manhattan_180", "clean_points"]


def droute_manhattan_180(
    port1: kdb.DTrans,
    port2: kdb.DTrans,
    bend90_radius: float,
    bend180_radius: float,
    start_straight: float,
    end_straight: float,
    layout: KCLayout | kdb.Layout,
) -> list[kdb.Point]:
    """Calculate manhattan route using um based points.

    Args:
        port1: Transformation of start port.
        port2: Transformation of end port.
        bend90_radius: The radius or (symmetrical) dimension of 90° bend. [um]
        bend180_radius: The distance between the two ports of the 180° bend. [um]
        start_straight: Minimum straight after the starting port. [um]
        end_straight: Minimum straight before the end port. [um]
        layout: Layout/KCLayout object where to get the dbu info from.

    Returns:
        route: Calculated route in points in dbu.
    """
    return route_manhattan_180(
        port1.to_itype(layout.dbu),
        port2.to_itype(layout.dbu),
        int(bend90_radius / layout.dbu),
        int(bend180_radius / layout.dbu),
        int(start_straight / layout.dbu),
        int(end_straight / layout.dbu),
    )


def route_manhattan_180(
    port1: Port | kdb.Trans,
    port2: Port | kdb.Trans,
    bend90_radius: int,
    bend180_radius: int,
    start_straight: int,
    end_straight: int,
) -> list[kdb.Point]:
    """Calculate manhattan route using um based points.

    Args:
        port1: Transformation of start port.
        port2: Transformation of end port.
        bend90_radius: The radius or (symmetrical) dimension of 90° bend. [dbu]
        bend180_radius: The distance between the two ports of the 180° bend. [dbu]
        start_straight: Minimum straight after the starting port. [dbu]
        end_straight: Minimum straight before the end port. [dbu]

    Returns:
        route: Calculated route in points in dbu.
    """
    t1 = port1.dup() if isinstance(port1, kdb.Trans) else port1.trans.dup()
    t2 = port2.dup() if isinstance(port2, kdb.Trans) else port2.trans.dup()

    _p = kdb.Point(0, 0)

    p1 = t1 * _p
    p2 = t2 * _p

    if t2.disp == t1.disp and t2.angle == t1.angle:
        raise ValueError("Identically oriented ports cannot be connected")

    tv = t1.inverted() * (t2.disp - t1.disp)

    if (t2.angle - t1.angle) % 4 == 2 and tv.y == 0:
        if tv.x > 0:
            return [p1, p2]
        if tv.x == 0:
            return []

    t1 *= kdb.Trans(0, False, start_straight, 0)
    # t2 *= kdb.Trans(0, False, end_straight, 0)

    points = [p1] if start_straight != 0 else []
    end_points = [t2 * _p, p2] if end_straight != 0 else [p2]
    tv = t1.inverted() * (t2.disp - t1.disp)
    if tv.abs() == 0:
        return points + end_points
    if (t2.angle - t1.angle) % 4 == 2 and tv.x > 0 and tv.y == 0:
        return points + end_points
    match (tv.x, tv.y, (t2.angle - t1.angle) % 4):
        case (x, y, 0) if x > 0 and abs(y) == bend180_radius:
            if end_straight > 0:
                t2 *= kdb.Trans(0, False, end_straight, 0)
            pts = [t1.disp.to_p(), t2.disp.to_p()]
            pts[1:1] = [pts[1] + (t2 * kdb.Vector(0, tv.y))]
            raise NotImplementedError(
                "`case (x, y, 0) if x > 0 and abs(y) == bend180_radius`"
                " not supported yet"
            )
        case (x, 0, 2):
            if start_straight > 0:
                t1 *= kdb.Trans(0, False, start_straight, 0)
            if end_straight > 0:
                t2 *= kdb.Trans(0, False, end_straight, 0)
            pts = [t1.disp.to_p(), t2.disp.to_p()]
            pts[1:1] = [
                pts[0] + t1 * kdb.Vector(0, bend180_radius),
                pts[1] + t2 * kdb.Vector(0, bend180_radius),
            ]

            if start_straight != 0:
                pts.insert(
                    0,
                    (t1 * kdb.Trans(0, False, -start_straight, 0)).disp.to_p(),
                )
            if end_straight != 0:
                pts.append((t2 * kdb.Trans(0, False, -end_straight, 0)).disp.to_p())
            return pts
        case _:
            return route_manhattan(
                t1.dup(),
                t2.dup(),
                bend90_radius,
                start_straight=0,
                end_straight=end_straight,
            )
    raise NotImplementedError(
        "Case not supportedt yet. Please open an issue if you believe this is an error"
        " and needs to be implemented ;)"
    )


def droute_manhattan(
    port1: kdb.DTrans,
    port2: kdb.DTrans,
    bend90_radius: int,
    start_straight: int,
    end_straight: int,
    layout: KCLayout | kdb.Layout,
    invert: bool = False,
) -> list[kdb.Point]:
    """Calculate manhattan route using um based points.

    Doesn't use any non-90° bends.

    Args:
        port1: Transformation of start port.
        port2: Transformation of end port.
        bend90_radius: The radius or (symmetrical) dimension of 90° bend. [um]
        start_straight: Minimum straight after the starting port. [um]
        end_straight: Minimum straight before the end port. [um]
        layout: Layout/KCLayout object where to get the dbu info from.
        invert: Invert the direction in which to route. In the normal behavior,
            route manhattan will try to take turns first. If true, it will try
            to route straight as long as possible

    Returns:
        route: Calculated route in points in dbu.
    """
    return route_manhattan(
        port1.to_itype(layout.dbu),
        port2.to_itype(layout.dbu),
        int(bend90_radius / layout.dbu),
        int(start_straight / layout.dbu),
        int(end_straight / layout.dbu),
        invert=invert,
    )


@config.logger.catch(reraise=True)
def route_manhattan(
    port1: Port | kdb.Trans,
    port2: Port | kdb.Trans,
    bend90_radius: int,
    start_straight: int,
    end_straight: int,
    max_tries: int = 20,
    invert: bool = False,
) -> list[kdb.Point]:
    """Calculate manhattan route using um based points.

    Only uses 90° bends.

    Args:
        port1: Transformation of start port.
        port2: Transformation of end port.
        bend90_radius: The radius or (symmetrical) dimension of 90° bend. [dbu]
        start_straight: Minimum straight after the starting port. [dbu]
        end_straight: Minimum straight before the end port. [dbu]
        max_tries: Maximum number of tries to calculate a manhattan route before
            giving up
        invert: Invert the direction in which to route. In the normal behavior,
            route manhattan will try to take turns first. If true, it will try
            to route straight as long as possible

    Returns:
        route: Calculated route in dbu points.
    """
    if not invert:
        t1 = port1.dup() if isinstance(port1, kdb.Trans) else port1.trans.dup()
        t2 = port2.dup() if isinstance(port2, kdb.Trans) else port2.trans.dup()
        _start_straight = start_straight
        _end_straight = end_straight
    else:
        t2 = port1.dup() if isinstance(port1, kdb.Trans) else port1.trans.dup()
        t1 = port2.dup() if isinstance(port2, kdb.Trans) else port2.trans.dup()
        _end_straight = start_straight
        _start_straight = end_straight
    _p = kdb.Point(0, 0)

    p1 = t1 * _p
    p2 = t2 * _p
    tv = t1.inverted() * (t2.disp - t1.disp)

    if (t2.angle - t1.angle) % 4 == 2 and tv.y == 0:
        if tv.x > 0:
            return [p1, p2]
        if tv.x == 0:
            return []
    if (
        (np.sign(tv.y) * (t2.angle - t1.angle)) % 4 == 3
        and abs(tv.y) > bend90_radius + _end_straight
        and tv.x >= bend90_radius + _start_straight
        and _end_straight == 0
        and _start_straight == 0
    ):
        return [p1, p1 + (t1 * kdb.Vector(tv.x, 0)), p2]

    if t2.disp == t1.disp and t2.angle == t1.angle:
        raise ValueError("Identically oriented ports cannot be connected")

    box = kdb.Box(
        (t1 * kdb.Trans(0, False, _start_straight, 0)).disp.to_p(),
        (t2 * kdb.Trans(0, False, _end_straight, 0)).disp.to_p(),
    )
    match (box.width(), box.height()):
        case (x, y) if (x < bend90_radius and y <= 2 * bend90_radius) or (
            x <= 2 * bend90_radius and y < bend90_radius
        ):
            config.logger.warning(
                "Potential collision in routing due to small distance between the port "
                f"in relation to bend radius {x=}/{bend90_radius}, {y=}/{bend90_radius}"
            )

    # we want a straight start and have to add a bend radius if
    t1 *= kdb.Trans(_start_straight + bend90_radius, 0)
    tv = t1.inverted() * (t2.disp - t1.disp)

    points = [p1]
    end_points = None

    if t2.angle == t1.angle == 0 and tv.x < 0 and abs(tv.y) >= 2 * bend90_radius:
        t2 *= kdb.Trans(_end_straight, 0)
        if _end_straight == 0:
            end_points = [p2]
        else:
            end_points = [t2 * _p, p2]
    else:
        t2 *= kdb.Trans(_end_straight + bend90_radius, 0)
        end_points = [t2 * _p, p2]

    t1.inverted() * (t2.disp - t1.disp)

    for _ in range(max_tries):
        tv = t1.inverted() * (t2.disp - t1.disp)
        if tv.abs() == 0 and (t2.angle - t1.angle) % 4 == 2:
            break
        if (t2.angle - t1.angle) % 4 == 2 and tv.x > 0 and tv.y == 0:
            break
        points.append(t1 * _p)

        match (int(np.sign(tv.x)), int(np.sign(tv.y)), (t2.angle - t1.angle) % 4):
            case (0, 0, ang):
                if ang == 0:
                    raise ValueError("Something weird happened")
                else:
                    break
            case (x, y, 2) if x == -1 and y != abs(tv.y) > 4 * bend90_radius:
                t1 *= kdb.Trans(-y % 4, False, 0, -y * 2 * bend90_radius)
            case (x, 0, ang) if abs(tv.x) > 2 * bend90_radius and (
                ang != 2 or x != -1
            ) and ang != 0:
                break
            case (0, y, ang) if (y * ang) % 4 != 1:
                break
            case (0, y, ang) if (y * ang) % 4 == 3:
                t1 *= kdb.Trans(0, False, 2 * bend90_radius, 0)
            case (x, y, 0):
                if abs(tv.y) < 2 * bend90_radius:
                    d = -y if y != 0 else -1
                    t1 *= kdb.Trans(d % 4, False, 0, d * 2 * bend90_radius)
                else:
                    if x == 1:
                        t1 *= kdb.Trans(0, False, tv.x, 0)
                    else:
                        t1 *= kdb.Trans(y, False, 0, tv.y)
            case (-1, y, 2):
                if abs(tv.y) > 4 * bend90_radius:
                    t1 *= kdb.Trans(2, False, 0, y * 2 * bend90_radius)
                else:
                    t1 *= kdb.Trans(
                        2, False, 0, (-y if y != 0 else 1) * 2 * bend90_radius
                    )
            case (x, y, 2):
                if abs(tv.y) < 2 * bend90_radius:
                    t1 *= kdb.Trans(-y, False, 0, -y * 2 * bend90_radius)
                else:
                    t1 *= kdb.Trans(y % 4, False, 0, tv.y)
            case (x, y, ang) if ang in [1, 3]:
                if x == -1:
                    if tv.x > -2 * bend90_radius:
                        t1 *= kdb.Trans(0, False, 2 * bend90_radius + tv.x, 0)
                    else:
                        if abs(tv.y) < 2 * bend90_radius:
                            _y = y if y != 0 else 1
                            t1 *= kdb.Trans(
                                (-_y) % 4, False, 0, -_y * 2 * bend90_radius
                            )
                        else:
                            t1 *= kdb.Trans(y % 4, False, 0, y * 2 * bend90_radius)
                elif (y * ang) % 4 == 3 and x == 1:
                    if tv.x < 2 * bend90_radius:
                        t1 *= kdb.Trans(y, False, tv.x + 2 * bend90_radius, 0)
                    else:
                        t1 *= kdb.Trans(0, False, tv.x, 0)
                else:
                    if abs(tv.x) < 2 * bend90_radius:
                        if abs(tv.y) < 2 * bend90_radius:
                            t1 *= kdb.Trans(-y, False, 0, -y * 2 * bend90_radius)
                            points.append(t1 * _p)
                            t1 *= kdb.Trans(
                                y,
                                False,
                                0,
                                y * 2 * bend90_radius + (tv.y if tv.y > 0 else 0),
                            )
                        else:
                            t1 *= kdb.Trans(0, False, 2 * bend90_radius + tv.x, 0)
                    else:
                        if y != 0 and abs(tv.y) < 2 * bend90_radius:
                            if y > 0:
                                t1 *= kdb.Trans(
                                    y, False, 0, tv.y + y * 2 * bend90_radius
                                )
                            else:
                                t1 *= kdb.Trans(y, False, 0, y * 2 * bend90_radius)
                        else:
                            t1 *= kdb.Trans(y, False, 0, tv.y)
    clean_points(points)
    points.extend(end_points)
    clean_points(points)

    if invert:
        points.reverse()
    return points


def vec_dir(vec: kdb.Vector) -> int:
    match (vec.x, vec.y):
        case (x, 0) if x > 0:
            return 0
        case (x, 0) if x < 0:
            return 2
        case (0, y) if y > 0:
            return 1
        case (0, y) if y < 0:
            return 3
        case _:
            raise ValueError(f"Non-manhattan vectors aren't supported {vec}")


@config.logger.catch(reraise=True)
def backbone2bundle(
    backbone: list[kdb.Point],
    port_widths: list[int],
    spacings: list[int],
) -> list[list[kdb.Point]]:
    """Used to extract a bundle from a backbone."""
    pts: list[list[kdb.Point]] = []

    edges: list[kdb.Edge] = []
    dirs: list[int] = []
    p1 = backbone[0]

    for p2 in backbone[1:]:
        edges.append(kdb.Edge(p1, p2))
        dirs.append(vec_dir(p2 - p1))
        p1 = p2

    width = sum(port_widths) + sum(spacings)

    x = -width // 2

    for pw, spacing in zip(port_widths, spacings):
        x += pw // 2 + spacing // 2

        _pts = [p.dup() for p in backbone]
        p1 = _pts[0]

        for p2, e, dir in zip(_pts[1:], edges, dirs):
            _e = e.shifted(-x)
            if dir % 2:
                p1.x = _e.p1.x
                p2.x = _e.p2.x
            else:
                p1.y = _e.p1.y
                p2.y = _e.p2.y
            p1 = p2

        x += spacing - spacing // 2 + pw - pw // 2
        pts.append(_pts)

    return pts


def route_ports_to_bundle(
    ports_to_route: list[tuple[kdb.Trans, int]],
    bend_radius: int,
    bbox: kdb.Box,
    spacing: int,
    bundle_base_point: kdb.Point,
    start_straight: int = 0,
    end_straight: int = 0,
) -> tuple[dict[kdb.Trans, list[kdb.Point]], kdb.Point]:
    dir = ports_to_route[0][0].angle
    dir_trans = kdb.Trans(dir, False, 0, 0)
    inv_dir_trans = dir_trans.inverted()
    trans_ports = [
        (inv_dir_trans * _trans, _width) for (_trans, _width) in ports_to_route
    ]
    bundle_width = sum(tw[1] for tw in trans_ports) + (len(trans_ports) - 1) * spacing

    trans_mapping = {
        norm_t: t for (t, _), (norm_t, _) in zip(ports_to_route, trans_ports)
    }

    def sort_port(port_width: tuple[kdb.Trans, int]) -> int:
        return -port_width[0].disp.y

    def append_straights(
        straights: list[int], current_straights: list[int], reverse: bool
    ) -> None:
        if reverse:
            straights.extend(reversed(current_straights))
            current_straights.clear()
        else:
            straights.extend(current_straights)
            current_straights.clear()

    sorted_ports = list(sorted(trans_ports, key=sort_port))

    base_bundle_position = inv_dir_trans * bundle_base_point
    bundle_position = base_bundle_position.dup()

    old_dir = 2

    straight: int = 0
    straights: list[int] = []
    current_straights: list[int] = []
    bend_straight_lengths: list[int] = []
    bundle_route_y = bundle_position.y + bundle_width // 2

    for _trans, _width in sorted_ports:
        bundle_route_y -= _width // 2
        dy = _trans.disp.y - bundle_route_y

        match dy:
            case 0:
                _dir = 0
            case y if y > 0:
                _dir = 1
            case _:
                _dir = -1
        changed = _dir != old_dir
        match dy:
            case 0:
                bend_straight_lengths.append(0)
                append_straights(straights, current_straights, old_dir == -1)
                current_straights.append(0)
                straight = _width + spacing
                old_dir = _dir
            case y if abs(y) < 2 * bend_radius:
                bend_straight_lengths.append(4 * bend_radius)
                if not changed:
                    append_straights(straights, current_straights, old_dir == -1)
                    current_straights.append(0)
                    straight = _width + spacing
                    old_dir = -_dir
                else:
                    current_straights.append(straight)
                    straight = 0
            case _:
                bend_straight_lengths.append(2 * bend_radius)
                if changed:
                    append_straights(straights, current_straights, old_dir == -1)
                    current_straights.append(0)
                    straight = _width + spacing
                else:
                    current_straights.append(straight)
                    straight += _width + spacing
                old_dir = _dir
        bundle_route_y -= _width - _width // 2 + spacing
    append_straights(straights, current_straights, old_dir == -1)

    bundle_position_x = max(
        tw[0].disp.x + ss + es + start_straight + end_straight
        for tw, ss, es in zip(sorted_ports, bend_straight_lengths, straights)
    )
    bundle_position.x = max(bundle_position.x, bundle_position_x)

    bundle_route_y = bundle_position.y + bundle_width // 2
    bundle_route_x = bundle_position.x
    port_dict: dict[kdb.Trans, list[kdb.Point]] = {}

    for (_trans, _width), _end_straight in zip(sorted_ports, straights):
        bundle_route_y -= _width // 2
        t_e = kdb.Trans(2, False, bundle_route_x, bundle_route_y)
        pts = [
            dir_trans * p
            for p in route_manhattan(
                t_e,
                _trans,
                bend90_radius=bend_radius,
                start_straight=_end_straight + end_straight,
                end_straight=start_straight,
            )
        ]
        pts.reverse()
        port_dict[trans_mapping[_trans]] = pts
        bundle_route_y -= _width - _width // 2 + spacing

    return port_dict, dir_trans * bundle_position


def route_ports_side(
    dir: Literal[1, -1],
    ports_to_route: list[tuple[kdb.Trans, int]],
    existing_side_ports: list[tuple[kdb.Trans, int]],
    bend_radius: int,
    bbox: kdb.Box,
    spacing: int,
    start_straight: int = 0,
) -> dict[kdb.Trans, list[kdb.Point]]:
    _ports_dir = ports_to_route[0][0].angle
    _dir = (_ports_dir + dir) % 4
    _attr = "y" if _ports_dir % 2 else "x"
    _inv_rot = kdb.Trans(_ports_dir, False, 0, 0).inverted()

    _pts = [
        kdb.Point(0, 0),
        kdb.Point(bend_radius, 0),
        kdb.Point(bend_radius, dir * bend_radius),
    ]

    def base_pts(trans: kdb.Trans, start_straight: int) -> list[kdb.Point]:
        pts = [p.dup() for p in _pts]
        for pt in pts[1:]:
            pt.x = pt.x + start_straight
        return [trans * p for p in pts]

    pts_dict: dict[kdb.Trans, list[kdb.Point]] = {}

    ports_to_route.sort(key=lambda port_width: -dir * (_inv_rot * port_width[0]).disp.y)

    start_straight = 0

    for trans, width in ports_to_route:
        _trans = kdb.Trans(_ports_dir, False, trans.disp.x, trans.disp.y)
        pts_dict[trans] = base_pts(_trans, start_straight=start_straight)
        start_straight += width + spacing

    return pts_dict

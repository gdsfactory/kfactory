"""Can calculate manhattan routes based on ports/transformations."""

from functools import partial
from typing import Literal

import numpy as np

from .. import kdb
from ..conf import config
from ..enclosure import clean_points
from ..kcell import KCLayout, Port

__all__ = ["route_manhattan", "route_manhattan_180"]


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

    Returns:
        route: Calculated route in points in dbu.
    """
    return route_manhattan(
        port1.to_itype(layout.dbu),
        port2.to_itype(layout.dbu),
        int(bend90_radius / layout.dbu),
        int(start_straight / layout.dbu),
        int(end_straight / layout.dbu),
    )


def route_manhattan(
    port1: Port | kdb.Trans,
    port2: Port | kdb.Trans,
    bend90_radius: int,
    start_straight: int,
    end_straight: int,
    max_tries: int = 20,
) -> list[kdb.Point]:
    """Calculate manhattan route using um based points.

    Doesn't use any non-90° bends.

    Args:
        port1: Transformation of start port.
        port2: Transformation of end port.
        bend90_radius: The radius or (symmetrical) dimension of 90° bend. [dbu]
        start_straight: Minimum straight after the starting port. [dbu]
        end_straight: Minimum straight before the end port. [dbu]
        max_tries: Maximum number of tries to calculate a manhattan route before
        giving up

    Returns:
        route: Calculated route in points in dbu.
    """
    t1 = port1.dup() if isinstance(port1, kdb.Trans) else port1.trans.dup()
    t2 = port2.dup() if isinstance(port2, kdb.Trans) else port2.trans.dup()
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
        and abs(tv.y) > bend90_radius + end_straight
        and tv.x >= bend90_radius + start_straight
        and end_straight == 0
        and start_straight == 0
    ):
        return [p1, p1 + (t1 * kdb.Vector(tv.x, 0)), p2]

    if t2.disp == t1.disp and t2.angle == t1.angle:
        raise ValueError("Identically oriented ports cannot be connected")

    box = kdb.Box(
        (t1 * kdb.Trans(0, False, start_straight, 0)).disp.to_p(),
        (t2 * kdb.Trans(0, False, end_straight, 0)).disp.to_p(),
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
    t1 *= kdb.Trans(start_straight + bend90_radius, 0)
    tv = t1.inverted() * (t2.disp - t1.disp)

    points = [p1]
    end_points = None

    if t2.angle == t1.angle == 0 and tv.x < 0 and abs(tv.y) >= 2 * bend90_radius:
        t2 *= kdb.Trans(end_straight, 0)
        if end_straight == 0:
            end_points = [p2]
        else:
            end_points = [t2 * _p, p2]
    else:
        t2 *= kdb.Trans(end_straight + bend90_radius, 0)
        end_points = [t2 * _p, p2]

    t1.inverted() * (t2.disp - t1.disp)

    for i in range(max_tries):
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

    return points


@config.logger.catch(reraise=True)
def route_bundle_manhattan(
    start_ports: list[Port],
    end_ports: list[Port] | list[kdb.Trans],
    bend90_radius: int,
    spacings: list[int],
    start_straights: list[int],
    end_straights: list[int],
    max_tries: int = 20,
) -> list[list[kdb.Point]]:
    """Calculate manhattan route using um based points.

    Doesn't use any non-90° bends.

    Args:
        start_ports: Transformation of start port.
        end_ports: Transformation of end port.
        bend90_radius: The radius or (symmetrical) dimension of 90° bend. [dbu]
        spacings: Spacings between each route on the bundle path
        start_straights: Minimum straight after the starting port. [dbu]
        end_straights: Minimum straight before the end port. [dbu]
        max_tries: Maximum number of tries to calculate a manhattan route before
        giving up

    Returns:
        route: Calculated route in points in dbu.
    """
    if len(start_ports) == 0 or len(start_ports) != len(end_ports):
        raise ValueError(
            f"Length of start_ports ({len(start_ports)}) and"
            f" end_ports ({len(end_ports)}) must be the same and not 0"
        )
    start_trans = [p if isinstance(p, kdb.Trans) else p.trans for p in start_ports]
    end_trans = [p if isinstance(p, kdb.Trans) else p.trans for p in end_ports]

    sv = [trans.disp for trans in start_trans]
    ev = [trans.disp for trans in end_trans]

    s_xmin = min(v.x for v in sv)
    e_xmin = min(v.x for v in ev)
    s_xmax = max(v.x for v in sv)
    e_xmax = max(v.x for v in ev)
    s_ymin = min(v.y for v in sv)
    e_ymin = min(v.y for v in ev)
    s_ymax = max(v.y for v in sv)
    e_ymax = max(v.y for v in ev)

    s_box = kdb.Box(s_xmin, s_ymin, s_xmax, s_ymax)
    e_box = kdb.Box(e_xmin, e_ymin, e_xmax, e_ymax)

    s_box.enlarge(bend90_radius)
    e_box.enlarge(bend90_radius)

    if not (kdb.Region(s_box) & kdb.Region(e_box)).is_empty():
        raise ValueError(
            "The bounding boxes of the two port collections are too close"
            " to each other to safely use bundle routing."
        )

    route_points: list[list[kdb.Point]] = []

    # avg_center_start = kdb.Vector(0, 0)
    # for t in start_trans:
    #     avg_center_start += t.disp
    # avg_center_start /= len(start_trans)

    start_mean = kdb.Vector(
        *[
            int(x)
            for x in np.mean(
                [[t.disp.x, t.disp.y] for t in start_trans], axis=0, dtype=int
            )
        ]
    )
    end_mean = kdb.Vector(
        *[
            int(x)
            for x in np.mean(
                [[t.disp.x, t.disp.y] for t in end_trans], axis=0, dtype=int
            )
        ]
    )

    start_angle_count = {i: 0 for i in range(4)}
    end_angle_count = {i: 0 for i in range(4)}

    for t in start_trans:
        start_angle_count[t.angle] += 1
    for t in end_trans:
        end_angle_count[t.angle] += 1

    best_start_angle = [
        t for t in sorted(start_angle_count.items(), key=lambda x: x[0])
    ]
    best_end_angle = [t for t in sorted(end_angle_count.items(), key=lambda x: x[0])]

    v = end_mean - start_mean

    match v.x:
        case x if x == 0:
            x_dir = None
        case x if x > 0:
            x_dir = 0
        case _:
            x_dir = 2

    match v.y:
        case y if y == 0:
            y_dir = None
        case y if y > 0:
            y_dir = 1
        case y if y < 0:
            y_dir = 3

    if best_start_angle[1][1] == 0:
        dir = best_end_angle[0][0]
        # all the start ports point in the same direction, so do the standard bundle

        def sort_port(
            index: int, port: Port, dir: Literal[-1, 1], attr: Literal["x", "y"]
        ) -> int:
            return dir * getattr(port.trans, attr)  # type: ignore[no-any-return]

        match dir:
            case 0:
                _ports: list[tuple[int, Port]] = list(
                    sorted(
                        enumerate(start_ports), key=partial(sort_port, dir=-1, attr="y")
                    )
                )
                left_ports: list[Port] = []
                left_spacings: list[int] = []
                right_ports: list[Port] = []
                right_spacings: list[int] = []

                # for index, _port in _ports:
                #     if _port.trans.disp.y < start_mean.y:
                #         left_ports.append[_port]
            case 1:
                _ports = sorted(
                    enumerate(start_ports), key=partial(sort_port, dir=1, attr="x")
                )
            case 2:
                _ports = sorted(
                    enumerate(start_ports), key=partial(sort_port, dir=1, attr="y")
                )
            case _:
                _ports = sorted(
                    enumerate(start_ports), key=partial(sort_port, dir=-1, attr="x")
                )

    # choose a good direction for the bundle

    return route_points

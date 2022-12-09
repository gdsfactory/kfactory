from typing import List, Optional, Union

import numpy as np

from .. import kdb
from ..kcell import KLib, Port
from ..utils.geo import clean_points

__all__ = ["route_manhattan", "route_manhattan_180"]


def droute_manhattan_180(
    port1: kdb.DTrans,
    port2: kdb.DTrans,
    bend90_radius: float,
    bend180_radius: float,
    start_straight: float,
    end_straight: float,
    layout: KLib | kdb.Layout,
) -> List[kdb.Point]:
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
) -> List[kdb.Point]:
    """Calculates a  hopefully minimal distance manhattan route (no s-bends)"""
    t1 = port1.dup() if isinstance(port1, kdb.Trans) else port1.trans.dup()
    t2 = port2.dup() if isinstance(port2, kdb.Trans) else port2.trans.dup()

    _p = kdb.Point(0, 0)

    p1 = t1 * _p
    p2 = t2 * _p

    if t2.disp == t1.disp and t2.angle == t1.angle:
        raise ValueError("Identically oriented ports cannot be connected")

    t1 *= kdb.Trans(0, False, start_straight, 0)

    tv = t1.inverted() * (t2.disp - t1.disp)

    if (t2.angle - t1.angle) % 4 == 2 and tv.y == 0 and tv.x > 0:
        return [p1, p2]

    t2 *= kdb.Trans(0, False, start_straight, 0)

    points = [p1] if start_straight != 0 else []
    end_points = [t2 * _p, p2] if end_straight != 0 else [p2]
    tv = t1.inverted() * (t2.disp - t1.disp)
    if tv.abs() == 0:
        return points + end_points
    if (t2.angle - t1.angle) % 4 == 2 and tv.x > 0 and tv.y == 0:
        return points + end_points
    t1 = port1.dup() if isinstance(port1, kdb.Trans) else port1.trans.dup()
    raise NotImplementedError(
        "Case not supportedt yet. Please open an issue if you believe this is an error and needs to be implemented ;)"
    )


def droute_manhattan(
    port1: kdb.DTrans,
    port2: kdb.DTrans,
    bend90_radius: int,
    start_straight: int,
    end_straight: int,
    layout: KLib | kdb.Layout,
) -> List[kdb.Point]:
    return route_manhattan(
        port1.to_itype(layout.dbu),
        port2.to_itype(layout.dbu),
        int(bend90_radius / layout.dbu),
        int(start_straight / layout.dbu),
        int(end_straight / layout.dbu),
    )


def route_manhattan(
    port1: Union[Port, kdb.Trans],
    port2: Union[Port, kdb.Trans],
    bend90_radius: int,
    start_straight: int,
    end_straight: int,
    in_dbu: bool = True,
    layout: Optional[KLib | kdb.Layout] = None,
) -> List[kdb.Point]:
    """Calculates a  hopefully minimal distance manhattan route (no s-bends)"""

    t1 = port1.dup() if isinstance(port1, kdb.Trans) else port1.trans.dup()
    t2 = port2.dup() if isinstance(port2, kdb.Trans) else port2.trans.dup()
    _p = kdb.Point(0, 0)

    p1 = t1 * _p
    p2 = t2 * _p
    tv = t1.inverted() * (t2.disp - t1.disp)
    if (t2.angle - t1.angle) % 4 == 2 and tv.y == 0 and tv.x > 0:
        return [p1, p2]
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

    # we want a straight start and have to add a bend radius if
    t1 *= kdb.Trans(start_straight + bend90_radius, 0)
    tv = t1.inverted() * (t2.disp - t1.disp)

    points = [p1]
    end_points = None

    if t2.angle == t1.angle == 0 and tv.x < 0 and abs(tv.y) >= 2 * bend90_radius:
        t2 *= kdb.Trans(end_straight, 0)
        end_points = [p2] if end_straight == 0 else [t2 * _p, p2]
    else:
        t2 *= kdb.Trans(end_straight + bend90_radius, 0)
        end_points = [t2 * _p, p2]

    v = t1.inverted() * (t2.disp - t1.disp)

    for _ in range(10):
        tv = t1.inverted() * (t2.disp - t1.disp)
        if tv.abs() == 0:
            break
        if (t2.angle - t1.angle) % 4 == 2 and tv.x > 0 and tv.y == 0:
            break
        points.append(t1 * _p)
        tv = t1.inverted() * (t2.disp - t1.disp)
    clean_points(points)
    points.extend(end_points)
    clean_points(points)

    return points

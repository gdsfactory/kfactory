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
    spacing: int,
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
        spacing: Spacing between each route on the bundle path.
            (with regard to the main layer)
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
            case 1:
                _ports = list(
                    sorted(
                        enumerate(start_ports), key=partial(sort_port, dir=1, attr="x")
                    )
                )
            case 2:
                _ports = list(
                    sorted(
                        enumerate(start_ports), key=partial(sort_port, dir=1, attr="y")
                    )
                )
            case _:
                _ports = list(
                    sorted(
                        enumerate(start_ports), key=partial(sort_port, dir=-1, attr="x")
                    )
                )

        left_ports: list[Port] = []
        right_ports: list[Port] = []

        for index, _port in _ports:
            if _port.trans.disp.y < start_mean.y:
                left_ports.append(_port)
            else:
                right_ports.append(_port)

        start_routes: list[list[kdb.Point]] = []

        min_start = 0
        for _port in reversed(list(left_ports)):
            if dir % 2:
                sx = start_mean.x
                if len(_ports) % 2:
                    pass
                if _port.x == sx:
                    start_routes.append(
                        [_port.trans.disp.to_p(), _port.trans.disp.to_p()]
                    )
                elif abs(_port.x - sx) < 2 * bend90_radius:
                    raise NotImplementedError()
                else:
                    pts = [
                        _port.trans.disp.to_p(),
                        _port.trans.disp.to_p()
                        + (
                            kdb.Trans(dir, False, 0, 0)
                            * kdb.Vector(bend90_radius + min_start, 0)
                        ),
                    ]
                    # pts.append(
                    #     kdb.Point(
                    #         pts[-1].x,
                    #         # ,  # fix
                    #     )
                    # )

            else:
                pass

    # choose a good direction for the bundle

    return route_points


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


def backbone2bundle(
    backbone: list[kdb.Point],
    port_widths: list[int],
    spacing: int,
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

    width = sum(port_widths) + (len(port_widths) - 1) * spacing

    x = -width // 2

    for pw in port_widths:
        x += pw // 2

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

        x += spacing + pw // 2
        pts.append(_pts)

    return pts


def route_ports_to_bundle(
    ports_to_route: list[tuple[kdb.Trans, int]],
    bend_radius: int,
    bbox: kdb.Box,
    spacing: int,
    bundle_base_point: kdb.Point,
    start_straight: int = 0,
) -> dict[kdb.Trans, list[kdb.Point]]:
    dir = ports_to_route[0][0].angle
    bundle_dir = (dir + 2) % 4
    sign = -1 if dir // 2 else 1
    # var_sign = -1 if dir % 2 else 1
    attr = "x" if dir % 2 else "y"
    var_attr = "y" if dir % 2 else "x"

    base_attr: int = getattr(bundle_base_point, attr)
    base_var_attr: int = getattr(bundle_base_point, var_attr)

    def sort_port(port_width: tuple[kdb.Trans, int]) -> int:
        return sign * getattr(port_width[0].disp, attr)  # type: ignore[no-any-return]

    sorted_ports = list(sorted(ports_to_route, key=sort_port))
    port_widths = [p[1] for p in sorted_ports]
    width = sum(port_widths) + (len(port_widths) - 1) * spacing

    port_dict: dict[kdb.Trans, list[kdb.Point]] = {}

    min_var: int = base_var_attr
    print(f"{min_var=}")

    ### Determine the start_straight (from bundle point of view)

    _attr = base_attr - sign * width // 2

    _start_straight = 0

    _last_sign = False

    straights: list[int] = []

    current_straights: list[int] = []
    _old_dir = None
    for i, (_port, _width) in enumerate(sorted_ports):
        _attr += sign * _width // 2
        _port_attr = sign * getattr(_port.disp, attr)
        diff = sign * (_port_attr - _attr)

        match diff:
            case 0:
                _dir = 0
            case x if x > 0:
                _dir = 1
            case _:
                _dir = -1

        if not _old_dir:
            _old_dir = _dir

        changed = (_dir != _old_dir) or (_dir == 0)

        print(f"{straights=}")
        print(f"{current_straights=}")

        if abs(diff) < 2 * bend_radius:
            if changed:
                current_straights.append(_width)
                # _old_dir = -_dir
            else:
                if _old_dir == 1:
                    _s = 0
                    append_list: list[int] = []
                    for _w in reversed(current_straights[1:]):
                        append_list.insert(0, _s)
                        _s += _w + spacing
                    append_list.insert(0, _s)
                    straights.extend(append_list)
                    current_straights = [_width]
                else:
                    _s = 0
                    append_list = []
                    for _w in current_straights[:-1]:
                        append_list.append(_s)
                        _s += _w + spacing
                    append_list.append(_s)
                    straights.extend(append_list)
                    current_straights = [_width]
                _old_dir = -_dir
        else:
            if changed:
                if _old_dir == 1:
                    _s = 0
                    append_list = []
                    for _w in reversed(current_straights[1:]):
                        append_list.insert(0, _s)
                        _s += _w + spacing
                    append_list.insert(0, _s)
                    straights.extend(append_list)
                    current_straights = []
                else:
                    _s = 0
                    append_list = []
                    for _w in current_straights[:-1]:
                        append_list.append(_s)
                        _s += _w + spacing
                    append_list.append(_s)
                    straights.extend(append_list)
                    current_straights = []
                _old_dir = _dir
            else:
                current_straights.append(_width)
    if _old_dir == 1:
        _s = 0
        append_list = []
        for _w in reversed(current_straights):
            append_list.insert(0, _s)
            _s += _w + spacing
        append_list.insert(0, _s)
    else:
        _s = 0
        append_list = []
        for _w in current_straights:
            append_list.append(_s)
            _s += _w + spacing
        append_list.append(_s)
    straights.extend(append_list)

    # _minmax = max if sign else min
    _minmax = max  # if dir in [0, 2, 3] else max

    ### Calculate the ideal minimum point of the bundle wrt the ports
    _attr = base_attr - sign * width // 2
    for i, (_port, _width) in enumerate(sorted_ports):
        _attr += sign * _width // 2
        _port_attr = sign * getattr(_port.disp, attr)
        _port_var_attr = sign * getattr(_port.disp, var_attr)
        _start_straight = straights[i]
        _dist = abs(_port_attr - _attr)
        _var_dist = abs(min_var - _port_var_attr)
        if _dist >= 2 * bend_radius:
            min_var = _minmax(
                _port_var_attr + sign * 2 * bend_radius + sign * _start_straight,
                min_var,
            )
            print(f"{_port_var_attr+ sign * 2 * bend_radius+ sign * _start_straight=}")
            print(f"{min_var=}")
            print(f"{_minmax.__name__=}")
        elif _dist == 0:
            _start_straight = 0
            print(f"{min_var=}")
            print(f"{_minmax.__name__=}")
            min_var = _minmax(_port_var_attr, min_var)
        else:
            min_var = _minmax(
                _port_var_attr + sign * 4 * bend_radius + sign * _start_straight,
                min_var,
            )
            print(f"{_port_var_attr+ sign * 2 * bend_radius+ sign * _start_straight=}")
            print(f"{min_var=}")
    bundle_point = bundle_base_point.dup()
    setattr(bundle_point, var_attr, min_var)

    w = -sign * width // 2
    for (_port, _width), straight in zip(sorted_ports, straights):
        w += sign * _width // 2
        v = kdb.Vector(bundle_point)
        setattr(v, attr, getattr(v, attr) + sign * w)
        t2 = kdb.Trans(bundle_dir, False, v)

        print(f"{v=}")
        print(f"{bundle_dir=}")
        print(f"{t2=}")

        port_dict[_port] = route_manhattan(
            t2,
            _port,
            bend_radius,
            # start_straight=0,
            end_straight=0,
            start_straight=straight,
            # end_straight=straight,
        )
        w += sign * _width // 2 + spacing

    print(f"{bundle_point=}")

    return port_dict


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

    # sign = -1 if _ports_dir // 2 else 1

    # start_side = (
    #     max([sign * getattr(trans.disp, _attr) for trans, _ in existing_side_ports])
    #     if existing_side_ports
    #     else None
    # )

    ports_to_route.sort(key=lambda port_width: -dir * (_inv_rot * port_width[0]).disp.y)
    # side_ports = existing_side_ports.copy()
    # side_ports.sort(key= lambda port_width)

    [print((_inv_rot * port_width[0]).disp) for port_width in ports_to_route]
    start_straight = 0

    for trans, width in ports_to_route:
        _trans = kdb.Trans(_ports_dir, False, trans.disp.x, trans.disp.y)
        pts_dict[trans] = base_pts(_trans, start_straight=start_straight)
        start_straight += width + spacing

    return pts_dict

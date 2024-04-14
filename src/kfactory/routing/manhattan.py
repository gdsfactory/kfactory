"""Can calculate manhattan routes based on ports/transformations."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import InitVar, dataclass, field
from typing import Literal, Protocol

import numpy as np

from .. import kdb
from ..conf import config
from ..enclosure import clean_points
from ..kcell import KCLayout, Port

__all__ = [
    "route_manhattan",
    "route_manhattan_180",
    "clean_points",
    "ManhattanRoutePathFunction",
    "ManhattanRoutePathFunction180",
]


class ManhattanRoutePathFunction(Protocol):
    """Minimal signature of a manhattan function."""

    def __call__(
        self,
        port1: Port | kdb.Trans,
        port2: Port | kdb.Trans,
        bend90_radius: int,
        start_straight: int,
        end_straight: int,
    ) -> list[kdb.Point]:
        """Minimal kwargs of a manhattan route function."""
        ...


class ManhattanRoutePathFunction180(Protocol):
    """Minimal signature of a manhattan function with 180° bend routing."""

    def __call__(
        self,
        port1: Port | kdb.Trans,
        port2: Port | kdb.Trans,
        bend90_radius: int,
        bend180_radius: int,
        start_straight: int,
        end_straight: int,
    ) -> list[kdb.Point]:
        """Minimal kwargs of a manhattan route function with 180° bend."""
        ...


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


_p = kdb.Point()


@dataclass
class ManhattanRouterSide:
    router: ManhattanRouter
    _t: kdb.Trans
    _ot: kdb.Trans
    pts: list[kdb.Point]

    def __post_init__(self) -> None:
        self.pts = self.pts.copy()
        if not self.pts:
            self.pts.append(self._t.disp.to_p())

    @property
    def t(self) -> kdb.Trans:
        return self._t

    @t.setter
    def t(self, __t: kdb.Trans) -> None:
        self._t.assign(__t)

    @property
    def tv(self) -> kdb.Vector:
        return self.t.inverted() * (self._ot.disp - self.t.disp)

    @property
    def ta(self) -> Literal[0, 1, 2, 3]:
        return (self._ot.angle - self.t.angle) % 4  # type: ignore[return-value]

    def right(self) -> None:
        self.pts.append(
            (self.t * kdb.Trans(0, False, self.router.bend90_radius, 0)) * _p
        )
        self.t *= kdb.Trans(
            3, False, self.router.bend90_radius, -self.router.bend90_radius
        )

    def left(self) -> None:
        self.pts.append(
            (self.t * kdb.Trans(0, False, self.router.bend90_radius, 0)) * _p
        )
        self.t *= kdb.Trans(
            1, False, self.router.bend90_radius, self.router.bend90_radius
        )

    def straight(self, d: int) -> None:
        self.t *= kdb.Trans(0, False, max(d, 0), 0)

    def straight_nobend(self, d: int) -> None:
        self.t *= kdb.Trans(0, False, max(d - self.router.bend90_radius, 0), 0)

    def reset(self) -> None:
        self.pts = [self.t.disp.to_p()]


@dataclass
class ManhattanRouter:
    bend90_radius: int
    start: ManhattanRouterSide = field(init=False)
    end: ManhattanRouterSide = field(init=False)
    start_transformation: InitVar[kdb.Trans]
    end_transformation: InitVar[kdb.Trans] = kdb.Trans()
    start_straight: InitVar[int] = 0
    end_straight: InitVar[int] = 0
    width: int = 0
    start_points: InitVar[list[kdb.Point]] = field(default=[])
    end_points: InitVar[list[kdb.Point]] = field(default=[])

    def __post_init__(
        self,
        start_transformation: kdb.Trans,
        end_transformation: kdb.Trans,
        start_straight: int,
        end_straight: int,
        start_points: list[kdb.Point],
        end_points: list[kdb.Point],
    ) -> None:
        assert start_straight >= 0, "Start straight must be >= 0"
        assert end_straight >= 0, "End straight must be >= 0"

        _start = start_transformation.dup()
        _start.mirror = False
        _end = end_transformation.dup()
        _end.mirror = False

        self.start = ManhattanRouterSide(
            router=self,
            _t=_start,
            _ot=_end,
            pts=start_points,
        )
        self.end = ManhattanRouterSide(
            router=self,
            _t=_end,
            _ot=_start,
            pts=end_points,
        )
        self.start.straight(start_straight)
        self.end.straight(end_straight)

    def auto_route(
        self,
        max_try: int = 20,
        test_collisions: bool = True,
        straight_s_bend_strategy: Literal["short", "long"] = "short",
    ) -> list[kdb.Point]:
        if max_try <= 0:
            raise ValueError("Router was not able to find a possible route")
        tv = self.start.tv
        x = tv.x
        y = tv.y
        y_abs = abs(y)
        ta = self.start.ta
        match ta:
            case 0:
                match x, y:
                    case _ if y_abs >= 2 * self.bend90_radius:
                        if x > 0:
                            self.start.straight(x)
                        if y > 0:
                            self.start.left()
                        else:
                            self.start.right()
                        return self.auto_route(max_try - 1)
                    case _:
                        # ports are close to each other ,so need to
                        # route like a P
                        if x > 0:
                            # the straight part of the P is on our side
                            self.start.straight(2 * self.bend90_radius - x)
                        if y > 0:
                            self.start.right()
                        else:
                            self.start.left()
                        return self.auto_route(max_try - 1)
            case 2:
                match y:
                    case 0:
                        return self.finish()
                    case y if y_abs < 2 * self.bend90_radius:
                        if straight_s_bend_strategy == "short":
                            self.start.right() if y > 0 else self.start.left()
                        else:
                            self.start.left() if y > 0 else self.start.right()
                        return self.auto_route(max_try - 1)
                    case _:
                        self.start.left() if y > 0 else self.start.right()
                        return self.auto_route(max_try - 1)
            case _:
                # 1/3 cases are just one to the other
                # with flipped y value and right/left flipped
                if ta == 3:
                    right = self.start.right
                    left = self.start.left
                    _y = y
                else:
                    right = self.start.left
                    left = self.start.right
                    _y = -y
                if x >= self.bend90_radius and _y >= self.bend90_radius:
                    # straight forward can connect with a single bend
                    self.start.straight(x - self.bend90_radius)
                    left()
                    return self.finish()
                if x >= 3 * self.bend90_radius:
                    # enough space to route but need to first make sure we have enough
                    # vertical way (seen from t1)
                    right()
                    return self.auto_route(max_try - 1)
                if _y >= 3 * self.bend90_radius:
                    # enough to route in the other side
                    self.start.straight(self.bend90_radius + x)
                    left()
                    return self.auto_route(max_try - 1)
                if _y <= -self.bend90_radius or x <= 0:
                    self.start.straight(x + self.bend90_radius)
                    right()
                    return self.auto_route(max_try - 1)

                # attempt small routing
                if x < self.bend90_radius and y_abs < self.bend90_radius:
                    config.logger.warning(
                        "route is too small, potential collisions: "
                        f"{self.start=}; {self.end=}; {self.start.pts=}"
                    )
                    right()
                    self.start.straight(self.bend90_radius - _y)
                    left()
                else:
                    right()
                return self.auto_route(max_try - 1)

        raise ValueError(
            "Route couldn't find a possible route, please open an issue on Github."
            f"{self.start=!r}, {self.end=!r}, {self.bend90_radius=}\n"
            f"{self.ta=}, {self.tv=!r}\n"
            f"{self.pts=}"
        )

    def collisions(self, log_errors: bool = True) -> kdb.Edges:
        p_start = self.start.pts[0]
        edges = kdb.Edges()
        has_collisions = False
        collisions = kdb.Edges()

        for p in self.start.pts[1:]:
            _edges = kdb.Edges([kdb.Edge(p_start, p)])
            potential_collisions = edges.interacting(_edges)
            if not potential_collisions.is_empty():
                has_collisions = True
                collisions += potential_collisions

        if has_collisions and log_errors:
            config.logger.error(
                f"Router {self.start.t=}, {self.end.t=}, {self.start.pts=},"
                f" {self.end.pts=} has collisions in the manhattan route.\n"
                f"{collisions=}"
            )
        return collisions

    def finish(self) -> list[kdb.Point]:
        tv = self.start.tv
        if self.start.ta != 2:
            raise ValueError(
                "Route is not finished. The transformations must be facing each other"
            )
        if tv.y != 0:
            raise ValueError(
                "Route  is not finished. The transformations are not properly aligned: "
                f"Vector (as seen from t1): {tv.x=}, {tv.y=}"
            )
        if self.end.pts[-1] != self.start.pts[-1]:
            self.start.pts.extend(reversed(self.end.pts))
        return self.start.pts


@dataclass(kw_only=True)
class ManhattanRouter180(ManhattanRouter):
    bend180_radius: int

    def __post_init__(
        self,
        start_transformation: kdb.Trans,
        end_transformation: kdb.Trans,
        start_straight: int,
        end_straight: int,
        start_points: list[kdb.Point],
        end_points: list[kdb.Point],
    ) -> None:
        super().__post_init__(
            start_transformation=start_transformation,
            end_transformation=end_transformation,
            start_straight=start_straight,
            end_straight=end_straight,
            start_points=start_points,
            end_points=end_points,
        )
        if self.bend180_radius < self.bend90_radius:
            raise AttributeError(
                "A router with a bend180_radius bigger than bend90_radius is "
                "non-funcitonal, It will always route with 90° bends."
            )

    def right_around(self) -> None:
        self.start.pts.append(self.start.t.disp.to_p())
        self.start.t *= kdb.Trans(2, False, 0, -self.bend180_radius)
        self.start.pts.append(self.start.t.disp.to_p())

    def left_around(self) -> None:
        self.start.pts.append(self.start.t.disp.to_p())
        self.start.t *= kdb.Trans(2, False, 0, self.bend180_radius)
        self.start.pts.append(self.start.t.disp.to_p())

    def right_around_end(self) -> None:
        self.start.pts.append(self.end.t.disp.to_p())
        self.end.t *= kdb.Trans(2, False, 0, -self.bend180_radius)
        self.start.pts.append(self.end.t.disp.to_p())

    def left_around_end(self) -> None:
        self.start.pts.append(self.end.t.disp.to_p())
        self.end.t *= kdb.Trans(2, False, 0, self.bend180_radius)
        self.start.pts.append(self.end.t.disp.to_p())


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
        t1 = port1 if isinstance(port1, kdb.Trans) else port1.trans
        t2 = port2.dup() if isinstance(port2, kdb.Trans) else port2.trans
        _start_straight = start_straight
        _end_straight = end_straight
    else:
        t2 = port1 if isinstance(port1, kdb.Trans) else port1.trans
        t1 = port2 if isinstance(port2, kdb.Trans) else port2.trans
        _end_straight = start_straight
        _start_straight = end_straight

    router = ManhattanRouter(
        bend90_radius=bend90_radius,
        start_transformation=t1,
        end_transformation=t2,
        start_straight=_start_straight,
        end_straight=_end_straight,
    )

    pts = router.auto_route()
    if invert:
        pts.reverse()

    return pts


def route_smart(
    start_ports: Sequence[Port | kdb.Trans],
    end_ports: Sequence[Port | kdb.Trans],
    bend90_radius: int,
    separation: int,
    start_straights: list[int] = [0],
    end_straights: list[int] = [0],
    invert: Sequence[bool] = [False],
    start_bbox: kdb.Box | None = None,
    end_bbox: kdb.Box | None = None,
    widths: list[int] | None = None,
) -> list[ManhattanRouter]:
    length = len(start_ports)

    assert len(end_ports) == length, (
        f"Length of starting ports {len(start_ports)=} does not match length of "
        f"end ports {len(end_ports)}"
    )

    if len(start_straights) == 1:
        start_straights = [start_straights[0]] * length
    if len(end_straights) == 1:
        end_straights = [end_straights[0]] * length
    if len(invert) == 1:
        invert = [invert[0]] * length

    assert len(start_straights) == length, (
        "start_straights does have too few or too"
        f"many elements {len(start_straights)=}, {len(start_straights)=}"
    )
    assert len(end_straights) == length, (
        "end_straights does have too few or too"
        f"many elements {len(start_straights)=}, {len(start_straights)=}"
    )

    start_ts = [p.trans if isinstance(p, Port) else p for p in start_ports]
    end_ts = [p.trans if isinstance(p, Port) else p for p in end_ports]
    if start_bbox is None:
        p1 = start_ts[0].disp.to_p()
        start_bbox = kdb.Box(p1, p1)
        for t in start_ts:
            start_bbox += t.disp.to_p()
    if end_bbox is None:
        p1 = start_ts[0].disp.to_p()
        end_bbox = kdb.Box(p1, p1)
        for t in end_ts:
            end_bbox += t.disp.to_p()

    routers: list[ManhattanRouter] = []
    # dbr = 2 * bend90_radius

    for ts, te, ss, es in zip(start_ts, end_ts, start_straights, end_straights):
        routers.append(
            ManhattanRouter(
                bend90_radius=bend90_radius,
                start_transformation=ts,
                end_transformation=te,
                start_straight=ss,
                end_straight=es,
            )
        )

    router_bboxes: list[kdb.Box] = [
        kdb.Box(router.start.t.disp.to_p(), router.end.t.disp.to_p())
        for router in routers
    ]
    complete_bbox = router_bboxes[0].dup().enlarged(separation + routers[0].width)
    bundled_bboxes: list[kdb.Box] = [complete_bbox]
    bundled_routers: list[list[ManhattanRouter]] = [[routers[0]]]
    bundle = bundled_routers[0]
    bundle_bbox = complete_bbox.dup()
    for router, bbox in zip(routers[1:], router_bboxes[1:]):
        dbrbox = bbox.enlarged(separation + router.width // 2)
        overlap_box = dbrbox & bundle_bbox

        if overlap_box.empty():
            overlap_complete = dbrbox & complete_bbox
            if overlap_complete.empty():
                bundled_bboxes.append(bundle_bbox)
                bundle_bbox = bbox.dup()
                bundle = [router]
                bundled_routers.append(bundle)
            else:
                for i in range(len(bundled_bboxes)):
                    bundled_bbox = bundled_bboxes[i]
                    if not (dbrbox & bundled_bbox).empty():
                        bb = bundled_bboxes[i]
                        bundled_routers[i].append(router)
                        bundled_bboxes[i] = bb + bbox.enlarged(router.width // 2)
                        break
        else:
            bundle.append(router)
            bundle_bbox += bbox

    merge_bboxes: list[tuple[int, int]] = []
    for i in range(len(bundled_bboxes)):
        for j in range(0, i):
            if not (bundled_bboxes[j] & bundled_bboxes[i]).empty():
                merge_bboxes.append((i, j))
                break
    for i, j in reversed(merge_bboxes):
        bundled_bboxes[j] = bundled_bboxes[i] + bundled_bboxes[j]
        bundled_routers[j] = bundled_routers[i] + bundled_routers[j]
    for i, _ in reversed(merge_bboxes):
        del bundled_bboxes[i]
        del bundled_routers[i]
    for router_bundle in bundled_routers:
        sorted_routers = _sort_routers(router_bundle)

        # simple (maybe error-prone) way to determine the ideal routing angle
        angle = router_bundle[0].end.t.angle

        disp_to_bbox = kdb.Trans(-angle, False, 0, 0) * (
            start_bbox.center().to_v() - router_bundle[0].end.t.disp
        )

        if disp_to_bbox.x > 0:
            target_angle = (angle - 2) % 4
        else:
            target_angle = angle

        router_groups: list[tuple[int, list[ManhattanRouter]]] = []
        group_angle: int | None = None
        current_group: list[ManhattanRouter] = []
        for router in sorted_routers:
            _ang = router.start.t.angle
            if _ang != group_angle:
                if group_angle is not None:
                    router_groups.append(
                        ((group_angle - target_angle) % 4, current_group)
                    )
                group_angle = _ang
                current_group = []
            current_group.append(router)
        else:
            if group_angle is not None:
                router_groups.append(((target_angle - group_angle) % 4, current_group))

        total_bbox = start_bbox

        if len(router_groups) > 1:
            passes0 = False
            start_angle = router_groups[0][0]
            end_angle = router_groups[-1][0]

            if end_angle <= start_angle and end_angle != 0:
                passes0 = True
            else:
                passes0 = False

            if passes0:
                angle = router_groups[0][0]
                routers_clockwise: list[ManhattanRouter]
                routers_clockwise = router_groups[0][1].copy()
                for i in range(1, len(router_groups)):
                    new_angle, new_routers = router_groups[i]
                    a = angle
                    if routers_clockwise:
                        while a != new_angle:
                            a = (a + 1) % 4
                            total_bbox += _route_to_side(
                                routers=[router.start for router in routers_clockwise],
                                clockwise=True,
                                bbox=start_bbox,
                                separation=separation,
                            )
                    if new_angle <= angle:
                        break
                    routers_clockwise.extend(new_routers)
                    angle = new_angle
                angle = router_groups[-1][0]
                routers_anticlockwise: list[ManhattanRouter]
                routers_anticlockwise = router_groups[-1][1].copy()
                if router_groups[-1][0] != 0:
                    for i in range(len(router_groups) - 2, -1, -1):
                        new_angle, new_routers = router_groups[i]
                        a = angle
                        if routers_anticlockwise:
                            while a != new_angle:
                                a = (a - 1) % 4
                                total_bbox += _route_to_side(
                                    routers=[
                                        router.start for router in routers_anticlockwise
                                    ],
                                    clockwise=False,
                                    bbox=start_bbox,
                                    separation=separation,
                                )
                        if new_angle == 0:
                            routers_anticlockwise.extend(new_routers)
                            break
                        if new_angle >= angle:
                            break
                        routers_anticlockwise.extend(new_routers)
                        angle = new_angle
            else:
                if router_groups[0][1][0].end.tv.y > 0:
                    for i in range(len(router_groups) - 1, -1):
                        new_angle, new_routers = router_groups[i]
                        a = angle
                        if routers_anticlockwise:
                            while a != new_angle:
                                a = (a + 1) % 4
                                total_bbox += _route_to_side(
                                    routers=[
                                        router.start for router in routers_anticlockwise
                                    ],
                                    clockwise=False,
                                    bbox=start_bbox,
                                    separation=separation,
                                )
                        if new_angle == 0 or (new_angle - angle) % 4 <= 0:
                            break
                        routers_anticlockwise.extend(new_routers)
                        angle = new_angle
                else:
                    for i in range(len(router_groups) - 1, -1):
                        new_angle, new_routers = router_groups[i]
                        a = angle
                        if routers_anticlockwise:
                            while a != new_angle:
                                a = (a + 1) % 4
                                total_bbox += _route_to_side(
                                    routers=[
                                        router.start for router in routers_anticlockwise
                                    ],
                                    clockwise=False,
                                    bbox=start_bbox,
                                    separation=separation,
                                )
                        if new_angle == 0 or (new_angle - angle) % 4 <= 0:
                            break
                        routers_anticlockwise.extend(new_routers)
                        angle = new_angle
        route_to_bbox([router.start for router in router_bundle], total_bbox)
        route_loosely(routers, separation=separation)

    return routers


def route_to_bbox(routers: Iterable[ManhattanRouterSide], bbox: kdb.Box) -> None:
    for router in routers:
        match router.t.angle:
            case 0:
                router.straight(bbox.right - router.t.disp.x)
            case 1:
                router.straight(bbox.top - router.t.disp.y)
            case 2:
                router.straight(-bbox.left + router.t.disp.x)
            case 3:
                router.straight(-bbox.bottom + router.t.disp.y)


def route_loosely(routers: Sequence[ManhattanRouter], separation: int) -> None:
    if routers:
        sign = np.sign(routers[0].start.tv.y)
        group = [routers[0]]
        i = 1
        sorted_rotuers = _sort_routers(routers)
        while i != len(routers):
            r = sorted_rotuers[i]
            _s = np.sign(r.start.tv.y)
            if sign == _s:
                group.append(r)
            else:
                match sign:
                    case -1:
                        start_straight = 0
                        for j, _r in enumerate(group):
                            _r.start.straight(start_straight)
                            _r.auto_route()
                            start_straight += separation + _r.width
                    case _:
                        start_straight = 0
                        for j, _r in enumerate(reversed(group)):
                            _r.start.straight(start_straight)
                            _r.auto_route()
                            start_straight += separation + _r.width
                group = [r]
                sign = _s
            i += 1
        match sign:
            case -1:
                start_straight = 0
                for j, _r in enumerate(group):
                    _r.start.straight(start_straight)
                    _r.auto_route()
                    start_straight += separation + _r.width
            case _:
                start_straight = 0
                for j, _r in enumerate(reversed(group)):
                    _r.start.straight(start_straight)
                    _r.auto_route()
                    start_straight += separation + _r.width


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


def _sort_routers(routes: Sequence[ManhattanRouter]) -> Sequence[ManhattanRouter]:
    angle = routes[0].end.t.angle
    match angle:
        case 0:
            return sorted(routes, key=lambda route: -route.end.t.disp.y)
        case 1:
            return sorted(routes, key=lambda route: route.end.t.disp.x)
        case 2:
            return sorted(routes, key=lambda route: route.end.t.disp.y)
        case _:
            return sorted(routes, key=lambda route: -route.end.t.disp.x)


def _route_to_side(
    routers: list[ManhattanRouterSide],
    clockwise: bool,
    bbox: kdb.Box,
    separation: int,
    until_bbox: bool = False,
) -> kdb.Box:
    bbox = bbox.enlarged(separation // 2)

    side = routers[0].t.angle

    def _sort_route(router: ManhattanRouterSide) -> tuple[int, int]:  # type:ignore[return]
        _side = (router.t.angle - side + 1) % 4
        match _side, (kdb.Trans(-router.t.angle, False, 0, 0) * router.t.disp).y:
            case 0, y:
                return _side, -y
            case 1, y if router.tv.y < 0:
                return _side, y
            case 1, y:
                return _side, -y
            case 2, y:
                return _side, y
            case _, y:
                return _side, y

    sorted_rs = sorted(routers, key=_sort_route)
    for rs in sorted_rs:
        hw1 = rs.router.width // 2
        hw2 = rs.router.width - hw1
        match rs.t.angle:
            case 0:
                s = bbox.right + hw1 - rs.t.disp.x - rs.router.bend90_radius
            case 1:
                s = bbox.top + hw1 - rs.t.disp.y - rs.router.bend90_radius
            case 2:
                s = rs.t.disp.x - (bbox.left - hw1) - rs.router.bend90_radius
            case _:
                s = rs.t.disp.y - (bbox.bottom - hw1) - rs.router.bend90_radius
        rs.straight(s)
        if clockwise:
            x = rs.tv.x
            if rs.ta == 3:
                if x >= rs.router.bend90_radius:
                    rs.straight_nobend(x)
                elif x > -rs.router.bend90_radius:
                    rs.straight(rs.router.bend90_radius + x)
            rs.left()
            bbox += rs.t * kdb.Point(0, -hw2 - separation)
        else:
            x = rs.tv.x
            if rs.ta == 1:
                if x >= rs.router.bend90_radius:
                    rs.straight_nobend(x)
                elif x > -rs.router.bend90_radius:
                    rs.straight(rs.router.bend90_radius + x)
            rs.right()
            bbox += rs.t * kdb.Point(0, hw2 + separation)

    return bbox


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

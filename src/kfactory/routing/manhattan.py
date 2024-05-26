"""Can calculate manhattan routes based on ports/transformations."""

from __future__ import annotations

from collections import defaultdict
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
    """A simple manhattan point router.

    Keeps track of the target and stores the points and transformation of the past
    routing.
    """

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
    """Class to store state of a routing between two ports or transformations."""

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
        straight_s_bend_strategy: Literal["short", "long"] = "short",
    ) -> list[kdb.Point]:
        """Automatically determine a route from start to end.

        Args:
            max_try: Maximum number of routing steps it can take. This is a security
                measure to stop infinite loops. This should never trigger an error.
            straight_s_bend_strategy: When emulating an s-bend (build a large S out of
                90deg bends), use the short or the longer route.
        """
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

    def collisions(
        self, log_errors: None | Literal["warn", "error"] = "error"
    ) -> tuple[kdb.Edges, kdb.Edges]:
        """Finds collisions.

        A collision is if the router crosses itself in it's route (`self.start.pts`).

        Args:
            log_errors: sends the an error or a warning to the kfactory logger if not
                `None`.

        Returns:
            tuple containing the collisions and all edges of the router
        """
        p_start = self.start.pts[1]
        edges = kdb.Edges()
        last_edge = kdb.Edge(self.start.pts[0], p_start)
        has_collisions = False
        collisions = kdb.Edges()

        for p in self.start.pts[2:]:
            new_edge = kdb.Edge(p_start, p)
            _edges = kdb.Edges([new_edge])
            potential_collisions = edges.interacting(other=_edges)

            if not potential_collisions.is_empty():
                has_collisions = True
                collisions.join_with(potential_collisions).join_with(_edges)
            edges.insert(last_edge)
            last_edge = new_edge
            p_start = p

        edges.insert(last_edge)

        if has_collisions and log_errors is not None:
            match log_errors:
                case "error":
                    config.logger.error(
                        f"Router {self.start.t=}, {self.end.t=}, {self.start.pts=},"
                        f" {self.end.pts=} has collisions in the manhattan route.\n"
                        f"{collisions=}"
                    )
                case "warn":
                    config.logger.warning(
                        f"Router {self.start.t=}, {self.end.t=}, {self.start.pts=},"
                        f" {self.end.pts=} has collisions in the manhattan route.\n"
                        f"{collisions=}"
                    )
        return collisions, edges

    def finish(self) -> list[kdb.Point]:
        """Determines whether the routing was successful.

        If it was successful and the start and end are facing each other,
        store all the points of `self.end.pts` in `self.start.pts` in reversed
        order.
        """
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
    bboxes: list[kdb.Box] | None = None,
    widths: list[int] | None = None,
    sort_ports: bool = False,
    waypoints: list[kdb.Point] | None = None,
    split_back: bool = True,
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

    assert len(start_straights) == length, (
        "start_straights does have too few or too"
        f"many elements {len(start_straights)=}, {len(start_straights)=}"
    )
    assert len(end_straights) == length, (
        "end_straights does have too few or too"
        f"many elements {len(start_straights)=}, {len(start_straights)=}"
    )
    if length == 0:
        return []

    start_ts = [p.trans if isinstance(p, Port) else p for p in start_ports]
    end_ts = [p.trans if isinstance(p, Port) else p for p in end_ports]
    if widths is None:
        widths = [p.width if isinstance(p, Port) else 0 for p in start_ports]
    box_region = kdb.Region()
    if bboxes:
        for box in bboxes:
            box_region.insert(box)
            box_region.merge()
    if sort_ports:
        if bboxes is None:
            config.logger.warning(
                "No bounding boxes were given but route_smart was configured to reorder"
                " the ports. Without bounding boxes route_smart cannot determine "
                "whether ports belong to specific bundles or they should build one "
                "bounding box. Therefore, all ports will be assigned to one bounding"
                " box. If this is the intended behavior, pass `[]` to the bboxes "
                "parameter to disable this warning."
            )
            bboxes = []
        default_start_bundle: list[kdb.Trans] = []
        start_bundles: dict[kdb.Box, list[kdb.Trans]] = defaultdict(list)

        b = kdb.Box()
        for ts in start_ts:
            p = ts.disp.to_p()
            if b.contains(p):
                start_bundles[b].append(ts)
            else:
                for i, _b in enumerate(bboxes):
                    if _b.contains(p):
                        start_bundles[_b].append(ts)
                        b = _b
                        break
                else:
                    default_start_bundle.append(ts)
        if default_start_bundle:
            b = kdb.Box()
            for ts in default_start_bundle:
                b += ts.disp.to_p()
            start_bundles[b] = default_start_bundle

        default_end_bundle: list[kdb.Trans] = []
        end_bundles: dict[kdb.Box, list[kdb.Trans]] = defaultdict(list)

        for ts in end_ts:
            p = ts.disp.to_p()
            if b.contains(p):
                end_bundles[b].append(ts)
            else:
                for i, _b in enumerate(bboxes):
                    if _b.contains(p):
                        end_bundles[_b].append(ts)
                        b = _b
                        break
                else:
                    default_end_bundle.append(ts)
        if default_end_bundle:
            b = kdb.Box()
            for ts in default_end_bundle:
                b += ts.disp.to_p()
            end_bundles[b] = default_end_bundle

        # try to match start_bundles with end_bundles which have the same size

        matches: list[tuple[kdb.Box, kdb.Box, int]] = []
        allowed_matches: list[tuple[kdb.Box, int]] = [
            (b, len(bundle)) for b, bundle in end_bundles.items()
        ]

        for box, s_bundle in sorted(
            start_bundles.items(), key=lambda item: (item[0].left, item[0].bottom)
        ):
            bl = len(s_bundle)
            bc = box.center()
            potential_matches = [x for x in allowed_matches if x[1] == bl]

            if potential_matches:
                match = min(
                    potential_matches,
                    key=lambda x: (bc - x[0].center()).abs(),
                )
                matches.append((box, match[0], bl))
                allowed_matches.remove(match)
            else:
                raise ValueError(
                    "The sorting algorithm currently doesn't support if multiple "
                    "bundles are conflicting with each other. Offending bundle at"
                    " starting port positions "
                    f"{box.left=},{box.bottom=},{box.right=},{box.top=}[dbu]"
                )
            start_ts = []
            end_ts = []
            for start_box, end_box, _bl in matches:
                end_bundle = end_bundles[end_box]
                start_bundle = start_bundles[start_box]
                v = start_box.center() - end_box.center()
                end_angle = end_bundle[0].angle
                match end_angle:
                    case 0:
                        if v.x < 0:
                            end_ts.extend(
                                _sort_transformations(
                                    end_bundle,
                                    target_side=0,
                                    box=end_box,
                                    split=1,
                                    clockwise=False,
                                )
                            )
                            start_ts.extend(
                                _sort_transformations(
                                    transformations=start_bundle,
                                    target_side=0,
                                    box=start_box,
                                    split=1,
                                    clockwise=True,
                                )
                            )
                        else:
                            end_ts.extend(
                                _sort_transformations(
                                    transformations=end_bundle,
                                    target_side=0,
                                    box=end_box,
                                    split=1,
                                    clockwise=False,
                                )
                            )
                            start_ts.extend(
                                _sort_transformations(
                                    transformations=start_bundle,
                                    target_side=2,
                                    box=start_box,
                                    split=1,
                                    clockwise=True,
                                )
                            )
                    case 1:
                        if v.y < 0:
                            end_ts.extend(
                                _sort_transformations(
                                    end_bundle,
                                    target_side=1,
                                    box=end_box,
                                    split=1,
                                    clockwise=False,
                                )
                            )
                            start_ts.extend(
                                _sort_transformations(
                                    transformations=start_bundle,
                                    target_side=1,
                                    box=start_box,
                                    split=1,
                                    clockwise=True,
                                )
                            )
                        else:
                            end_ts.extend(
                                _sort_transformations(
                                    transformations=end_bundle,
                                    target_side=1,
                                    box=end_box,
                                    split=1,
                                    clockwise=False,
                                )
                            )
                            start_ts.extend(
                                _sort_transformations(
                                    transformations=start_bundle,
                                    target_side=3,
                                    box=start_box,
                                    split=1,
                                    clockwise=True,
                                )
                            )
                    case 2:
                        if v.x > 0:
                            end_ts.extend(
                                _sort_transformations(
                                    end_bundle,
                                    target_side=2,
                                    box=end_box,
                                    split=1,
                                    clockwise=False,
                                )
                            )
                            start_ts.extend(
                                _sort_transformations(
                                    transformations=start_bundle,
                                    target_side=2,
                                    box=start_box,
                                    split=1,
                                    clockwise=True,
                                )
                            )
                        else:
                            end_ts.extend(
                                _sort_transformations(
                                    transformations=end_bundle,
                                    target_side=2,
                                    box=end_box,
                                    split=1,
                                    clockwise=False,
                                )
                            )
                            start_ts.extend(
                                _sort_transformations(
                                    transformations=start_bundle,
                                    target_side=0,
                                    box=start_box,
                                    split=1,
                                    clockwise=True,
                                )
                            )
                    case 3:
                        if v.y > 0:
                            end_ts.extend(
                                _sort_transformations(
                                    end_bundle,
                                    target_side=3,
                                    box=end_box,
                                    split=1,
                                    clockwise=False,
                                )
                            )
                            start_ts.extend(
                                _sort_transformations(
                                    transformations=start_bundle,
                                    target_side=3,
                                    box=start_box,
                                    split=1,
                                    clockwise=True,
                                )
                            )
                        else:
                            end_ts.extend(
                                _sort_transformations(
                                    transformations=end_bundle,
                                    target_side=3,
                                    box=end_box,
                                    split=1,
                                    clockwise=False,
                                )
                            )
                            start_ts.extend(
                                _sort_transformations(
                                    transformations=start_bundle,
                                    target_side=1,
                                    box=start_box,
                                    split=1,
                                    clockwise=True,
                                )
                            )

    all_routers: list[ManhattanRouter] = []

    for ts, te, w, ss, es in zip(
        start_ts, end_ts, widths, start_straights, end_straights
    ):
        all_routers.append(
            ManhattanRouter(
                bend90_radius=bend90_radius,
                start_transformation=ts,
                end_transformation=te,
                start_straight=ss,
                end_straight=es,
                width=w,
            )
        )

    router_bboxes: list[kdb.Box] = [
        kdb.Box(router.start.t.disp.to_p(), router.end.t.disp.to_p())
        for router in all_routers
    ]
    complete_bbox = router_bboxes[
        0
    ].dup()  # .enlarged(separation + all_routers[0].width)
    bundled_bboxes: list[kdb.Box] = []
    bundled_routers: list[list[ManhattanRouter]] = [[all_routers[0]]]
    bundle = bundled_routers[0]
    bundle_bbox = complete_bbox.dup()

    for router, bbox in zip(all_routers[1:], router_bboxes[1:]):
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
    bundled_bboxes.append(bundle_bbox)

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

        r = router_bundle[0]
        end_angle = r.end.t.angle
        re = router_bundle[-1]
        start_bbox = kdb.Box(r.start.t.disp.to_p(), re.start.t.disp.to_p())
        end_bbox = kdb.Box(r.end.t.disp.to_p(), re.end.t.disp.to_p())
        for r in router_bundle:
            start_bbox += r.start.t.disp.to_p()
            end_bbox += r.end.t.disp.to_p()
            if r.end.t.angle != end_angle:
                raise ValueError(
                    "All ports at the target (end) must have the same angle. "
                    f"{router.start.t=}/{router.end.t=}"
                )

        if box_region:
            start_bbox = (
                box_region.interacting(kdb.Region(start_bbox)).bbox() + start_bbox
            )
            end_bbox = box_region.interacting(kdb.Region(end_bbox)).bbox() + end_bbox
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
                router_groups.append(((group_angle - target_angle) % 4, current_group))

        total_bbox = start_bbox

        if len(router_groups) > 1:
            angle = router_groups[0][0]
            routers_clockwise: list[ManhattanRouter]
            routers_clockwise = router_groups[0][1].copy()
            if router_groups[0][0] != 0:
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
            route_to_bbox([router.start for router in sorted_routers], total_bbox)
            if waypoints is None:
                route_loosely(sorted_routers, separation=separation, end_bbox=end_bbox)
            else:
                route_loosely(sorted_routers, separation=separation, end_bbox=end_bbox)

        else:
            routers = router_groups[0][1]
            r = routers[0]
            match (target_angle - r.start.t.angle) % 4:
                case 1:
                    total_bbox = _route_to_side(
                        [r.start for r in routers],
                        clockwise=True,
                        bbox=total_bbox,
                        separation=separation,
                    )
                case 2:
                    total_bbox = _route_to_side(
                        [r.start for r in routers],
                        clockwise=routers[0].start.tv.y > 0,
                        bbox=total_bbox,
                        separation=separation,
                    )
                    total_bbox = _route_to_side(
                        [r.start for r in routers],
                        clockwise=routers[0].start.tv.y > 0,
                        bbox=total_bbox,
                        separation=separation,
                    )
                case 3:
                    total_bbox = _route_to_side(
                        [r.start for r in routers],
                        clockwise=False,
                        bbox=total_bbox,
                        separation=separation,
                    )
            if waypoints is None:
                route_to_bbox([router.start for router in router_bundle], total_bbox)
            else:
                route_to_bbox([router.start for router in router_bundle], total_bbox)
            route_loosely(routers, separation=separation, end_bbox=end_bbox)

    return all_routers


def route_to_bbox(routers: Iterable[ManhattanRouterSide], bbox: kdb.Box) -> None:
    if not bbox.empty():
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


def route_loosely(
    routers: Sequence[ManhattanRouter],
    separation: int,
    start_bbox: kdb.Box = kdb.Box(),
    end_bbox: kdb.Box = kdb.Box(),
) -> None:
    """Route two port banks (all ports same direction) to the end.

    This will not result in a tight bundle but use all the space available and
    choose the shortest path.
    """
    router_start_box = start_bbox.dup()
    router_end_box = end_bbox.dup()
    if routers:
        x_sign = np.sign(routers[0].end.tv.x)
        _y = 0
        for router in routers:
            _y += router.end.tv.y

        sorted_routers = _sort_routers(routers)
        if x_sign == -1:
            end_bbox = _route_to_side(
                routers=[r.end for r in routers],
                clockwise=_y > 0,
                bbox=end_bbox,
                separation=separation,
                until_bbox=True,
            )
            end_bbox = _route_to_side(
                routers=[r.end for r in routers],
                clockwise=_y > 0,
                bbox=end_bbox,
                separation=separation,
                until_bbox=True,
            )

        sign = np.sign(routers[0].start.tv.y)
        group = [routers[0]]
        group_box = kdb.Box(
            routers[0].start.t.disp.to_p(), routers[0].end.t.disp.to_p()
        )
        i = 1
        while i != len(routers):
            r = sorted_routers[i]
            _s = np.sign(r.start.tv.y)
            box = kdb.Box(r.start.t.disp.to_p(), r.end.t.disp.to_p())
            if sign == _s and not (box & group_box).empty():
                group.append(r)
                group_box += box
            else:
                match sign:
                    case -1:
                        for j, _r in enumerate(group):
                            delta = kdb.Point(
                                separation + _r.width, 0
                            )  # start_straight equivalent
                            route_to_bbox([_r.start], router_start_box)
                            router_start_box += _r.start.t * delta
                            route_to_bbox([_r.end], router_end_box)
                            if _r.end.tv.x <= _r.bend90_radius:
                                router_end_box += _r.end.t * delta
                            _r.auto_route(straight_s_bend_strategy="short")
                    case _:
                        for j, _r in enumerate(reversed(group)):
                            delta = kdb.Point(
                                separation + _r.width, 0
                            )  # start_straight equivalent
                            route_to_bbox([_r.start], router_start_box)
                            router_start_box += _r.start.t * delta
                            route_to_bbox([_r.end], router_end_box)
                            if _r.end.tv.x <= _r.bend90_radius:
                                router_end_box += _r.end.t * delta
                            _r.auto_route(straight_s_bend_strategy="short")
                group = [r]
                group_box = box
                sign = _s
                router_start_box = start_bbox.dup()
                router_end_box = end_bbox.dup()
            i += 1
        match sign:
            case -1:
                for j, _r in enumerate(group):
                    delta = kdb.Point(
                        separation + _r.width, 0
                    )  # start_straight equivalent
                    route_to_bbox([_r.start], router_start_box)
                    router_start_box += _r.start.t * delta
                    route_to_bbox([_r.end], router_end_box)
                    if _r.end.tv.x <= _r.bend90_radius:
                        router_end_box += _r.end.t * delta
                    _r.auto_route(straight_s_bend_strategy="short")
            case _:
                for j, _r in enumerate(reversed(group)):
                    delta = kdb.Point(
                        separation + _r.width, 0
                    )  # start_straight equivalent
                    route_to_bbox([_r.start], router_start_box)
                    router_start_box += _r.start.t * delta
                    route_to_bbox([_r.end], router_end_box)
                    if _r.end.tv.x <= _r.bend90_radius:
                        router_end_box += _r.end.t * delta
                    _r.auto_route(straight_s_bend_strategy="short")


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


def _sort_routers(routers: Sequence[ManhattanRouter]) -> Sequence[ManhattanRouter]:
    angle = routers[0].end.t.angle
    match angle:
        case 0:
            return sorted(routers, key=lambda route: -route.end.t.disp.y)
        case 1:
            return sorted(routers, key=lambda route: route.end.t.disp.x)
        case 2:
            return sorted(routers, key=lambda route: route.end.t.disp.y)
        case _:
            return sorted(routers, key=lambda route: -route.end.t.disp.x)


def _sort_transformations(
    transformations: Sequence[kdb.Trans],
    target_side: int,
    box: kdb.Box,
    split: Literal[-1, 0, 1],
    clockwise: bool,
) -> list[kdb.Trans]:
    trans_by_dir: dict[int, list[kdb.Trans]] = defaultdict(list)
    for trans in transformations:
        trans_by_dir[trans.angle].append(trans)
    back_angle = (target_side + 2) % 4
    back = trans_by_dir[back_angle]
    start_transformations: list[kdb.Trans] = []
    end_transformations: list[kdb.Trans] = []
    if back:
        match split:
            case -1:
                start_transformations = _sort_trans_bank(back)
                end_transformations = []
            case 0:
                # this is a rather primitive algorithm to split the transformations on
                # the backside, it just splits them in the middle. This could be smarter
                # by properly choosing where the transformations need to go
                match back_angle:
                    case 0:
                        start_transformations = _sort_trans_bank(
                            [t for t in back if t.disp.y < box.center().y]
                        )
                        end_transformations = _sort_trans_bank(
                            [t for t in back if t.disp.y >= box.center().y]
                        )
                    case 1:
                        start_transformations = _sort_trans_bank(
                            [t for t in back if t.disp.x < box.center().x]
                        )
                        end_transformations = _sort_trans_bank(
                            [t for t in back if t.disp.x >= box.center().x]
                        )
                    case 2:
                        start_transformations = _sort_trans_bank(
                            [t for t in back if t.disp.y < box.center().y]
                        )
                        end_transformations = _sort_trans_bank(
                            [t for t in back if t.disp.y >= box.center().y]
                        )
                    case 3:
                        start_transformations = _sort_trans_bank(
                            [t for t in back if t.disp.x > box.center().x]
                        )
                        end_transformations = _sort_trans_bank(
                            [t for t in back if t.disp.x >= box.center().x]
                        )
                end_transformations.reverse()
            case 1:
                start_transformations = []
                end_transformations = _sort_trans_bank(back)
                # end_transformations.reverse()
    for angle in [-1, 0, 1]:
        start_transformations.extend(
            _sort_trans_bank(trans_by_dir[(target_side + angle) % 4])
        )

    transformations = start_transformations + end_transformations
    if not clockwise:
        transformations.reverse()
    return transformations


def _sort_trans_bank(transformations: Sequence[kdb.Trans]) -> list[kdb.Trans]:
    if transformations:
        angle = transformations[0].angle
        match angle:
            case 0:
                return list(sorted(transformations, key=lambda t: t.disp.y))
            case 1:
                return list(sorted(transformations, key=lambda t: -t.disp.x))
            case 2:
                return list(sorted(transformations, key=lambda t: -t.disp.y))
            case _:
                return list(sorted(transformations, key=lambda t: t.disp.x))
    else:
        return []


def _route_to_side(
    routers: list[ManhattanRouterSide],
    clockwise: bool,
    bbox: kdb.Box,
    separation: int,
    until_bbox: bool = False,
) -> kdb.Box:
    # bbox = bbox.enlarged(separation // 2)
    bbox = bbox.dup()

    def _sort_route(router: ManhattanRouterSide) -> int:
        y = (kdb.Trans(-router.t.angle, False, 0, 0) * router.t.disp).y
        if clockwise:
            return -y
        else:
            return y

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

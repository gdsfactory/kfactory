"""Can calculate manhattan routes based on ports/transformations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    ParamSpec,
    Protocol,
    TypedDict,
    cast,
    overload,
)

import klayout.db as kdb
import numpy as np

from ..conf import (
    ANGLE_90,
    ANGLE_180,
    ANGLE_270,
    MIN_POINTS_FOR_CLEAN,
    MIN_WAYPOINTS_FOR_ROUTING,
    logger,
)
from ..port import BasePort, Port
from ..routing.steps import Step, Steps, Straight

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from ..kcell import DKCell, KCell
    from ..layout import KCLayout

__all__ = [
    "ManhattanRoutePathFunction",
    "ManhattanRoutePathFunction180",
    "clean_points",
    "clean_points",
    "route_manhattan",
    "route_manhattan_180",
    "route_smart",
]

P = ParamSpec("P")


class ManhattanRoutePathFunction(Protocol):
    """Minimal signature of a manhattan function."""

    def __call__(
        self,
        port1: Port | kdb.Trans,
        port2: Port | kdb.Trans,
        bend90_radius: int,
        start_steps: Sequence[Step] | None = None,
        end_steps: Sequence[Step] | None = None,
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
        start_steps: list[Step] | None = None,
        end_steps: list[Step] | None = None,
    ) -> list[kdb.Point]:
        """Minimal kwargs of a manhattan route function with 180° bend."""
        ...


class ManhattanBundleRoutingFunction(Protocol):
    def __call__(
        self,
        *,
        start_ports: Sequence[BasePort | kdb.Trans],
        end_ports: Sequence[BasePort | kdb.Trans],
        starts: Sequence[Sequence[Step]],
        ends: Sequence[Sequence[Step]],
        widths: Sequence[int] | None = None,
        **kwargs: Any,
    ) -> list[ManhattanRouter]: ...


def droute_manhattan_180(
    port1: kdb.DTrans,
    port2: kdb.DTrans,
    bend90_radius: float,
    bend180_radius: float,
    start_straight: float,
    end_straight: float,
    layout: KCLayout,
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

    p = kdb.Point(0, 0)

    p1 = t1 * p
    p2 = t2 * p

    if t2.disp == t1.disp and t2.angle == t1.angle:
        raise ValueError("Identically oriented ports cannot be connected")

    tv = t1.inverted() * (t2.disp - t1.disp)

    if (t2.angle - t1.angle) % 4 == ANGLE_180 and tv.y == 0:
        if tv.x > 0:
            return [p1, p2]
        if tv.x == 0:
            return []

    t1 *= kdb.Trans(0, False, start_straight, 0)

    points = [p1] if start_straight != 0 else []
    end_points = [t2 * p, p2] if end_straight != 0 else [p2]
    tv = t1.inverted() * (t2.disp - t1.disp)
    if tv.abs() == 0:
        return points + end_points
    if (t2.angle - t1.angle) % 4 == ANGLE_180 and tv.x > 0 and tv.y == 0:
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
                start_steps=[],
                end_steps=[Straight(dist=end_straight)],
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
        [Straight(dist=round(start_straight / layout.dbu))],
        [Straight(dist=round(end_straight / layout.dbu))],
        invert=invert,
    )


_p = kdb.Point(0, 0)


@dataclass
class ManhattanRouterSide:
    """A simple manhattan point router.

    Keeps track of the target and stores the points and transformation of the past
    routing.
    """

    router: ManhattanRouter
    _t: kdb.Trans
    pts: list[kdb.Point]

    def __post_init__(self) -> None:
        self.pts = self.pts.copy()
        if not self.pts:
            self.pts.append(self._t.disp.to_p())

    @cached_property
    def other(self) -> ManhattanRouterSide:
        return self.router.end if self == self.router.start else self.router.start

    @property
    def t(self) -> kdb.Trans:
        return self._t

    @t.setter
    def t(self, __t: kdb.Trans, /) -> None:
        self._t.assign(__t)

    @property
    def tv(self) -> kdb.Vector:
        return self.t.inverted() * (self.other.t.disp - self.t.disp)

    @property
    def ta(self) -> Literal[0, 1, 2, 3]:
        return (self.other.t.angle - self.t.angle) % 4  # type: ignore[return-value]

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

    @property
    def path_length(self) -> int:
        pl: int = 0
        l_ = len(self.pts)
        if l_ > 0:
            p1 = self.pts[0]
            for i in range(1, l_):
                p2 = self.pts[i]
                pl += int((p2 - p1).length())
        return pl


@dataclass
class ManhattanRouter:
    """Class to store state of a routing between two ports or transformations."""

    bend90_radius: int
    start_transformation: kdb.Trans
    end_transformation: kdb.Trans
    start: ManhattanRouterSide = field(init=False)
    end: ManhattanRouterSide = field(init=False)
    start_steps: InitVar[Sequence[Step]] = field(default=[])
    end_steps: InitVar[Sequence[Step]] = field(default=[])
    width: int = 0
    start_points: InitVar[list[kdb.Point]] = field(default=[])
    end_points: InitVar[list[kdb.Point]] = field(default=[])
    finished: bool = False
    allow_sbends: bool = False

    def __post_init__(
        self,
        start_steps: int | Sequence[Step],
        end_steps: int | Sequence[Step],
        start_points: list[kdb.Point],
        end_points: list[kdb.Point],
    ) -> None:
        start = self.start_transformation.dup()
        start.mirror = False
        end = self.end_transformation.dup()
        end.mirror = False

        self.start = ManhattanRouterSide(
            router=self,
            _t=start,
            pts=start_points,
        )
        self.end = ManhattanRouterSide(
            router=self,
            _t=end,
            pts=end_points,
        )
        if isinstance(start_steps, int):
            if start_steps < 0:
                raise ValueError("Start straight must be >= 0")
            self.start.straight(start_steps)
        else:
            Steps(list(start_steps)).execute(self.start)
        if isinstance(end_steps, int):
            if end_steps < 0:
                raise ValueError("End straight must be >= 0")
            self.end.straight(end_steps)
        else:
            Steps(list(end_steps)).execute(self.end)

    @property
    def path_length(self) -> int:
        if not self.finished:
            raise ValueError(
                "Router is not finished yet, path_length will be inaccurate."
            )
        return self.start.path_length

    def auto_route(
        self,
        max_try: int = 20,
        straight_s_bend_strategy: Literal["short", "long"] = "short",
        bbox: kdb.Box | None = None,
    ) -> list[kdb.Point]:
        """Automatically determine a route from start to end.

        Args:
            max_try: Maximum number of routing steps it can take. This is a security
                measure to stop infinite loops. This should never trigger an error.
            straight_s_bend_strategy: When emulating an s-bend (build a large S out of
                90deg bends), use the short or the longer route.
        """
        if self.finished:
            return self.start.pts
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
                        if self.allow_sbends:
                            return self.finish()
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
                if ta == ANGLE_270:
                    right = self.start.right
                    left = self.start.left
                    y_ = y
                else:
                    right = self.start.left
                    left = self.start.right
                    y_ = -y
                if x >= self.bend90_radius and y_ >= self.bend90_radius:
                    # straight forward can connect with a single bend
                    self.start.straight(x - self.bend90_radius)
                    left()
                    return self.finish()
                if x >= 3 * self.bend90_radius:
                    # enough space to route but need to first make sure we have enough
                    # vertical way (seen from t1)
                    right()
                    return self.auto_route(max_try - 1)
                if y_ >= 3 * self.bend90_radius:
                    # enough to route in the other side
                    self.start.straight(self.bend90_radius + x)
                    left()
                    return self.auto_route(max_try - 1)
                if y_ <= -self.bend90_radius or x <= 0:
                    self.start.straight(x + self.bend90_radius)
                    right()
                    return self.auto_route(max_try - 1)

                # attempt small routing
                if x < self.bend90_radius and y_abs < self.bend90_radius:
                    logger.warning(
                        "route is too small, potential collisions: "
                        f"{self.start=}; {self.end=}; {self.start.pts=}"
                    )
                    right()
                    self.start.straight(self.bend90_radius - y_)
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
        self, log_errors: Literal["warn", "error"] | None = "error"
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
            edges_ = kdb.Edges([new_edge])
            potential_collisions = edges.interacting(other=edges_)

            if not potential_collisions.is_empty():
                has_collisions = True
                collisions.join_with(potential_collisions).join_with(edges_)
            edges.insert(last_edge)
            last_edge = new_edge
            p_start = p

        edges.insert(last_edge)

        if has_collisions and log_errors is not None:
            match log_errors:
                case "error":
                    logger.error(
                        f"Router {self.start.t=}, {self.end.t=}, {self.start.pts=},"
                        f" {self.end.pts=} has collisions in the manhattan route.\n"
                        f"{collisions=}"
                    )
                case "warn":
                    logger.warning(
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
        if self.start.ta != ANGLE_180:
            raise ValueError(
                "Route is not finished. The transformations must be facing each other"
            )
        if tv.y != 0:
            if not self.allow_sbends:
                raise ValueError(
                    "Route  is not finished. The transformations are not properly "
                    f"aligned: Vector (as seen from t1): {tv.x=}, {tv.y=}"
                )
            if self.start.t.disp.to_p() != self.start.pts[-1]:
                self.start.pts.append(self.start.t.disp.to_p())
        if self.end.pts[-1] != self.start.pts[-1]:
            self.start.pts.extend(reversed(self.end.pts))
        else:
            self.start.pts.extend(reversed(self.end.pts[:-1]))
        self.end.pts = []
        self.finished = True
        return self.start.pts


def route_manhattan(
    port1: Port | kdb.Trans,
    port2: Port | kdb.Trans,
    bend90_radius: int,
    start_steps: Sequence[Step] | None = None,
    end_steps: Sequence[Step] | None = None,
    max_tries: int = 20,
    invert: bool = False,
) -> list[kdb.Point]:
    """Calculate manhattan route using um based points.

    Only uses 90° bends.

    Args:
        port1: Transformation of start port.
        port2: Transformation of end port.
        bend90_radius: The radius or (symmetrical) dimension of 90° bend. [dbu]
        start_steps: Steps to take at the beginning of the route. [dbu]
        end_steps: Steps to take at the end of the route. [dbu]
        max_tries: Maximum number of tries to calculate a manhattan route before
            giving up
        invert: Invert the direction in which to route. In the normal behavior,
            route manhattan will try to take turns first. If true, it will try
            to route straight as long as possible

    Returns:
        route: Calculated route in dbu points.
    """
    if end_steps is None:
        end_steps = []
    if start_steps is None:
        start_steps = []
    if not invert:
        t1 = port1 if isinstance(port1, kdb.Trans) else port1.trans
        t2 = port2.dup() if isinstance(port2, kdb.Trans) else port2.trans
        start_steps_ = start_steps
        end_steps_ = end_steps
    else:
        t2 = port1 if isinstance(port1, kdb.Trans) else port1.trans
        t1 = port2 if isinstance(port2, kdb.Trans) else port2.trans
        end_steps_ = end_steps
        start_steps_ = end_steps

    router = ManhattanRouter(
        bend90_radius=bend90_radius,
        start_transformation=t1,
        end_transformation=t2,
        start_steps=start_steps_,
        end_steps=end_steps_,
    )

    pts = router.auto_route()
    if invert:
        pts.reverse()

    return pts


class PathMatchDict(TypedDict):
    angle: Literal[0, 1, 2, 3]
    pts: tuple[kdb.Point, kdb.Point]
    dl: int


def path_length_match_manhattan_route(
    *,
    c: KCell | DKCell,
    routers: Sequence[ManhattanRouter],
    start_ports: Sequence[BasePort],
    end_ports: Sequence[BasePort],
    bend90_radius: int | None = None,
    separation: int | None = None,
    path_length: int | None = None,
    **kwargs: Any,
) -> None:
    """Simple path length matching router postprocess.

    Args:
        c: KCell where the routes are placed into.
        routers: List of the manhattan routers to be modified.
        start_ports: The start ports of the routes.
        end_ports: The end ports of the routes.
        bend90_radius: Radius of a bend in the routes.
        separation: Separation between the routes.
        path_length: Match to a certain path length instead of the maximum
            of all routers.
        kwargs: Compatibility with type checkers. Throws an error if defined.
    """
    if kwargs:
        raise ValueError(
            f"Additional kwargs aren't supported in route_dual_rails {kwargs=}"
        )
    if bend90_radius is None:
        raise ValueError(
            "bend90_radius must be passed to the function, please pass it"
            " through the router_post_process_kwargs if using the "
            "generic route_bunle"
        )
    if separation is None:
        raise ValueError(
            "separation must be passed to the function, please pass it"
            " through the router_post_process_kwargs if using the "
            "generic route_bunle"
        )
    position = -1
    path_loops = 1

    path_length = path_length or max(r.path_length for r in routers)
    match_dict: dict[
        Literal[0, 1, 2, 3], list[tuple[ManhattanRouter, PathMatchDict]]
    ] = {
        0: [],
        1: [],
        2: [],
        3: [],
    }
    modify_pts: tuple[kdb.Point, kdb.Point]

    for router in routers:
        modify_pts = tuple(router.start.pts[-2:])  # type: ignore[assignment]
        v = modify_pts[1] - modify_pts[0]
        match (v.x, v.y):
            case (x, 0) if x > 0:
                angle: Literal[0, 1, 2, 3] = 0
            case (x, 0) if x < 0:
                angle = 2
            case (0, y) if y > 0:
                angle = 1
            case _:
                angle = 3

        match_dict[angle].append(
            (
                router,
                PathMatchDict(
                    angle=angle, pts=modify_pts, dl=path_length - router.path_length
                ),
            )
        )

    match_dict[0].sort(key=lambda t: t[1]["pts"][0].y)
    match_dict[1].sort(key=lambda t: -t[1]["pts"][0].x)
    match_dict[2].sort(key=lambda t: -t[1]["pts"][0].y)
    match_dict[3].sort(key=lambda t: t[1]["pts"][0].x)

    for angle, routers_settings in match_dict.items():
        router_group: list[tuple[ManhattanRouter, PathMatchDict]] = []
        if len(routers_settings) > 0:
            increasing: bool | None = None
            old_router, old_settings = routers_settings[0]
            router_group.append((old_router, old_settings))
            for router, settings in routers_settings[1:]:
                increasing_ = settings["dl"] > old_settings["dl"]
                if increasing is not None and increasing_ != increasing:
                    if increasing is True:
                        _place_dl_path_length(
                            routers=router_group,
                            angle=angle,
                            direction=1,
                            separation=separation,
                            bend90_radius=bend90_radius,
                            path_loops=path_loops,
                            path_length=path_length,
                            index=position,
                        )
                    elif increasing is False:
                        router_group.reverse()
                        _place_dl_path_length(
                            routers=router_group,
                            angle=angle,
                            direction=-1,
                            separation=separation,
                            bend90_radius=bend90_radius,
                            path_loops=path_loops,
                            path_length=path_length,
                            index=position,
                        )
                    router_group = [(router, settings)]
                else:
                    router_group.append((router, settings))
                old_router = router
                old_settings = settings
                increasing = increasing_
            if not increasing:
                router_group.reverse()
            _place_dl_path_length(
                routers=router_group,
                angle=angle,
                direction=1 if increasing else -1,
                separation=separation,
                bend90_radius=bend90_radius,
                path_loops=path_loops,
                path_length=path_length,
                index=position,
            )


def _place_dl_path_length(
    routers: list[tuple[ManhattanRouter, PathMatchDict]],
    angle: Literal[0, 1, 2, 3],
    direction: Literal[-1, 1],
    separation: int,
    bend90_radius: int,
    path_loops: int,
    path_length: int,
    index: int,
    position: Literal["center", "corner_start", "corner_end"] = "center",
) -> None:
    l_ = len(routers) - 1
    t_ = kdb.Trans(angle, False, 0, 0)
    tinv = t_.inverted()

    pmin = max((tinv * settings["pts"][0]).x for _, settings in routers)

    for i, (router, settings) in enumerate(routers):
        pmin += router.width // 2
        pts = settings["pts"]
        v = pts[1] - pts[0]
        vl = v.length()
        # if position not in [0, -1]:
        if vl < (2 + path_loops * 4) * bend90_radius:
            raise ValueError(
                f"Not enough space to place {path_loops} path length matching segments"
                f" on {pts[0]} to {pts[1]}"
            )

        t = kdb.Trans(
            angle, False, (t_ * kdb.Point(pmin, (tinv * pts[0]).y)).to_v()
        ) * kdb.Trans(kdb.Vector(bend90_radius, 0))
        if direction == 1:
            r = kdb.Trans(3, False, bend90_radius, -bend90_radius)
            rr = kdb.Trans(1, False, bend90_radius, bend90_radius)
        else:
            r = kdb.Trans(1, False, bend90_radius, bend90_radius)
            rr = kdb.Trans(3, False, bend90_radius, -bend90_radius)

        p = kdb.Point(bend90_radius, 0)

        dl = path_length - router.start.path_length

        pts_: list[kdb.Point] = []

        dl_ = kdb.Trans(dl // (path_loops * 2), 0)
        for _ in range(path_loops):
            pts_.append(t * p)
            t *= r
            t *= dl_
            pts_.append(t * p)
            t *= rr
            t *= kdb.Trans((l_ - i) * separation * 2, 0)
            pts_.append(t * p)
            t *= rr
            t *= dl_
            pts_.append(t * p)
            t *= r
        router.start.pts[index:index] = pts_
        pmin += separation + router.width // 2


def route_smart(
    *,
    start_ports: Sequence[BasePort | kdb.Trans],
    end_ports: Sequence[BasePort | kdb.Trans],
    widths: Sequence[int] | None = None,
    bend90_radius: int | None = None,
    separation: int | None = None,
    starts: Sequence[Sequence[Step]] = [],
    ends: Sequence[Sequence[Step]] = [],
    bboxes: Sequence[kdb.Box] | None = None,
    sort_ports: bool = False,
    waypoints: Sequence[kdb.Point] | kdb.Trans | None = None,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    allow_sbend: bool = False,
    **kwargs: Any,
) -> list[ManhattanRouter]:
    """Route around start or end bboxes (obstacles on the way not implemented yet).

    Args:
        start_ports: Ports where the routing should start.
        end_ports: Ports denoting the end of the routes. Per bundle (separate bbox
            from any other router bundles, i.e. routers are not interacting in any way
            with other routers of the other groups) they must have the same angle.
        bend90_radius: The radius for 90° bends in dbu.
        separation: Separation which should be maintained between the routers in dbu.
        starts: Add straights at the beginning of each route in dbu.
        ends: Add straights in dbu at the end of all routes.
        bboxes: List of bounding boxes used to denote obstacles.
        widths: Defines the width of the core material of each route.
        sort_ports: Whether to allow rearranging of ports given as inputs or outputs.
        waypoints: Bundle the ports and route them with minimal separation through
            the waypoints. The waypoints can either be a list of at least two points
            or a single transformation. If it's a transformation, the points will be
            routed through it as if it were a tunnel with length 0.
        bbox_routing: "minimal": only route to the bbox so that it can be safely routed
            around, but start or end bends might encroach on the bounding boxes when
            leaving them.
        allow_sbends: Allows the router to route the final pieces with sbends.
        kwargs: Additional kwargs. Compatibility for type checking. If any kwargs are
            passed an error is raised.
    Raises:
        ValueError: If the route cannot conform to bend radius and other routing
            restrictions a value error is raised.
    Returns:
        List of ManhattanRoute objects which contain all the instances in the route
        as well as the route info.
    """
    length = len(start_ports)
    if len(kwargs) > 0:
        raise ValueError(
            f"Additional args and kwargs are not allowed for route_smart.{kwargs=}"
        )

    if bend90_radius is None or separation is None:
        raise ValueError(
            "route_smart needs to have 'bend90_radius' and 'separation' "
            "defined as kwargs. Please pass them or if using a "
            "'route_bundle' function using this, make sure the bundle router"
            " has the kwargs."
        )

    assert len(end_ports) == length, (
        f"Length of starting ports {len(start_ports)=} does not match length of "
        f"end ports {len(end_ports)}"
    )

    assert len(starts) == length, (
        "start_straights does have too few or too"
        f"many elements {len(starts)=}, {len(starts)=}"
    )
    assert len(ends) == length, (
        "end_straights does have too few or too"
        f"many elements {len(starts)=}, {len(starts)=}"
    )
    if length == 0:
        return []

    start_ts = [p.get_trans() if isinstance(p, BasePort) else p for p in start_ports]
    end_ts = [p.get_trans() if isinstance(p, BasePort) else p for p in end_ports]
    if widths is None:
        widths = [
            p.cross_section.width if isinstance(p, BasePort) else 0 for p in start_ports
        ]
    box_region = kdb.Region()
    if bboxes:
        for box in bboxes:
            box_region.insert(box)
            box_region.merge()
    if sort_ports:
        if bboxes is None:
            logger.warning(
                "No bounding boxes were given but route_smart was configured to reorder"
                " the ports. Without bounding boxes route_smart cannot determine "
                "whether ports belong to specific bundles or they should build one "
                "bounding box. Therefore, all ports will be assigned to one bounding"
                " box. If this is the intended behavior, pass `[]` to the bboxes "
                "parameter to disable this warning."
            )
            bboxes = []
        w0 = widths[0]
        if not all(w == w0 for w in widths):
            raise NotImplementedError(
                f"'sort_ports=True' with variable widths is not supported: {widths=}"
            )
        if waypoints is not None:
            return _route_waypoints(
                waypoints=waypoints,
                widths=[w0 for _ in range(len(start_ts))],
                separation=separation,
                bend90_radius=bend90_radius,
                start_ts=start_ts,
                end_ts=end_ts,
                starts=starts,
                ends=ends,
                bboxes=bboxes,
                sort_ports=True,
                bbox_routing=bbox_routing,
                allow_sbends=allow_sbend,
            )
        default_start_bundle: list[kdb.Trans] = []
        start_bundles: dict[kdb.Box, list[kdb.Trans]] = defaultdict(list)
        mh_routers: list[ManhattanRouter] = []
        for s, s_t, e, e_t in zip(starts, start_ts, ends, end_ts, strict=False):
            mh_routers.append(
                ManhattanRouter(
                    bend90_radius=bend90_radius,
                    start_transformation=s_t,
                    end_transformation=e_t,
                    start_steps=s,
                    end_steps=e,
                    allow_sbends=allow_sbend,
                )
            )
        start_ts = [r.start.t for r in mh_routers]
        end_ts = [r.end.t for r in mh_routers]
        start_mapping = {r.start.t: r.start_transformation for r in mh_routers}
        end_mapping = {r.end.t: r.end_transformation for r in mh_routers}

        b = kdb.Box()
        for ts in start_ts:
            p = ts.disp.to_p()
            if b.contains(p):
                start_bundles[b].append(ts)
            else:
                for _b in bboxes:
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
                for _b in bboxes:
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
                    case _:
                        ...

        all_routers: list[ManhattanRouter] = []
        for ts, te, w, ss, es in zip(
            start_ts, end_ts, widths, starts, ends, strict=False
        ):
            start_t = start_mapping[ts]
            end_t = end_mapping[te]
            all_routers.append(
                ManhattanRouter(
                    bend90_radius=bend90_radius,
                    start_transformation=start_t,
                    end_transformation=end_t,
                    start_steps=ss,
                    end_steps=es,
                    width=w,
                    allow_sbends=allow_sbend,
                )
            )

    else:
        if waypoints is not None:
            return _route_waypoints(
                waypoints=waypoints,
                widths=widths,
                separation=separation,
                start_ts=start_ts,
                end_ts=end_ts,
                starts=starts,
                ends=ends,
                bboxes=bboxes,
                bbox_routing=bbox_routing,
                bend90_radius=bend90_radius,
                sort_ports=False,
                allow_sbends=allow_sbend,
            )

        all_routers = []
        for ts, te, w, ss, es in zip(
            start_ts, end_ts, widths, starts, ends, strict=False
        ):
            all_routers.append(
                ManhattanRouter(
                    bend90_radius=bend90_radius,
                    start_transformation=ts,
                    end_transformation=te,
                    start_steps=ss,
                    end_steps=es,
                    width=w,
                    allow_sbends=allow_sbend,
                )
            )

    router_bboxes: list[kdb.Box] = [
        kdb.Box(router.start.t.disp.to_p(), router.end.t.disp.to_p()).enlarged(
            router.width // 2
        )
        for router in all_routers
    ]
    complete_bbox = router_bboxes[0].dup()
    bundled_bboxes: list[kdb.Box] = []
    bundled_routers: list[list[ManhattanRouter]] = [[all_routers[0]]]
    bundle = bundled_routers[0]
    bundle_bbox = complete_bbox.dup()

    for router, bbox in zip(all_routers[1:], router_bboxes[1:], strict=False):
        dbrbox = bbox.enlarged(separation + router.width // 2)
        overlap_box = dbrbox & bundle_bbox

        if overlap_box.empty():
            overlap_complete = dbrbox & complete_bbox
            if overlap_complete.empty():
                bundled_bboxes.append(bundle_bbox)
                bundle_bbox = bbox.dup()
                bundle_region = kdb.Region(bundle_bbox)
                if not (bundle_region & box_region).is_empty():
                    bundle_bbox += box_region.interacting(bundle_region).bbox()
                bundle = [router]
                bundled_routers.append(bundle)
            else:
                for i in range(len(bundled_bboxes)):
                    bundled_bbox = bundled_bboxes[i]
                    if not (dbrbox & bundled_bbox).empty():
                        bb = bundled_bboxes[i]
                        bundled_routers[i].append(router)
                        bundled_bboxes[i] = bb + bbox
                        bundle_bbox = bundled_bboxes[i]
                        bundle = bundled_routers[i]
                        break
                else:
                    bundled_bboxes.append(bundle_bbox)
                    bundle_bbox = bbox.dup()
                    bundle_region = kdb.Region(bundle_bbox)
                    if not (bundle_region & box_region).is_empty():
                        bundle_bbox += box_region.interacting(bundle_region).bbox()
                    bundle = [router]
                    bundled_routers.append(bundle)
                    continue
        else:
            bundle.append(router)
            bundle_bbox += bbox
        complete_bbox += bbox
    bundled_bboxes.append(bundle_bbox)

    merge_bboxes: list[tuple[int, int]] = []
    for i in range(len(bundled_bboxes)):
        for j in range(i):
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
        start_bbox = kdb.Box(r.start.pts[0], re.start.t * _p)
        end_bbox = kdb.Box(r.end.pts[0], re.end.t * _p)
        start_bbox += re.start.t * kdb.Point(-1, 0)
        end_bbox += re.end.t * kdb.Point(-1, 0)
        for r in router_bundle:
            start_bbox += kdb.Box(r.start.pts[0], r.start.t.disp.to_p()) + kdb.Box(
                0, -r.width // 2, 0, r.width // 2
            ).transformed(r.start.t)
            end_bbox += kdb.Box(r.end.pts[0], r.end.t.disp.to_p()) + kdb.Box(
                0, -r.width // 2, 0, r.width // 2
            ).transformed(r.end.t)
            if r.end.t.angle != end_angle:
                raise ValueError(
                    "All ports at the target (end) must have the same angle. "
                    f"{r.start.t=}/{r.end.t=}"
                )
        if bbox_routing == "minimal":
            route_to_bbox(
                (router.start for router in sorted_routers),
                start_bbox,
                bbox_routing="full",
                separation=separation,
            )
            route_to_bbox(
                (router.end for router in sorted_routers),
                end_bbox,
                bbox_routing="full",
                separation=separation,
            )

        if box_region:
            start_bbox = (
                box_region.interacting(kdb.Region(start_bbox)).bbox() + start_bbox
            )
            end_bbox = box_region.interacting(kdb.Region(end_bbox)).bbox() + end_bbox
        route_to_bbox(
            (router.start for router in sorted_routers),
            start_bbox,
            bbox_routing=bbox_routing,
            separation=separation,
        )
        route_to_bbox(
            (router.end for router in sorted_routers),
            end_bbox,
            bbox_routing=bbox_routing,
            separation=separation,
        )
        bb_start2end = kdb.Trans(-angle, False, 0, 0) * start_bbox
        bb_end2start = kdb.Trans(-angle, False, 0, 0) * end_bbox

        if bb_start2end.left - bb_end2start.right > bend90_radius + sum(widths):
            target_angle = (angle - 2) % 4
        else:
            target_angle = angle
            avg = kdb.Vector()
            end_routers = [r.end for r in sorted_routers]
            for rs in end_routers:
                avg += rs.tv
            route_to_bbox(
                end_routers, end_bbox, separation=separation, bbox_routing=bbox_routing
            )
            _route_to_side(
                end_routers,
                clockwise=avg.y > 0,
                bbox=end_bbox,
                separation=separation,
                bbox_routing=bbox_routing,
            )
            _route_to_side(
                end_routers,
                clockwise=avg.y > 0,
                bbox=end_bbox,
                separation=separation,
                bbox_routing=bbox_routing,
            )
        router_groups: list[tuple[int, list[ManhattanRouter]]] = []
        group_angle: int | None = None
        current_group: list[ManhattanRouter] = []
        for router in sorted_routers:
            ang = router.start.t.angle
            if ang != group_angle:
                if group_angle is not None:
                    router_groups.append(
                        ((group_angle - target_angle) % 4, current_group)
                    )
                group_angle = ang
                current_group = []
            current_group.append(router)
        if group_angle is not None:
            router_groups.append(((group_angle - target_angle) % 4, current_group))

        total_bbox = start_bbox

        if len(router_groups) > 1:
            i = 0
            rg_angles = [rg[0] for rg in router_groups]
            traverses0 = False
            a = rg_angles[0]

            for _a in rg_angles[1:]:
                if _a == 0:
                    continue
                if _a <= a:
                    traverses0 = True
                a = _a
            angle = rg_angles[0]

            # Find out whether we are passing the angle where no side routing is
            # necessary and if we do, we need to start routing clockwise until we
            # pass 0. Otherwise test on which side of the bounding box we land

            # Routing clock-wise (the order of the routers, the actual routings are
            # anti-clockwise and vice-versa)

            if traverses0 or rg_angles[-1] in {0, 3}:
                routers_clockwise: list[ManhattanRouter]
                routers_clockwise = router_groups[0][1].copy()
                for i in range(1, len(router_groups)):
                    new_angle, new_routers = router_groups[i]
                    a = angle
                    if routers_clockwise:
                        if traverses0:
                            while a not in {new_angle, 0}:
                                a = (a + 1) % 4
                                total_bbox += _route_to_side(
                                    routers=[
                                        router.start for router in routers_clockwise
                                    ],
                                    clockwise=True,
                                    bbox=start_bbox,
                                    separation=separation,
                                    allow_sbends=a == 0 and allow_sbend,
                                )
                        else:
                            while a != new_angle:
                                a = (a + 1) % 4
                                total_bbox += _route_to_side(
                                    routers=[
                                        router.start for router in routers_clockwise
                                    ],
                                    clockwise=True,
                                    bbox=start_bbox,
                                    separation=separation,
                                    allow_sbends=a == 0 and allow_sbend,
                                )
                    if new_angle <= angle:
                        if new_angle != 0:
                            i -= 1  # noqa: PLW2901
                        break
                    routers_clockwise.extend(new_routers)
                    angle = new_angle
                else:
                    a = angle
                    while a != 0:
                        a = (a + 1) % 4
                        total_bbox += _route_to_side(
                            routers=[router.start for router in routers_clockwise],
                            clockwise=True,
                            bbox=start_bbox,
                            separation=separation,
                        )

            # Route the rest of the groups anti-clockwise
            if i < len(router_groups) - 1:
                angle = rg_angles[-1]
                routers_anticlockwise: list[ManhattanRouter]
                routers_anticlockwise = router_groups[-1][1].copy()
                n = i
                for i in reversed(range(n, len(router_groups) - 1)):
                    new_angle, new_routers = router_groups[i]
                    a = angle
                    if routers_anticlockwise:
                        while a not in {new_angle, 0}:
                            a = (a - 1) % 4
                            total_bbox += _route_to_side(
                                routers=[
                                    router.start for router in routers_anticlockwise
                                ],
                                clockwise=False,
                                bbox=start_bbox,
                                separation=separation,
                                allow_sbends=a == 0 and allow_sbend,
                            )
                    if new_angle == 0:
                        routers_anticlockwise.extend(new_routers)
                        break
                    if new_angle >= angle:
                        break
                    routers_anticlockwise.extend(new_routers)
                    angle = new_angle
                else:
                    a = angle
                    while a != 0:
                        a = (a - 1) % 4
                        total_bbox += _route_to_side(
                            routers=[router.start for router in routers_anticlockwise],
                            clockwise=False,
                            bbox=start_bbox,
                            separation=separation,
                            allow_sbends=a == 0 and allow_sbend,
                        )
            route_to_bbox(
                [router.start for router in sorted_routers],
                total_bbox,
                bbox_routing=bbox_routing,
                separation=separation,
            )
            route_loosely(
                sorted_routers,
                separation=separation,
                start_bbox=total_bbox,
                end_bbox=end_bbox,
                bbox_routing=bbox_routing,
                allow_sbend=allow_sbend,
            )
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
                        allow_sbends=allow_sbend,
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
                        allow_sbends=allow_sbend,
                    )
                case 3:
                    total_bbox = _route_to_side(
                        [r.start for r in routers],
                        clockwise=False,
                        bbox=total_bbox,
                        separation=separation,
                        allow_sbends=allow_sbend,
                    )
                case _:
                    ...
            route_to_bbox(
                [router.start for router in router_bundle],
                total_bbox,
                bbox_routing=bbox_routing,
                separation=separation,
            )
            route_loosely(
                routers,
                separation=separation,
                start_bbox=total_bbox,
                end_bbox=end_bbox,
                bbox_routing=bbox_routing,
                allow_sbend=allow_sbend,
            )

    return all_routers


def route_to_bbox(
    routers: Iterable[ManhattanRouterSide],
    bbox: kdb.Box,
    separation: int,
    bbox_routing: Literal["minimal", "full"],
) -> None:
    if not bbox.empty():
        if bbox_routing == "minimal":
            bb = bbox.dup()
            for router in routers:
                hw1 = router.router.width // 2 + separation
                bb += router.t * kdb.Point(router.router.bend90_radius - hw1, 0)
            for router in routers:
                hw1 = router.router.width // 2 + separation
                match router.t.angle:
                    case 0:
                        router.straight_nobend(bb.right + hw1 - router.t.disp.x)
                    case 1:
                        router.straight_nobend(bb.top + hw1 - router.t.disp.y)
                    case 2:
                        router.straight_nobend(-bb.left + hw1 + router.t.disp.x)
                    case 3:
                        router.straight_nobend(-bb.bottom + hw1 + router.t.disp.y)
        elif bbox_routing == "full":
            for router in routers:
                hw1 = max(
                    router.router.width // 2 + separation - router.router.bend90_radius,
                    0,
                )
                match router.t.angle:
                    case 0:
                        router.straight(bbox.right + hw1 - router.t.disp.x)
                    case 1:
                        router.straight(bbox.top + hw1 - router.t.disp.y)
                    case 2:
                        router.straight(-bbox.left + hw1 + router.t.disp.x)
                    case 3:
                        router.straight(-bbox.bottom + hw1 + router.t.disp.y)
        else:
            raise ValueError(
                f"routing mode {bbox_routing=} is not supported, available modes"
                " 'minimal', 'full'"
            )


def route_loosely(
    routers: Sequence[ManhattanRouter],
    separation: int,
    bbox_routing: Literal["minimal", "full"],
    start_bbox: kdb.Box | None = None,
    end_bbox: kdb.Box | None = None,
    allow_sbend: bool = False,
) -> None:
    """Route two port banks (all ports same direction) to the end.

    This will not result in a tight bundle but use all the space available and
    choose the shortest path.
    """
    if start_bbox is None:
        start_bbox = kdb.Box()
    if end_bbox is None:
        end_bbox = kdb.Box()
    router_start_box = start_bbox.dup()

    if routers:
        angle = (routers[0].end.t.angle - 2) % 4
        sorted_routers = _sort_routers(routers)

        routers_per_angle: dict[int, list[ManhattanRouter]] = defaultdict(list)
        route_to_bbox(
            routers=(r.start for r in sorted_routers),
            bbox=start_bbox,
            separation=separation,
            bbox_routing=bbox_routing,
        )

        for router in sorted_routers:
            routers_per_angle[(router.start.t.angle - angle + 2) % 4].append(router)

        if ANGLE_90 in routers_per_angle:
            r_list = list(reversed(routers_per_angle[1]))
            delta = -r_list[0].width // 2
            for router in r_list:
                route_to_bbox(
                    routers=[router.start],
                    bbox=router_start_box,
                    separation=separation,
                    bbox_routing=bbox_routing,
                )
                tv = router.start.tv
                s = max(router.bend90_radius, router.width + separation)
                if tv.x >= s:
                    router.auto_route()
                    continue
                delta += router.width // 2
                router.start.straight(s + tv.x)
                router_start_box += router.start.t * kdb.Point(
                    router.width + separation, 0
                )
                router.start.left()
                route_to_bbox(
                    routers=[router.start],
                    bbox=router_start_box,
                    separation=separation,
                    bbox_routing=bbox_routing,
                )
                router_start_box += router.start.t * kdb.Point(
                    router.bend90_radius + router.width + separation, 0
                )
                delta += router.width - router.width // 2 + separation

        if ANGLE_270 in routers_per_angle:
            r_list = list(routers_per_angle[3])
            delta = -r_list[0].width // 2
            for router in r_list:
                route_to_bbox(
                    routers=[router.start],
                    bbox=router_start_box,
                    separation=separation,
                    bbox_routing=bbox_routing,
                )
                tv = router.start.tv
                s = max(router.bend90_radius, router.width + separation)
                if tv.x >= s:
                    router.auto_route()
                    continue
                delta += router.width // 2
                router.start.straight(s + tv.x)
                router_start_box += router.start.t * kdb.Point(
                    router.width + separation, 0
                )
                router.start.right()
                route_to_bbox(
                    routers=[router.start],
                    bbox=router_start_box,
                    separation=separation,
                    bbox_routing=bbox_routing,
                )
                router_start_box += router.start.t * kdb.Point(
                    router.bend90_radius + router.width + separation, 0
                )
                delta += router.width - router.width // 2 + separation

        reverse_groups: list[list[ManhattanRouter]] = []
        forward_groups: list[list[ManhattanRouter]] = []
        s = 0
        delta = 0
        group: list[ManhattanRouter] = []
        group_bbox = kdb.Box()

        for router in sorted_routers:
            tv = router.start.tv
            if tv.y == 0:
                if group:
                    if s == -1:
                        reverse_groups.append(group)
                        group = []
                    else:
                        forward_groups.append(group)
                delta = 0
                router.auto_route()
                s = 0
            elif tv.y > 0:
                r_bbox = kdb.Box(
                    router.start.t.disp.to_p(), router.end.t.disp.to_p()
                ).enlarged(router.width)
                if s == -1:
                    if group:
                        reverse_groups.append(group)
                    group = []
                    group_bbox = r_bbox
                elif s == 0:
                    if group:
                        reverse_groups.append(group)
                    group = []
                if not (r_bbox & group_bbox.enlarged(separation)).empty():
                    group_bbox += r_bbox
                    group.append(router)
                else:
                    if group:
                        forward_groups.append(group)
                    group = [router]
                    group_bbox = r_bbox
                s = 1
            else:
                r_bbox = kdb.Box(
                    router.start.t.disp.to_p(), router.end.t.disp.to_p()
                ).enlarged(router.width)
                if s in (1, 0):
                    if group:
                        forward_groups.append(group)
                    group = [router]
                    group_bbox = r_bbox
                if not (r_bbox & group_bbox.enlarged(separation)).empty():
                    group_bbox += r_bbox
                    group.append(router)
                else:
                    if group:
                        reverse_groups.append(group)
                    group = [router]
                    group_bbox = r_bbox
                s = -1
        if s == 1 and group:
            forward_groups.append(group)
        elif s == -1 and group:
            reverse_groups.append(group)

        for router_group in forward_groups:
            delta = 0
            for router in reversed(router_group):
                if not router.finished:
                    router.start.straight(delta)
                    delta += router.width + separation
                    router.auto_route(bbox=start_bbox)

        for router_group in reverse_groups:
            delta = 0
            for router in router_group:
                if not router.finished:
                    router.start.straight(delta)
                    delta += router.width + separation
                    router.auto_route(bbox=start_bbox)


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
                    case _:
                        ...
                end_transformations.reverse()
            case 1:
                start_transformations = []
                end_transformations = _sort_trans_bank(back)
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
                return sorted(transformations, key=lambda t: t.disp.y)
            case 1:
                return sorted(transformations, key=lambda t: -t.disp.x)
            case 2:
                return sorted(transformations, key=lambda t: -t.disp.y)
            case _:
                return sorted(transformations, key=lambda t: t.disp.x)
    else:
        return []


def _route_to_side(
    routers: list[ManhattanRouterSide],
    clockwise: bool,
    bbox: kdb.Box,
    separation: int,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    allow_sbends: bool = False,
) -> kdb.Box:
    """Route a list of routers either clockwise or anti-clockwise one 90° corner.

    "minimal" will only route so far around that the routers are one separation of their
    width away from the bbbox. "full" will first route all routers outside of the bbox.
    """
    bbox = bbox.dup()

    def _sort_route(router: ManhattanRouterSide) -> int:
        y = (kdb.Trans(-router.t.angle, False, 0, 0) * router.t.disp).y
        if clockwise:
            return -y
        return y

    sorted_rs = sorted(routers, key=_sort_route)
    for rs in sorted_rs:
        hw1 = rs.router.width // 2
        hw2 = rs.router.width - hw1
        match rs.t.angle:
            case 0:
                s = (
                    bbox.right
                    + hw1
                    + separation
                    - rs.t.disp.x
                    - rs.router.bend90_radius
                )
            case 1:
                s = bbox.top + hw1 + separation - rs.t.disp.y - rs.router.bend90_radius
            case 2:
                s = (
                    rs.t.disp.x
                    - (bbox.left - hw1 - separation)
                    - rs.router.bend90_radius
                )
            case _:
                s = (
                    rs.t.disp.y
                    - (bbox.bottom - hw1 - separation)
                    - rs.router.bend90_radius
                )
        rs.straight(s)
        tv = rs.tv
        x = tv.x
        y = tv.y
        if clockwise:
            match rs.ta:
                case 3:
                    if x >= rs.router.bend90_radius:
                        rs.straight_nobend(x)
                    elif x > -rs.router.bend90_radius and not allow_sbends:
                        rs.straight(rs.router.bend90_radius + x)
                case 0 if x > 0:
                    rs.straight(x)
            if not (y == 0 and rs.ta == ANGLE_180 and x > 0):
                rs.left()
            bbox += rs.t * kdb.Point(0, -hw2)
        else:
            match rs.ta:
                case 1:
                    if x >= rs.router.bend90_radius:
                        rs.straight_nobend(x)
                    elif x > -rs.router.bend90_radius and not allow_sbends:
                        rs.straight(rs.router.bend90_radius + x)
                case 0 if x > 0:
                    rs.straight(x)
            if not (y == 0 and rs.ta == ANGLE_180 and x > 0):
                rs.right()
            bbox += rs.t * kdb.Point(0, hw2)

    return bbox


def _backbone2bundle(
    backbone: Sequence[kdb.Point],
    port_widths: Sequence[int],
    spacing: int,
) -> list[list[kdb.Point]]:
    """Used to extract a bundle from a backbone."""
    pts: list[list[kdb.Point]] = []

    edges: list[kdb.Edge] = []
    angles: list[int] = []
    p1 = backbone[0]

    for p2 in backbone[1:]:
        edges.append(kdb.Edge(p1, p2))
        angles.append(vec_dir(p2 - p1))
        p1 = p2

    width = sum(port_widths) + spacing * (len(port_widths) - 1)

    x = -width // 2

    for pw in port_widths:
        x += pw // 2

        pts_ = [p.dup() for p in backbone]
        p1 = pts_[0]

        for p2, e, angle in zip(pts_[1:], edges, angles, strict=False):
            e_ = e.shifted(-x)
            if angle % 2:
                p1.x = e_.p1.x
                p2.x = e_.p2.x
            else:
                p1.y = e_.p1.y
                p2.y = e_.p2.y
            p1 = p2

        x += spacing + pw - pw // 2
        pts.append(pts_)

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
    angle = ports_to_route[0][0].angle
    dir_trans = kdb.Trans(angle, False, 0, 0)
    inv_dir_trans = dir_trans.inverted()
    trans_ports = [
        (inv_dir_trans * _trans, _width) for (_trans, _width) in ports_to_route
    ]
    bundle_width = sum(tw[1] for tw in trans_ports) + (len(trans_ports) - 1) * spacing

    trans_mapping = {
        norm_t: t
        for (t, _), (norm_t, _) in zip(ports_to_route, trans_ports, strict=False)
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

    sorted_ports = sorted(trans_ports, key=sort_port)

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
                dir_ = 0
            case y if y > 0:
                dir_ = 1
            case _:
                dir_ = -1
        changed = dir_ != old_dir
        match dy:
            case 0:
                bend_straight_lengths.append(0)
                append_straights(straights, current_straights, old_dir == -1)
                current_straights.append(0)
                straight = _width + spacing
                old_dir = dir_
            case y if abs(y) < 2 * bend_radius:
                bend_straight_lengths.append(4 * bend_radius)
                if not changed:
                    append_straights(straights, current_straights, old_dir == -1)
                    current_straights.append(0)
                    straight = _width + spacing
                    old_dir = -dir_
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
                old_dir = dir_
        bundle_route_y -= _width - _width // 2 + spacing
    append_straights(straights, current_straights, old_dir == -1)

    bundle_position_x = max(
        tw[0].disp.x + ss + es + start_straight + end_straight
        for tw, ss, es in zip(
            sorted_ports, bend_straight_lengths, straights, strict=False
        )
    )
    bundle_position.x = max(bundle_position.x, bundle_position_x)

    bundle_route_y = bundle_position.y + bundle_width // 2
    bundle_route_x = bundle_position.x
    port_dict: dict[kdb.Trans, list[kdb.Point]] = {}

    for (_trans, _width), _end_straight in zip(sorted_ports, straights, strict=False):
        bundle_route_y -= _width // 2
        t_e = kdb.Trans(2, False, bundle_route_x, bundle_route_y)
        pts = [
            dir_trans * p
            for p in route_manhattan(
                t_e,
                _trans,
                bend90_radius=bend_radius,
                start_steps=[Straight(dist=end_straight + end_straight)],
                end_steps=[Straight(dist=start_straight)],
            )
        ]
        pts.reverse()
        port_dict[trans_mapping[_trans]] = pts
        bundle_route_y -= _width - _width // 2 + spacing

    return port_dict, dir_trans * bundle_position


def _route_waypoints(
    waypoints: kdb.Trans | Sequence[kdb.Point],
    widths: Sequence[int],
    separation: int,
    bend90_radius: int,
    start_ts: Sequence[kdb.Trans],
    end_ts: Sequence[kdb.Trans],
    starts: Sequence[Sequence[Step]],
    ends: Sequence[Sequence[Step]],
    bboxes: Sequence[kdb.Box] | None,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    sort_ports: bool = False,
    allow_sbends: bool = False,
) -> list[ManhattanRouter]:
    if isinstance(waypoints, kdb.Trans):
        length_widths = len(widths)
        half_width = (sum(widths) + (len(widths) - 1) * separation) // 2
        backbone_start_trans: list[kdb.Trans] = []
        backbone_end_trans: list[kdb.Trans] = []
        rot_t = waypoints * kdb.Trans.R180
        rot_t.mirror = False
        w = -half_width
        for i in range(length_widths):
            w += widths[i] // 2
            backbone_start_trans.append(rot_t * kdb.Trans(0, w))
            backbone_end_trans.append(rot_t * kdb.Trans(2, False, 0, w))
            w += widths[i] - widths[i] // 2 + separation
        start_manhattan_routers = route_smart(
            start_ports=start_ts,
            end_ports=backbone_start_trans,
            widths=widths,
            bend90_radius=bend90_radius,
            separation=separation,
            starts=starts,
            ends=cast("list[list[Step]]", [[]] * len(starts)),
            bboxes=bboxes,
            waypoints=None,
            bbox_routing=bbox_routing,
            sort_ports=sort_ports,
        )
        end_manhattan_routers = route_smart(
            start_ports=end_ts,
            end_ports=backbone_end_trans,
            widths=widths,
            bend90_radius=bend90_radius,
            separation=separation,
            starts=ends,
            ends=cast("list[list[Step]]", [[]] * len(ends)),
            bboxes=bboxes,
            waypoints=None,
            bbox_routing=bbox_routing,
        )
        all_routers: list[ManhattanRouter] = []
        start_manhattan_routers.sort(key=lambda sr: sr.end_transformation)
        end_manhattan_routers.sort(
            key=lambda er: er.end_transformation * kdb.Trans.R180
        )

        for sr, er in zip(start_manhattan_routers, end_manhattan_routers, strict=False):
            router = ManhattanRouter(
                bend90_radius=bend90_radius,
                start_transformation=sr.start_transformation,
                end_transformation=er.start_transformation,
                start_points=sr.start.pts[:-1] + list(reversed(er.start.pts[:-1])),
                allow_sbends=allow_sbends,
            )
            router.start.t = router.end_transformation * kdb.Trans.R180
            router.finished = True
            all_routers.append(router)
        return all_routers
    if len(waypoints) < MIN_WAYPOINTS_FOR_ROUTING:
        raise ValueError(
            "If the waypoints should only contain one point, a direction "
            "for the waypoint must be indicated, please pass a 'kdb.Trans'"
            " object instead."
        )
    start_angle = vec_dir(waypoints[0] - waypoints[1])
    end_angle = vec_dir(waypoints[-1] - waypoints[-2])
    all_routers = []
    bundle_points = _backbone2bundle(
        backbone=waypoints,
        port_widths=widths,
        spacing=separation,
    )
    start_manhattan_routers = route_smart(
        start_ports=start_ts,
        end_ports=[
            kdb.Trans(start_angle, False, _bb[0].to_v()) for _bb in bundle_points
        ],
        widths=widths,
        bend90_radius=bend90_radius,
        separation=separation,
        starts=starts,
        ends=cast("list[list[Step]]", [[]] * len(starts)),
        bboxes=bboxes,
        sort_ports=sort_ports,
        waypoints=None,
        bbox_routing=bbox_routing,
    )
    end_manhattan_routers = route_smart(
        end_ports=[
            kdb.Trans(end_angle, False, _bb[-1].to_v()) for _bb in bundle_points
        ],
        start_ports=end_ts,
        widths=widths,
        bend90_radius=bend90_radius,
        separation=separation,
        starts=ends,
        ends=cast("list[list[Step]]", [[]] * len(ends)),
        bboxes=bboxes,
        sort_ports=sort_ports,
        waypoints=None,
        bbox_routing=bbox_routing,
    )
    start_manhattan_routers.sort(key=lambda sr: sr.start.pts[-1])
    end_manhattan_routers.sort(key=lambda er: er.start.pts[-1])
    bundle_points.sort(key=lambda _bb: _bb[0])
    end_manhattan_routers = [
        er
        for _, er in sorted(
            zip(
                sorted(bundle_points, key=lambda _bb: _bb[-1]),
                end_manhattan_routers,
                strict=False,
            ),
            key=lambda pair: pair[0][0],
        )
    ]
    for sr, _bb, er in zip(
        start_manhattan_routers, bundle_points, end_manhattan_routers, strict=False
    ):
        router = ManhattanRouter(
            bend90_radius=bend90_radius,
            start_transformation=sr.start_transformation,
            end_transformation=er.start_transformation,
            start_points=sr.start.pts[:-1]
            + _bb[1:-1]
            + list(reversed(er.start.pts[:-1])),
            allow_sbends=allow_sbends,
        )
        router.start.t = router.end.t * kdb.Trans.R180
        router.finished = True
        all_routers.append(router)
    return all_routers


@overload
def clean_points(points: list[kdb.Point]) -> list[kdb.Point]: ...


@overload
def clean_points(points: list[kdb.DPoint]) -> list[kdb.DPoint]: ...


def clean_points(
    points: list[kdb.Point] | list[kdb.DPoint],
) -> list[kdb.Point] | list[kdb.DPoint]:
    """Remove useless points from a manhattan type of list.

    This will remove the middle points that are on a straight line.
    """
    if len(points) < MIN_POINTS_FOR_CLEAN:
        return points
    if len(points) == MIN_POINTS_FOR_CLEAN:
        return points if points[1] != points[0] else points[:1]
    p_p = points[0]
    p = points[1]

    del_points: list[int] = []

    for i, p_n in enumerate(points[2:], 2):
        v2 = p_n - p  # type: ignore[operator]
        v1 = p - p_p  # type: ignore[operator]

        if (
            (np.sign(v1.x) == np.sign(v2.x)) and (np.sign(v1.y) == np.sign(v2.y))
        ) or v2.abs() == 0:
            del_points.append(i - 1)
        else:
            p_p = p
            p = p_n  # type: ignore[assignment]
    for i in reversed(del_points):
        del points[i]

    return points

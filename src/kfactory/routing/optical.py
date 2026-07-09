"""Optical routing allows the creation of photonic (or any route using bends)."""

from __future__ import annotations

import inspect
from collections.abc import Sequence
from enum import IntEnum
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Protocol,
    TypedDict,
    TypeGuard,
    cast,
    overload,
)

from .. import kdb, rdb
from ..conf import (
    ANGLE_270,
    MIN_POINTS_FOR_PLACEMENT,
    NUM_PORTS_FOR_ROUTING,
    config,
    logger,
)
from ..instance import Instance, ProtoTInstance
from ..instance_group import InstanceGroup, ProtoTInstanceGroup
from ..kcell import DKCell, KCell, ProtoTKCell
from ..port import Port
from .generic import ManhattanRoute, PlacerFunction, get_radius
from .generic import (
    route_bundle as route_bundle_generic,
)
from .manhattan import (
    ManhattanRouter,
    _is_manhattan,
    route_manhattan,
    route_smart,
)
from .route_ports import (
    RoutePort,
    port_for_connect,
    route_port,
)
from .route_ports import (
    instance_route_port as _instance_route_port,
)
from .route_ports import (
    instance_route_port_by_name as _instance_route_port_by_name,
)
from .steps import Step, Straight

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ..factories import (
        SBendFactoryDBU,
        SBendFactoryUM,
        StraightFactoryDBU,
        StraightFactoryUM,
    )
    from ..port import BasePort, DPort, Port
    from ..schematic import Constraint
    from ..typings import dbu, um
    from .utils import RouteDebug

__all__ = [
    "get_radius",
    "place_manhattan",
    "place_manhattan_with_sbends",
    "route_bundle",
    "route_loopback",
    "vec_angle",
]

_PENDING_POLYGON_REGIONS: dict[int, dict[kdb.LayerInfo, kdb.Region]] = {}
_PENDING_POLYGON_HOLES: dict[int, dict[kdb.LayerInfo, kdb.Region]] = {}


class _HasRoutingFastFactory(Protocol):
    routing_fast_factory: StraightFactoryDBU


class _RoutingFastParameterFactoryDBU(Protocol):
    def __call__(
        self, width: int, length: int, routing_fast: bool = False
    ) -> ProtoTKCell[Any]: ...


class _RoutingFastParameterFactoryUM(Protocol):
    def __call__(
        self, width: float, length: float, routing_fast: bool = False
    ) -> ProtoTKCell[Any]: ...


class _RoutingStraightFactoryDBU(Protocol):
    supports_routing_fast: bool
    supports_polygon_materialization: bool

    def __call__(
        self, width: int, length: int, routing_fast: bool = False
    ) -> KCell: ...


class _CachedRoutingStraightFactoryDBU:
    def __init__(
        self,
        make_cell: Callable[[int, int, bool], KCell],
        *,
        supports_routing_fast: bool,
        supports_polygon_materialization: bool,
    ) -> None:
        self._make_cell = make_cell
        self._cache: dict[tuple[int, int], KCell] = {}
        self.supports_routing_fast = supports_routing_fast
        self.supports_polygon_materialization = supports_polygon_materialization

    def __call__(self, width: int, length: int, routing_fast: bool = False) -> KCell:
        key = (width, length)
        straight_cell = self._cache.get(key)
        if straight_cell is None:
            straight_cell = self._make_cell(width, length, routing_fast)
            self._cache[key] = straight_cell
        return straight_cell


class LoopSide(IntEnum):
    left = -1
    center = 0
    right = 1


class LoopPosition(IntEnum):
    start = -1
    center = 0
    end = 1


class PathLengthConfig[T: (int, float)](TypedDict, total=False):
    loops: int
    loop_side: int
    element: int
    loop_position: int
    total_length: int


def _get_routing_fast_straight_factory(
    straight_factory: object,
) -> StraightFactoryDBU | None:
    if _has_routing_fast_factory(straight_factory):
        return straight_factory.routing_fast_factory
    if isinstance(straight_factory, partial) and _has_routing_fast_factory(
        straight_factory.func
    ):
        return partial(
            straight_factory.func.routing_fast_factory,
            *straight_factory.args,
            **(straight_factory.keywords or {}),
        )
    return None


def _has_routing_fast_factory(factory: object) -> TypeGuard[_HasRoutingFastFactory]:
    return hasattr(factory, "routing_fast_factory")


def _accepts_routing_fast_parameter_dbu(
    factory: Callable[..., object],
) -> TypeGuard[_RoutingFastParameterFactoryDBU]:
    try:
        return "routing_fast" in inspect.signature(factory).parameters
    except (TypeError, ValueError):
        return False


def _accepts_routing_fast_parameter_um(
    factory: Callable[..., object],
) -> TypeGuard[_RoutingFastParameterFactoryUM]:
    try:
        return "routing_fast" in inspect.signature(factory).parameters
    except (TypeError, ValueError):
        return False


def _supports_routing_fast_factory(
    factory: StraightFactoryDBU,
) -> TypeGuard[_RoutingStraightFactoryDBU]:
    return getattr(factory, "supports_routing_fast", False) is True


def _supports_polygon_materialization_factory(
    factory: StraightFactoryDBU,
) -> TypeGuard[_RoutingStraightFactoryDBU]:
    return getattr(factory, "supports_polygon_materialization", False) is True


def _expect_kcell(cell: ProtoTKCell[Any], context: str) -> KCell:
    if not isinstance(cell, KCell):
        raise TypeError(f"{context} must return a KCell, got {type(cell).__name__}")
    return cell


def path_length_match(
    routers: Sequence[ManhattanRouter],
    element: int = -1,
    loops: int = 1,
    loop_side: LoopSide = LoopSide.left,
    loop_position: LoopPosition = LoopPosition.start,
    path_length: int | None = None,
) -> None:
    if path_length is None:
        path_length = max(router.path_length for router in routers)
    elif path_length < max(router.path_length for router in routers):
        path_length_ = max(router.path_length for router in routers)
        logger.warning(
            f"Requesting path length matching to {path_length!r}[dbu], but the minimal"
            f" possible path length is {path_length_!r}. Increasing to minimum."
        )
    if path_length % 2:
        logger.warning(
            "path length matching target length "
            "can only be done with a precision of 2 dbu. "
            "Rounding path length matching to nearest 2 dbu length."
        )
        path_length += 1

    if element is None:
        raise ValueError("Element to put path length matching must be defined")

    match loop_side:
        case LoopSide.center:
            loops += 1
    br = max(routers[0].bend90_radius, routers[0].width + routers[0].separation)

    for router in routers:
        length = router.path_length

        match loop_side:
            case LoopSide.left:
                loop_length = (path_length - length) // (loops * 2)
                pts = [
                    kdb.Point(0, 0),
                    kdb.Point(0, loop_length + 2 * br),
                    kdb.Point(2 * br, loop_length + 2 * br),
                    kdb.Point(2 * br, 0),
                ]

                for i in range(1, loops):
                    t = kdb.Trans(i * 4 * br, 0)
                    pts += [t * pt for pt in pts[:4]]
            case LoopSide.right:
                loop_length = (path_length - length) // (loops * 2)
                pts = [
                    kdb.Point(0, 0),
                    kdb.Point(0, -(loop_length + 2 * br)),
                    kdb.Point(2 * br, -(loop_length + 2 * br)),
                    kdb.Point(2 * br, 0),
                ]

                for i in range(1, loops):
                    t = kdb.Trans(i * 4 * br, 0)
                    pts += [t * pt for pt in pts[:4]]

            case LoopSide.center:
                loop_length = (path_length - length) // (loops * 2)
                lh1 = loop_length // 2
                lh2 = loop_length - lh1

                if lh1 > br:
                    lh1 -= br
                    lh2 += br

                pts = [kdb.Point(0, 0)]
                for i in range(loops):
                    pts.extend(
                        [
                            kdb.Point(4 * br * i, lh1 + 2 * br),
                            kdb.Point(4 * br * i + 2 * br, lh1 + 2 * br),
                            kdb.Point(4 * br * i + 2 * br, -(lh2)),
                            kdb.Point(4 * br * (i + 1), -(lh2)),
                        ]
                    )
                pts.extend(
                    [
                        kdb.Point(4 * br * (i + 1), 2 * br),
                        kdb.Point(4 * br * (i + 1) + 2 * br, 2 * br),
                        kdb.Point(4 * br * (i + 1) + 2 * br, 0),
                    ]
                )
            case _:
                raise ValueError(
                    f"Argument side must be of any value of {LoopSide.__members__}"
                    ". This can either be "
                    "an enum value or the int representation."
                )

        if element < -1:
            element_pts = router.start.pts[element - 1 : element + 1]
        elif element == -1:
            element_pts = router.start.pts[element - 1 :]
        else:
            element_pts = router.start.pts[element : element + 2]

        v = element_pts[1] - element_pts[0]

        if v.x != 0:
            d = 0 if v.x > 0 else 2
        elif v.y > 0:
            d = 1
        else:
            d = 3

        t = kdb.Trans(element_pts[0].to_v()) * kdb.Trans(d, False, 0, 0)

        match loop_position:
            case LoopPosition.start:
                if element == 0 or element == -len(router.start.pts):
                    t *= kdb.Trans(br, 0)
                else:
                    t *= kdb.Trans(2 * br, 0)
            case LoopPosition.center:
                t *= kdb.Trans(round((v.length() - pts[-1].x) / 2), 0)
            case LoopPosition.end:
                if element == 0 or element == -len(router.start.pts):
                    t *= kdb.Trans(round(v.length() - br - pts[-1].x // 2), 0)
                else:
                    t *= kdb.Trans(round(v.length() - 2 * br - pts[-1].x), 0)
            case _:
                raise ValueError(
                    "Argument loop_position must be of any value of "
                    f"{LoopPosition.__members__}. This can either be "
                    "an enum value or the int representation."
                )
        if length % 2:
            logger.warning(
                "path length matching can only be done with a precision of 2 dbu. "
                "Rounding path length matching to nearest 2 dbu length."
            )
            length += 1
        if loop_length * 2 * loops != path_length - length:
            l_diff = (path_length - length - loop_length * 2 * loops) // 2
            if loop_side == LoopSide.right:
                pts[1].y -= l_diff
                pts[2].y -= l_diff
            else:
                pts[1].y += l_diff
                pts[2].y += l_diff

        pts = [t * p for p in pts]

        if element < 0:
            router.start.pts[element:element] = pts
        else:
            router.start.pts[element + 1 : element + 1] = pts


@overload
def route_bundle(
    c: KCell,
    start_ports: Sequence[Port],
    end_ports: Sequence[Port],
    separation: dbu,
    straight_factory: StraightFactoryDBU,
    bend90_cell: KCell,
    taper_cell: KCell | None = None,
    min_straight_taper: dbu = 0,
    place_port_type: str = "optical",
    place_allow_small_routes: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    bboxes: list[kdb.Box] | None = None,
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    route_width: dbu | list[dbu] | None = None,
    sort_ports: bool = False,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    waypoints: kdb.Trans | list[kdb.Point] | None = None,
    starts: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None,
    ends: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None,
    start_angles: int | list[int] | None = None,
    end_angles: int | list[int] | None = None,
    purpose: str | None = "routing",
    sbend_factory: SBendFactoryDBU | None = None,
    constraints: Sequence[Constraint] | None = None,
    route_debug: RouteDebug | None = None,
    route_name: str | None = None,
) -> list[ManhattanRoute]: ...


@overload
def route_bundle(
    c: DKCell,
    start_ports: Sequence[DPort],
    end_ports: Sequence[DPort],
    separation: um,
    straight_factory: StraightFactoryUM,
    bend90_cell: DKCell,
    taper_cell: DKCell | None = None,
    min_straight_taper: um = 0,
    place_port_type: str = "optical",
    place_allow_small_routes: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    bboxes: list[kdb.DBox] | None = None,
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    route_width: um | list[um] | None = None,
    sort_ports: bool = False,
    bbox_routing: Literal["minimal", "full"] = "minimal",
    waypoints: kdb.Trans | list[kdb.DPoint] | None = None,
    starts: um | list[um] | list[Step] | list[list[Step]] | None = None,
    ends: um | list[um] | list[Step] | list[list[Step]] | None = None,
    start_angles: float | list[float] | None = None,
    end_angles: float | list[float] | None = None,
    purpose: str | None = "routing",
    sbend_factory: SBendFactoryUM | None = None,
    constraints: Sequence[Constraint] | None = None,
    route_debug: RouteDebug | None = None,
    route_name: str | None = None,
) -> list[ManhattanRoute]: ...


def route_bundle(
    c: KCell | DKCell,
    start_ports: Sequence[Port] | Sequence[DPort],
    end_ports: Sequence[Port] | Sequence[DPort],
    separation: dbu | um,
    straight_factory: StraightFactoryDBU | StraightFactoryUM,
    bend90_cell: KCell | DKCell,
    taper_cell: KCell | DKCell | None = None,
    min_straight_taper: dbu | float = 0,
    place_port_type: str = "optical",
    place_allow_small_routes: bool = False,
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    bboxes: list[kdb.Box] | list[kdb.DBox] | None = None,
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    route_width: dbu | list[dbu] | um | list[um] | None = None,
    sort_ports: bool = False,
    bbox_routing: Literal["minimal", "full"] = "minimal",
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
    sbend_factory: SBendFactoryDBU | SBendFactoryUM | None = None,
    constraints: Sequence[Constraint] | None = None,
    route_debug: RouteDebug | None = None,
    route_name: str | None = None,
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
    if ends is None:
        ends = []
    if starts is None:
        starts = []
    if bboxes is None:
        bboxes = []
    bend90_radius = get_radius(bend90_cell.ports.filter(port_type=place_port_type))
    start_ports_ = [p.base._copy(copy_info=False) for p in start_ports]
    end_ports_ = [p.base._copy(copy_info=False) for p in end_ports]
    if sbend_factory is None:
        placer: PlacerFunction = place_manhattan
        placer_kwargs: dict[str, Any] = {
            "straight_factory": straight_factory,
            "bend90_cell": bend90_cell,
            "taper_cell": taper_cell,
            "port_type": place_port_type,
            "min_straight_taper": min_straight_taper,
            "allow_small_routes": place_allow_small_routes,
            "allow_width_mismatch": allow_width_mismatch,
            "allow_layer_mismatch": allow_layer_mismatch,
            "allow_type_mismatch": allow_type_mismatch,
            "purpose": purpose,
            "route_width": route_width,
        }
    else:
        # Not a type error
        placer = place_manhattan_with_sbends
        placer_kwargs = {
            "straight_factory": straight_factory,
            "bend90_cell": bend90_cell,
            "taper_cell": taper_cell,
            "port_type": place_port_type,
            "min_straight_taper": min_straight_taper,
            "allow_small_routes": place_allow_small_routes,
            "allow_width_mismatch": allow_width_mismatch,
            "allow_layer_mismatch": allow_layer_mismatch,
            "allow_type_mismatch": allow_type_mismatch,
            "purpose": purpose,
            "route_width": route_width,
            "sbend_factory": sbend_factory,
        }
    if isinstance(c, KCell):
        _raw_routing_fast_straight_factory = _get_routing_fast_straight_factory(
            straight_factory
        )
        _routing_fast_parameter_factory = (
            straight_factory
            if _accepts_routing_fast_parameter_dbu(straight_factory)
            else None
        )

        if (
            _raw_routing_fast_straight_factory is not None
            or _routing_fast_parameter_factory is not None
        ):

            def _make_straight_cell(
                width: int, length: int, routing_fast: bool
            ) -> KCell:
                if _raw_routing_fast_straight_factory is not None:
                    return _expect_kcell(
                        _raw_routing_fast_straight_factory(
                            width=width,
                            length=length,
                        ),
                        "routing_fast_factory",
                    )
                if _routing_fast_parameter_factory is not None:
                    return _expect_kcell(
                        _routing_fast_parameter_factory(
                            width=width,
                            length=length,
                            routing_fast=True,
                        ),
                        "straight_factory(routing_fast=True)",
                    )
                return _expect_kcell(
                    straight_factory(width=width, length=length), "straight_factory"
                )

            placer_kwargs["straight_factory"] = _CachedRoutingStraightFactoryDBU(
                _make_straight_cell,
                supports_routing_fast=True,
                supports_polygon_materialization=(
                    _raw_routing_fast_straight_factory is not None
                ),
            )

        try:
            return route_bundle_generic(
                c=c,
                start_ports=start_ports_,
                end_ports=end_ports_,
                starts=cast("dbu | list[dbu] | list[Step] | list[list[Step]]", starts),
                ends=cast("dbu | list[dbu] | list[Step] | list[list[Step]]", ends),
                route_width=cast("int", route_width),
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
                    "allow_sbend": sbend_factory is not None,
                },
                placer_function=placer,
                placer_kwargs=placer_kwargs,
                start_angles=cast("list[int] | int", start_angles),
                end_angles=cast("list[int] | int", end_angles),
                constraints=constraints,
                route_debug=route_debug,
                route_name=route_name,
            )
        except ValueError as e:
            if str(e).startswith("Found non-manhattan waypoints."):
                waypoints = cast("list[kdb.Point]", waypoints)
                wp_old = waypoints[0]
                non_manhattan_wps: list[tuple[kdb.Point, kdb.Point, kdb.Vector]] = []
                for wp in waypoints[1:]:
                    v = wp - wp_old
                    if not _is_manhattan(v):
                        non_manhattan_wps.append((wp_old, wp, v))
                    wp_old = wp
                error_msg = (
                    "Found non-manhattan waypoints. route_smart only supports manhattan"
                    " (orthogonal to the axes) routing.\n Non-manhattan waypoints "
                    "(x,y)[dbu]:\n"
                )
                for error_wp in non_manhattan_wps:
                    error_msg += (
                        f"Start point: {error_wp[0]} End point: {error_wp[1]} "
                        f"Resulting vector (end - start): {error_wp[2]}\n"
                    )
                if on_placer_error == "show_error":
                    c_: KCell | DKCell = c.dup()
                    c_.name = c.kcl._future_cell_name or c.name
                    db = rdb.ReportDatabase("Routing Waypoint Errors")
                    err_cat = db.create_category("Waypoint Error")
                    wp_cat = db.create_category("Waypoints")
                    cell = db.create_cell(c_.name)
                    wp_len = len(waypoints)

                    width = cast("int | None", route_width) or cast(
                        "int", start_ports[0].width
                    )

                    for i, wp in enumerate(waypoints):
                        it = db.create_item(cell=cell, category=wp_cat)
                        it.add_value(f"Waypoint {i + 1}/{wp_len}")
                        it.add_value(
                            kdb.DText(
                                f"Waypoint {i + 1}/{wp_len}",
                                kdb.Trans(wp.to_v()).to_dtype(c.kcl.dbu),
                            )
                        )
                        it.add_value(
                            kdb.Box(width).moved(wp.to_v()).to_dtype(c.kcl.dbu)
                        )
                    for error_wp in non_manhattan_wps:
                        it = db.create_item(cell=cell, category=err_cat)
                        it.add_value(
                            kdb.Path([error_wp[0], error_wp[1]], width)
                            .to_dtype(c.kcl.dbu)
                            .polygon()
                        )
                    c_.show(lyrdb=db)
                raise ValueError(error_msg) from e
            raise
    if route_width is not None:
        if isinstance(route_width, list):
            route_width = [c.kcl.to_dbu(width) for width in route_width]
        else:
            route_width = c.kcl.to_dbu(route_width)
    angles: dict[int | float, int] = {0: 0, 90: 1, 180: 2, 270: 3}
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
            starts = [c.kcl.to_dbu(cast("int|float", start)) for start in starts]
        starts = cast("int | list[int] | list[Step] | list[list[Step]]", starts)
    if isinstance(ends, int | float):
        ends = c.kcl.to_dbu(ends)
    elif isinstance(ends, list):
        if isinstance(ends[0], int | float):
            ends = [c.kcl.to_dbu(cast("int|float", end)) for end in ends]
        ends = cast("int | list[int] | list[Step] | list[list[Step]]", ends)

    _routing_fast_parameter_factory_um = (
        straight_factory
        if _accepts_routing_fast_parameter_um(straight_factory)
        else None
    )

    def _make_straight_cell(width: int, length: int, routing_fast: bool) -> KCell:
        if _routing_fast_parameter_factory_um is not None:
            dkc = _routing_fast_parameter_factory_um(
                width=c.kcl.to_um(width),
                length=c.kcl.to_um(length),
                routing_fast=True,
            )
        else:
            dkc = cast("StraightFactoryUM", straight_factory)(
                width=c.kcl.to_um(width), length=c.kcl.to_um(length)
            )
        return c.kcl[dkc.cell_index()]

    _straight_factory = _CachedRoutingStraightFactoryDBU(
        _make_straight_cell,
        supports_routing_fast=_routing_fast_parameter_factory_um is not None,
        supports_polygon_materialization=False,
    )

    bend90_cell = c.kcl[bend90_cell.cell_index()]
    if taper_cell is not None:
        taper_cell = c.kcl[taper_cell.cell_index()]
    if min_straight_taper:
        min_straight_taper = c.kcl.to_dbu(min_straight_taper)

    bboxes_ = [c.kcl.to_dbu(b) for b in cast("list[kdb.DBox]", bboxes)]
    if waypoints is not None:
        if isinstance(waypoints, list):
            waypoints = [
                p.to_itype(c.kcl.dbu) for p in cast("list[kdb.DPoint]", waypoints)
            ]
        else:
            waypoints = cast("kdb.DCplxTrans", waypoints).s_trans().to_itype(c.kcl.dbu)
    if sbend_factory is None:
        placer = place_manhattan
        placer_kwargs = {
            "straight_factory": _straight_factory,
            "bend90_cell": bend90_cell,
            "taper_cell": taper_cell,
            "port_type": place_port_type,
            "min_straight_taper": min_straight_taper,
            "allow_small_routes": place_allow_small_routes,
            "allow_width_mismatch": allow_width_mismatch,
            "allow_layer_mismatch": allow_layer_mismatch,
            "allow_type_mismatch": allow_type_mismatch,
            "purpose": purpose,
            "route_width": route_width,
        }
    else:
        sbend_factory = cast("SBendFactoryUM", sbend_factory)

        def _sbend_factory(
            c: ProtoTKCell[Any], offset: dbu, length: dbu, width: dbu
        ) -> ProtoTInstance[Any] | ProtoTInstanceGroup[Any, Any]:
            return sbend_factory(
                c=c,
                offset=c.kcl.to_um(offset),
                length=c.kcl.to_um(length),
                width=c.kcl.to_um(width),
            )

        # Not a type error
        placer = place_manhattan_with_sbends
        placer_kwargs = {
            "straight_factory": _straight_factory,
            "bend90_cell": bend90_cell,
            "taper_cell": taper_cell,
            "port_type": place_port_type,
            "min_straight_taper": min_straight_taper,
            "allow_small_routes": place_allow_small_routes,
            "allow_width_mismatch": allow_width_mismatch,
            "allow_layer_mismatch": allow_layer_mismatch,
            "allow_type_mismatch": allow_type_mismatch,
            "purpose": purpose,
            "route_width": route_width,
            "sbend_factory": _sbend_factory,
        }
    try:
        return route_bundle_generic(
            c=c.kcl[c.cell_index()],
            start_ports=start_ports_,
            end_ports=end_ports_,
            starts=starts,
            ends=ends,
            route_width=route_width,
            on_collision=on_collision,
            on_placer_error=on_placer_error,
            collision_check_layers=collision_check_layers,
            routing_function=route_smart,
            routing_kwargs={
                "bend90_radius": bend90_radius,
                "separation": c.kcl.to_dbu(separation),
                "sort_ports": sort_ports,
                "bbox_routing": bbox_routing,
                "bboxes": list(bboxes_),
                "waypoints": waypoints,
                "allow_sbend": sbend_factory is not None,
            },
            placer_function=placer,
            placer_kwargs=placer_kwargs,
            constraints=constraints,
            start_angles=start_angles,
            end_angles=end_angles,
            route_debug=route_debug,
            route_name=route_name,
        )
    except ValueError as e:
        if str(e).startswith("Found non-manhattan waypoints."):
            waypoints = cast("list[kdb.DPoint]", waypoints)
            wp_old_d = waypoints[0]
            non_manhattan_wps_d: list[tuple[kdb.DPoint, kdb.DPoint, kdb.DVector]] = []
            for wp_d in waypoints[1:]:
                v_d = wp_d - wp_old_d
                if not _is_manhattan(v_d):
                    non_manhattan_wps_d.append((wp_old_d, wp_d, v_d))
                wp_old_d = wp_d
            error_msg = (
                "Found non-manhattan waypoints. route_smart only supports manhattan"
                " (orthogonal to the axes) routing.\n Non-manhattan waypoints "
                "(x,y)[dbu]:\n"
            )
            for error_wp_d in non_manhattan_wps_d:
                error_msg += (
                    f"Start point: {error_wp_d[0]} End point: {error_wp_d[1]} "
                    f"Resulting vector (end - start): {error_wp_d[2]}\n"
                )
            if on_placer_error == "show_error":
                c_ = c.dup()
                c_.name = c.kcl._future_cell_name or c.name
                db = rdb.ReportDatabase("Routing Waypoint Errors")
                err_cat = db.create_category("Waypoint Error")
                wp_cat = db.create_category("Waypoints")
                cell = db.create_cell(c_.name)
                wp_len = len(waypoints)

                width_d = cast("float | None", route_width) or start_ports[0].width

                for i, wp_d in enumerate(waypoints):
                    it = db.create_item(cell=cell, category=wp_cat)
                    it.add_value(f"Waypoint {i + 1}/{wp_len}")
                    it.add_value(
                        kdb.DText(f"Waypoint {i + 1}/{wp_len}", kdb.DTrans(wp_d.to_v()))
                    )
                    it.add_value(kdb.DBox(width_d).moved(wp_d.to_v()))
                for error_wp_d in non_manhattan_wps_d:
                    it = db.create_item(cell=cell, category=err_cat)
                    it.add_value(
                        kdb.DPath([error_wp_d[0], error_wp_d[1]], width_d).polygon()
                    )
                c_.show(lyrdb=db)
            raise ValueError(error_msg) from e
        raise


def _place_straight(
    c: KCell,
    straight_factory: StraightFactoryDBU,
    purpose: str | None,
    w: int,
    route: ManhattanRoute,
    p1: Port | RoutePort,
    p2: Port | RoutePort,
    route_width: int | None,
    *,
    port_type: str,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> tuple[RoutePort, RoutePort]:
    p1_route = route_port(p1)
    p2_route = route_port(p2)
    length = abs(p1_route.trans.disp.x - p2_route.trans.disp.x) + abs(
        p1_route.trans.disp.y - p2_route.trans.disp.y
    )
    if _supports_routing_fast_factory(straight_factory):
        ports = _place_straight_polygon(
            c=c,
            straight_factory=straight_factory,
            w=w,
            length=length,
            route=route,
            p1=p1_route,
            p2=p2_route,
            port_type=port_type,
        )
        if ports is not None:
            route.length_straights += length
            return ports
        wg = c << straight_factory(width=w, length=length, routing_fast=True)
    else:
        wg = c << straight_factory(width=w, length=length)
    wg.purpose = purpose
    allow_width_mismatch = route_width is not None or allow_width_mismatch
    _connect_straight_instance(
        wg,
        p1_route,
        allow_width_mismatch=allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )
    wg_p1 = _instance_route_port(wg, 0)
    wg_p2 = _instance_route_port(wg, 1)
    if wg_p1.port_type != port_type or wg_p2.port_type != port_type:
        raise ValueError(f"straight_factory returned unexpected ports for {port_type=}")
    route.instances.append(wg)
    route.length_straights += length
    return wg_p1, wg_p2


def _place_straight_polygon(
    c: KCell,
    straight_factory: StraightFactoryDBU,
    w: int,
    length: int,
    route: ManhattanRoute,
    p1: RoutePort,
    p2: RoutePort,
    *,
    port_type: str,
) -> tuple[RoutePort, RoutePort] | None:
    if not _supports_polygon_materialization_factory(straight_factory):
        return None
    if (
        not p1.is_dbu
        or not p2.is_dbu
        or p1.width != w
        or p2.width != w
        or p1.port_type != port_type
        or p2.port_type != port_type
    ):
        return None

    if not _is_manhattan(p2.trans.disp - p1.trans.disp):
        return None

    straight_cell = straight_factory(width=w, length=length)
    xs = straight_cell._base.ports[0].cross_section
    if xs is None:
        return None
    if not p1.base.any_cross_section.main_layer.is_equivalent(
        xs.main_layer
    ) or not p2.base.any_cross_section.main_layer.is_equivalent(xs.main_layer):
        return None

    _queue_straight_cross_section_polygons(route, xs, p1, p2)
    return (
        RoutePort(base=p1.base, trans=p1.trans * kdb.Trans.R180, dbu=True),
        RoutePort(base=p2.base, trans=p2.trans * kdb.Trans.R180, dbu=True),
    )


def _queue_straight_cross_section_polygons(
    route: ManhattanRoute,
    xs: Any,
    p1: RoutePort,
    p2: RoutePort,
) -> None:
    points = [p1.trans.disp.to_p(), p2.trans.disp.to_p()]
    route_id = id(route)
    pending_regions = _PENDING_POLYGON_REGIONS.setdefault(route_id, {})
    pending_holes = _PENDING_POLYGON_HOLES.setdefault(route_id, {})

    _queue_path_region(pending_regions, xs.main_layer, points, xs.width)
    for layer, layer_section in xs.enclosure.layer_sections.items():
        for section in layer_section.sections:
            _queue_path_region(
                pending_regions,
                layer,
                points,
                xs.width + 2 * section.d_max,
            )
            if section.d_min is not None:
                inner_width = xs.width + 2 * section.d_min
                if inner_width > 0:
                    _queue_path_region(
                        pending_holes,
                        layer,
                        points,
                        inner_width,
                    )


def _queue_path_region(
    regions: dict[kdb.LayerInfo, kdb.Region],
    layer: kdb.LayerInfo,
    points: list[kdb.Point],
    width: int,
) -> None:
    region = regions.get(layer)
    if region is None:
        region = kdb.Region()
        regions[layer] = region
    region.insert(kdb.Path(points, width))


def _insert_route_polygons(c: KCell, route: ManhattanRoute) -> None:
    route_id = id(route)
    pending_regions = _PENDING_POLYGON_REGIONS.pop(route_id, None)
    if not pending_regions:
        return
    pending_holes = _PENDING_POLYGON_HOLES.pop(route_id, {})
    for layer, pending_region in pending_regions.items():
        holes = pending_holes.get(layer)
        region = pending_region
        if holes is not None:
            region -= holes
        region.merge()
        c.shapes(c.kcl.layer(layer)).insert(region)
        route.polygons.setdefault(layer, []).extend(region.each())


def _connect_straight_instance(
    wg: Instance,
    target: RoutePort,
    *,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> None:
    local_base = wg.cell._base.ports[0]
    target_base = target.base

    if _supports_direct_straight_connect(
        local_base, target
    ) and _ports_match_for_direct_connect(
        local_base,
        target_base,
        allow_width_mismatch=allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    ):
        _directly_connect_straight(wg, local_base, target)
        return

    _connect_instance_with_checks(
        wg,
        local_base,
        target,
        allow_width_mismatch=allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )


def _supports_direct_straight_connect(
    local_base: BasePort,
    target: RoutePort,
) -> bool:
    """Whether routing can apply the default `Instance.connect` transform directly."""
    target_base = target.base
    return (
        config.connect_use_mirror
        and config.connect_use_angle
        and local_base.trans is not None
        and target.is_dbu
        and local_base.dcplx_trans is None
        and target_base.dcplx_trans is None
        and local_base.asymmetric_cross_section is None
        and target_base.asymmetric_cross_section is None
    )


def _ports_match_for_direct_connect(
    local_base: BasePort,
    target_base: BasePort,
    *,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> bool:
    """Mirror the cheap compatibility checks needed before direct connection."""
    local_xs = local_base.any_cross_section
    target_xs = target_base.any_cross_section
    return (
        (local_base.is_symmetric() == target_base.is_symmetric())
        and (local_xs.width == target_xs.width or allow_width_mismatch)
        and (
            local_xs.main_layer.is_equivalent(target_xs.main_layer)
            or allow_layer_mismatch
        )
        and (local_base.port_type == target_base.port_type or allow_type_mismatch)
    )


def _directly_connect_straight(
    wg: Instance,
    local_base: BasePort,
    target: RoutePort,
) -> None:
    """Apply the same transform as `Instance.connect(..., mirror=False)`."""
    assert local_base.trans is not None
    wg.trans = target.trans * kdb.Trans.R180 * local_base.trans.inverted()


def _connect_instance_with_checks(
    wg: Instance,
    local_base: BasePort,
    target: Port | RoutePort,
    *,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> None:
    wg.connect(
        Port(base=local_base),
        port_for_connect(target),
        allow_width_mismatch=allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )


def _copy_port_for_placement(
    port: Port | RoutePort,
    post_trans: kdb.Trans = kdb.Trans.R0,
) -> Port:
    return Port(
        base=port_for_connect(port).base.transformed(
            post_trans=post_trans,
            copy_info=False,
        )
    )


def _copy_polar_for_placement(
    port: Port | RoutePort,
    d: int = 0,
    d_orth: int = 0,
    angle: int = 2,
    mirror: bool = False,
) -> Port:
    return _copy_port_for_placement(port, kdb.Trans(angle, mirror, d, d_orth))


def _copy_route_endpoint(port: Port | RoutePort) -> Port:
    if isinstance(port, RoutePort):
        return port.to_port()
    return Port(base=port.base.transformed(copy_info=False))


def _place_sbend(
    c: KCell,
    sbend_factory: SBendFactoryDBU,
    purpose: str | None,
    w: int,
    route: ManhattanRoute,
    p1: Port | RoutePort,
    p2: Port | RoutePort,
    *,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> tuple[Port, Port]:
    p1_ = _copy_port_for_placement(p1)
    p1_.trans.mirror = False
    delta_p = p1_.trans.inverted() * p2.trans.disp.to_p()

    offset = abs(delta_p.y)
    sbend_group = sbend_factory(c=c, width=w, length=delta_p.x, offset=offset)
    if isinstance(sbend_group, ProtoTInstance):
        sbend_group = InstanceGroup(
            insts=[Instance(kcl=sbend_group.cell.kcl, instance=sbend_group.instance)],
            ports=[sbend_group.ports[0], sbend_group.ports[1]],
        )
    else:
        sbend_group = InstanceGroup(
            insts=[
                Instance(kcl=inst.cell.kcl, instance=inst.instance)
                for inst in sbend_group.insts
            ],
            ports=list(sbend_group.ports),
        )
    sp1, sp2 = sbend_group.ports[0], sbend_group.ports[1]

    sp1_ = _copy_polar_for_placement(sp1)
    sp1_.trans.mirror = False
    sbg_delta_p = sp1_.trans.inverted() * sp2.trans.disp.to_p()
    if delta_p.y == sbg_delta_p.y:
        sbend_group.connect(
            sp1.name,
            p1_,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
            allow_width_mismatch=allow_width_mismatch,
        )
    else:
        sbend_group.connect(
            sp1.name,
            p1_,
            mirror=True,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
            allow_width_mismatch=allow_width_mismatch,
        )
    if purpose:
        for inst in sbend_group:
            inst.purpose = purpose
    sp1, sp2 = sbend_group.ports[0], sbend_group.ports[1]
    route.instances.extend(sbend_group.insts)
    route.length_straights += delta_p.x
    return sp1, sp2


def _place_tapered_straight(
    c: KCell,
    straight_factory: StraightFactoryDBU,
    taper_cell: KCell,
    purpose: str | None,
    route: ManhattanRoute,
    p1: Port | RoutePort,
    p2: Port | RoutePort,
    route_width: int | None,
    taper_ports: tuple[Port, Port],
    *,
    port_type: str,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> tuple[RoutePort, RoutePort]:
    taperp1, taperp2 = taper_ports
    p1_route = route_port(p1)
    p2_route = route_port(p2)
    length = int((p1_route.trans.disp.to_p() - p2_route.trans.disp.to_p()).length())
    t1 = c << taper_cell
    t1.purpose = purpose
    t1.connect(
        taperp1.name,
        port_for_connect(p1),
        allow_width_mismatch=route_width is not None or allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )
    route.instances.append(t1)
    t2 = c << taper_cell
    t2.purpose = purpose
    t2.connect(
        taperp1.name,
        port_for_connect(p2),
        allow_width_mismatch=route_width is not None or allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )
    route.instances.append(t2)
    route.n_taper += 2
    l_ = int(length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2)
    if l_ != 0:
        p1_ = _instance_route_port_by_name(t1, taperp2.name)
        p2_ = _instance_route_port_by_name(t2, taperp2.name)
        _place_straight(
            c=c,
            straight_factory=straight_factory,
            purpose=purpose,
            w=taperp2.width,
            p1=p1_,
            p2=p2_,
            route_width=route_width,
            route=route,
            port_type=port_type,
            allow_width_mismatch=allow_width_mismatch,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
        )

    return (
        _instance_route_port_by_name(t1, taperp1.name),
        _instance_route_port_by_name(t2, taperp1.name),
    )


def _place_tapered_sbend_or_straight(
    c: KCell,
    sbend_factory: SBendFactoryDBU,
    taper_cell: KCell,
    purpose: str | None,
    route: ManhattanRoute,
    p1: Port | RoutePort,
    p2: Port | RoutePort,
    route_width: int | None,
    taper_ports: tuple[Port, Port],
    *,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> tuple[Port, Port]:
    taperp1, taperp2 = taper_ports
    p1_route = route_port(p1)
    p2_route = route_port(p2)
    length = int((p1_route.trans.disp.to_p() - p2_route.trans.disp.to_p()).length())
    t1 = c << taper_cell
    t1.purpose = purpose
    t1.connect(
        taperp1.name,
        port_for_connect(p1),
        allow_width_mismatch=route_width is not None or allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )
    route.instances.append(t1)
    t2 = c << taper_cell
    t2.purpose = purpose
    t2.connect(
        taperp1.name,
        port_for_connect(p2),
        allow_width_mismatch=route_width is not None or allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )
    route.instances.append(t2)
    route.n_taper += 2
    l_ = int(length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2)
    if l_ != 0:
        p1_ = t1.ports[taperp2.name]
        p2_ = t2.ports[taperp2.name]
        _place_sbend(
            c=c,
            sbend_factory=sbend_factory,
            purpose=purpose,
            w=taperp2.width,
            p1=p1_,
            p2=p2_,
            route=route,
            allow_width_mismatch=allow_width_mismatch,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
        )

    return t1.ports[taperp1.name], t2.ports[taperp1.name]


def place_manhattan(
    c: ProtoTKCell[Any],
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    route_width: dbu | None = None,
    straight_factory: StraightFactoryDBU | None = None,
    bend90_cell: ProtoTKCell[Any] | None = None,
    taper_cell: ProtoTKCell[Any] | None = None,
    port_type: str = "optical",
    min_straight_taper: dbu = 0,
    allow_small_routes: bool = False,
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    purpose: str | None = "routing",
    **kwargs: Any,
) -> ManhattanRoute:
    # configure and set up route and placers
    c = KCell(base=c.base)
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
    if straight_factory is None:
        raise ValueError(
            "place_manhattan needs to have a straight_factory set. Please pass a "
            "straight_factory which takes kwargs 'width: int' and 'length: int'."
        )
    if bend90_cell is None:
        raise ValueError(
            "place_manhattan needs to be passed a fixed bend90 cell with two optical"
            " ports which are 90° apart from each other with port_type 'port_type'."
        )
    route_start_port = _copy_port_for_placement(p1)
    route_end_port = _copy_port_for_placement(p2)
    if p1.base.trans is None:
        logger.warning(
            f"{p1=} is not a manhattan port (either off-grid or angle not a multiple of"
            " 90 degrees). Forcing port to be manhattan."
        )
        route_start_port.trans = route_start_port.trans
    if p2.base.trans is None:
        logger.warning(
            f"{p2=} is not a manhattan port (either off-grid or angle not a multiple of"
            " 90 degrees). Forcing port to be manhattan."
        )
        route_end_port.trans = route_end_port.trans
    route_start_port.name = "route_start"
    route_start_port.trans.angle = (route_start_port.angle + 2) % 4
    route_end_port.name = "route_end"
    route_end_port.trans.angle = (route_end_port.angle + 2) % 4

    old_pt = pts[0]
    old_bend_port = p1
    bend90_ports = [p for p in bend90_cell.ports if p.port_type == port_type]

    if len(bend90_ports) != NUM_PORTS_FOR_ROUTING:
        raise AttributeError(
            f"{bend90_cell.name} should have 2 ports but has {len(bend90_ports)} ports"
            f"with {port_type=}"
        )
    if abs((bend90_ports[0].trans.angle - bend90_ports[1].trans.angle) % 4) not in [
        1,
        3,
    ]:
        raise AttributeError(
            f"{bend90_cell.name} bend ports should be 90° apart from each other"
        )

    if (bend90_ports[1].trans.angle - bend90_ports[0].trans.angle) % 4 == ANGLE_270:
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
    b90r = round(
        max(
            (b90p1.trans.disp - b90c.disp).length(),
            (b90p2.trans.disp - b90c.disp).length(),
        )
    )
    if taper_cell is not None:
        taper_cell = KCell(base=taper_cell.base)
        taper_ports = [p for p in taper_cell.ports if p.port_type == port_type]
        if (
            len(taper_ports) != NUM_PORTS_FOR_ROUTING
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
            backbone=list(pts),
            start_port=route_start_port,
            end_port=route_end_port,
            instances=[],
            bend90_radius=b90r,
            taper_length=int((taperp1.trans.disp - taperp2.trans.disp).length()),
        )
    else:
        route = ManhattanRoute(
            backbone=list(pts),
            start_port=route_start_port,
            end_port=route_end_port,
            instances=[],
            bend90_radius=b90r,
            taper_length=0,
        )
    w = route_width or p1.width
    # placing
    if not pts or len(pts) < MIN_POINTS_FOR_PLACEMENT:
        # Nothing to be placed
        return route
    # the solution should be just a straight
    if len(pts) == MIN_POINTS_FOR_PLACEMENT:
        length = int((pts[1] - pts[0]).length())
        if (
            taper_cell is None
            or length
            < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
            + min_straight_taper
        ):
            p1_, p2_ = _place_straight(
                c=c,
                straight_factory=straight_factory,
                purpose=purpose,
                w=w,
                route=route,
                p1=p1,
                p2=p2,
                route_width=w,
                port_type=port_type,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
        else:
            p1_, p2_ = _place_tapered_straight(
                c=c,
                straight_factory=straight_factory,
                purpose=purpose,
                taper_ports=(taperp1, taperp2),
                route=route,
                p1=p1,
                p2=p2,
                route_width=w,
                port_type=port_type,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
                taper_cell=taper_cell,
            )
        route.start_port = p1
        route.end_port = p2
        _insert_route_polygons(c, route)
        return route

    # in other cases, place the bend and then route
    for i in range(1, len(pts) - 1):
        pt = pts[i]
        new_pt = pts[i + 1]

        if (pt.distance(old_pt) < b90r) and not allow_small_routes:
            raise ValueError(
                f"distance between points {old_pt!s} and {pt!s} is too small to"
                f" safely place bends {pt.to_s()=}, {old_pt.to_s()=},"
                f" {pt.distance(old_pt)=} < {b90r=}"
            )
        if (
            pt.distance(old_pt) < 2 * b90r
            and i not in {1, len(pts) - 1}
            and not allow_small_routes
        ):
            raise ValueError(
                f"distance between points {old_pt!s} and {pt!s} is too small to"
                f" safely place bends {pt=!s}, {old_pt=!s},"
                f" {pt.distance(old_pt)=} < {2 * b90r=}"
            )

        vec = pt - old_pt
        vec_n = new_pt - pt

        bend90 = c << bend90_cell
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
        new_bend_port = _instance_route_port_by_name(bend90, b90p1.name)
        length = int((new_bend_port.trans.disp - old_bend_port.trans.disp).length())
        if length > 0:
            if (
                taper_cell is None
                or length
                < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                + min_straight_taper
            ):
                p1_, _ = _place_straight(
                    c=c,
                    straight_factory=straight_factory,
                    purpose=purpose,
                    w=w,
                    route=route,
                    p1=old_bend_port,
                    p2=new_bend_port,
                    route_width=route_width,
                    port_type=port_type,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                    allow_width_mismatch=allow_width_mismatch,
                )
            else:
                p1_, _ = _place_tapered_straight(
                    c=c,
                    straight_factory=straight_factory,
                    taper_cell=taper_cell,
                    purpose=purpose,
                    route=route,
                    p1=old_bend_port,
                    p2=new_bend_port,
                    route_width=route_width,
                    taper_ports=(taperp1, taperp2),
                    port_type=port_type,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            if i == 1:
                route.start_port = _copy_route_endpoint(p1_)
        route.instances.append(bend90)
        old_pt = pt
        old_bend_port = _instance_route_port_by_name(bend90, b90p2.name)
    length = int((old_bend_port.trans.disp - p2.trans.disp).length())
    if length > 0:
        if (
            taper_cell is None
            or length
            < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
            + min_straight_taper
        ):
            _, p2_ = _place_straight(
                c=c,
                straight_factory=straight_factory,
                purpose=purpose,
                w=w,
                route=route,
                p1=old_bend_port,
                p2=p2,
                route_width=route_width,
                port_type=port_type,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
        else:
            _, p2_ = _place_tapered_straight(
                c=c,
                straight_factory=straight_factory,
                taper_cell=taper_cell,
                purpose=purpose,
                route=route,
                p1=old_bend_port,
                p2=p2,
                route_width=route_width,
                taper_ports=(taperp1, taperp2),
                port_type=port_type,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
        route.end_port = _copy_route_endpoint(p2_)
    else:
        route.end_port = _copy_route_endpoint(old_bend_port)
    route.start_port.name = "route_start"
    route.end_port.name = "route_end"
    _insert_route_polygons(c, route)
    return route


def place_manhattan_with_sbends(
    c: ProtoTKCell[Any],
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    route_width: dbu | None = None,
    straight_factory: StraightFactoryDBU | None = None,
    bend90_cell: ProtoTKCell[Any] | None = None,
    taper_cell: ProtoTKCell[Any] | None = None,
    port_type: str = "optical",
    min_straight_taper: dbu = 0,
    allow_small_routes: bool = False,
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    purpose: str | None = "routing",
    *,
    sbend_factory: SBendFactoryDBU | None = None,
    **kwargs: Any,
) -> ManhattanRoute:
    # configure and set up route and placers
    c = KCell(base=c.base)
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
    if straight_factory is None:
        raise ValueError(
            "place_manhattan_with_sbends needs to have a straight_factory set. Please "
            "pass a straight_factory which takes kwargs 'width: int' and 'length: int'."
        )
    if bend90_cell is None:
        raise ValueError(
            "place_manhattan_with_sbends needs to be passed a fixed bend90 cell with "
            "two optical ports which are 90° apart from each other with port_type "
            "'port_type'."
        )
    if sbend_factory is None:
        raise ValueError(
            "place_manhattan_with_sbends needs to be passed a sbend_function."
        )
    route_start_port = _copy_port_for_placement(p1)
    route_start_port.name = "route_start"
    route_start_port.trans.angle = (route_start_port.angle + 2) % 4
    route_end_port = _copy_port_for_placement(p2)
    route_end_port.name = "route_end"
    route_end_port.trans.angle = (route_end_port.angle + 2) % 4

    old_pt = pts[0]
    old_bend_port = p1
    bend90_ports = [p for p in bend90_cell.ports if p.port_type == port_type]

    if len(bend90_ports) != NUM_PORTS_FOR_ROUTING:
        raise AttributeError(
            f"{bend90_cell.name} should have 2 ports but has {len(bend90_ports)} ports"
            f"with {port_type=}"
        )
    if abs((bend90_ports[0].trans.angle - bend90_ports[1].trans.angle) % 4) != 1:
        raise AttributeError(
            f"{bend90_cell.name} bend ports should be 90° apart from each other"
        )

    if (bend90_ports[1].trans.angle - bend90_ports[0].trans.angle) % 4 == ANGLE_270:
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
    b90r = round(
        max(
            (b90p1.trans.disp - b90c.disp).length(),
            (b90p2.trans.disp - b90c.disp).length(),
        )
    )
    if taper_cell is not None:
        taper_cell = KCell(base=taper_cell.base)
        taper_ports = [p for p in taper_cell.ports if p.port_type == "optical"]
        if (
            len(taper_ports) != NUM_PORTS_FOR_ROUTING
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
            backbone=list(pts),
            start_port=route_start_port,
            end_port=route_end_port,
            instances=[],
            bend90_radius=b90r,
            taper_length=int((taperp1.trans.disp - taperp2.trans.disp).length()),
        )
    else:
        route = ManhattanRoute(
            backbone=list(pts),
            start_port=route_start_port,
            end_port=route_end_port,
            instances=[],
            bend90_radius=b90r,
            taper_length=0,
        )
    w = route_width or p1.width
    # placing
    if not pts or len(pts) < MIN_POINTS_FOR_PLACEMENT:
        # Nothing to be placed
        return route
    # the solution should be just a straight
    if len(pts) == MIN_POINTS_FOR_PLACEMENT:
        vec = pts[1] - pts[0]
        if _is_sbend_vec(vec):
            sbend_vec = (kdb.Trans(-p1.angle, False, 0, 0) * vec.to_p()).to_v()
            _place_sbend(
                c=c,
                sbend_factory=sbend_factory,
                purpose=purpose,
                w=w,
                route=route,
                p1=old_bend_port,
                p2=_copy_polar_for_placement(
                    old_bend_port, d=sbend_vec.x, d_orth=sbend_vec.y, angle=2
                ),
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
        else:
            length = int(vec.length())
            if (
                taper_cell is None
                or length
                < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                + min_straight_taper
            ):
                _place_straight(
                    c=c,
                    straight_factory=straight_factory,
                    purpose=purpose,
                    w=w,
                    route=route,
                    p1=p1,
                    p2=p2,
                    route_width=w,
                    port_type=port_type,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            else:
                _place_tapered_straight(
                    c=c,
                    straight_factory=straight_factory,
                    purpose=purpose,
                    taper_ports=(taperp1, taperp2),
                    route=route,
                    p1=p1,
                    p2=p2,
                    route_width=w,
                    port_type=port_type,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                    taper_cell=taper_cell,
                )
        p1.name = "route_start"
        p2.name = "route_end"
        route.start_port = p1
        route.end_port = p2
        _insert_route_polygons(c, route)
        return route

    # in other cases, place the bend and then route
    for i in range(1, len(pts) - 1):
        pt = pts[i]
        new_pt = pts[i + 1]
        old_angle = old_bend_port.angle

        vec = pt - old_pt
        if _is_sbend_vec(vec):
            sbend_vec = (kdb.Trans(-old_angle, False, 0, 0) * vec.to_p()).to_v()
            bend_port = _copy_polar_for_placement(
                old_bend_port, d=sbend_vec.x, d_orth=sbend_vec.y, angle=2
            )
            p1_, p2_ = _place_sbend(
                c=c,
                sbend_factory=sbend_factory,
                purpose=purpose,
                w=w,
                route=route,
                p1=old_bend_port,
                p2=bend_port,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
            old_pt = pt
            old_bend_port = p2_
            if i == 1:
                route.start_port = _copy_route_endpoint(p1_)
            continue

        vec_n = new_pt - pt

        if _is_sbend_vec(vec_n):
            new_bend_port = _copy_polar_for_placement(old_bend_port, int(vec.length()))
            length = int((new_bend_port.trans.disp - old_bend_port.trans.disp).length())
            if length > 0:
                if (
                    taper_cell is None
                    or length
                    < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                    + min_straight_taper
                ):
                    _, p2_ = _place_straight(
                        c=c,
                        straight_factory=straight_factory,
                        purpose=purpose,
                        w=w,
                        route=route,
                        p1=old_bend_port,
                        p2=new_bend_port,
                        route_width=route_width,
                        port_type=port_type,
                        allow_layer_mismatch=allow_layer_mismatch,
                        allow_type_mismatch=allow_type_mismatch,
                        allow_width_mismatch=allow_width_mismatch,
                    )
                else:
                    _, p2_ = _place_tapered_straight(
                        c=c,
                        straight_factory=straight_factory,
                        taper_cell=taper_cell,
                        purpose=purpose,
                        route=route,
                        p1=old_bend_port,
                        p2=new_bend_port,
                        route_width=route_width,
                        taper_ports=(taperp1, taperp2),
                        port_type=port_type,
                        allow_width_mismatch=allow_width_mismatch,
                        allow_layer_mismatch=allow_layer_mismatch,
                        allow_type_mismatch=allow_type_mismatch,
                    )
            old_pt = pt
            old_bend_port = p2_
            continue

        if (pt.distance(old_pt) < b90r) and not allow_small_routes:
            raise ValueError(
                f"distance between points {old_pt!s} and {pt!s} is too small to"
                f" safely place bends {pt.to_s()=}, {old_pt.to_s()=},"
                f" {pt.distance(old_pt)=} < {b90r=}"
            )
        if (
            pt.distance(old_pt) < 2 * b90r
            and i not in {1, len(pts) - 1}
            and not allow_small_routes
        ):
            raise ValueError(
                f"distance between points {old_pt!s} and {pt!s} is too small to"
                f" safely place bends {pt=!s}, {old_pt=!s},"
                f" {pt.distance(old_pt)=} < {2 * b90r=}"
            )

        bend90 = c << bend90_cell
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
        new_bend_port = _instance_route_port_by_name(bend90, b90p1.name)
        length = int((new_bend_port.trans.disp - old_bend_port.trans.disp).length())
        if length > 0:
            if (
                taper_cell is None
                or length
                < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                + min_straight_taper
            ):
                p1_, p2_ = _place_straight(
                    c=c,
                    straight_factory=straight_factory,
                    purpose=purpose,
                    w=w,
                    route=route,
                    p1=old_bend_port,
                    p2=new_bend_port,
                    route_width=route_width,
                    port_type=port_type,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                    allow_width_mismatch=allow_width_mismatch,
                )
            else:
                p1_, p2_ = _place_tapered_straight(
                    c=c,
                    straight_factory=straight_factory,
                    taper_cell=taper_cell,
                    purpose=purpose,
                    route=route,
                    p1=old_bend_port,
                    p2=new_bend_port,
                    route_width=route_width,
                    taper_ports=(taperp1, taperp2),
                    port_type=port_type,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            if i == 1:
                route.start_port = _copy_route_endpoint(p1_)
        route.instances.append(bend90)
        old_pt = pt
        old_bend_port = _instance_route_port_by_name(bend90, b90p2.name)
    vec = pts[-1] - pts[-2]
    if _is_sbend_vec(vec):
        sbend_vec = (old_bend_port.trans.inverted() * pts[-1]).to_v()
        bend_port = _copy_polar_for_placement(
            old_bend_port, d=sbend_vec.x, d_orth=sbend_vec.y, angle=2
        )
        _place_sbend(
            c=c,
            sbend_factory=sbend_factory,
            purpose=purpose,
            w=w,
            route=route,
            p1=old_bend_port,
            p2=bend_port,
            allow_width_mismatch=allow_width_mismatch,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
        )
        route.end_port = bend_port
    else:
        length = int((old_bend_port.trans.disp - p2.trans.disp).length())
        if length > 0:
            if (
                taper_cell is None
                or length
                < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                + min_straight_taper
            ):
                _, p2_ = _place_straight(
                    c=c,
                    straight_factory=straight_factory,
                    purpose=purpose,
                    w=w,
                    route=route,
                    p1=old_bend_port,
                    p2=p2,
                    route_width=route_width,
                    port_type=port_type,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            else:
                _, p2_ = _place_tapered_straight(
                    c=c,
                    straight_factory=straight_factory,
                    taper_cell=taper_cell,
                    purpose=purpose,
                    route=route,
                    p1=old_bend_port,
                    p2=p2,
                    route_width=route_width,
                    taper_ports=(taperp1, taperp2),
                    port_type=port_type,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            route.end_port = _copy_route_endpoint(p2_)
        else:
            route.end_port = _copy_route_endpoint(old_bend_port)
    route.start_port.name = "route_start"
    route.end_port.name = "route_end"
    _insert_route_polygons(c, route)
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

    Raises:
        ValueError: If the ports are not parallel or point in the same direction.
    """
    t1 = port1 if isinstance(port1, kdb.Trans) else port1.trans
    t2 = port2 if isinstance(port2, kdb.Trans) else port2.trans

    (t1, port1_), (t2, _) = sorted(
        [(t1, port1), (t2, port2)], key=lambda t: -(t1.inverted() * t[0]).disp.y
    )

    if (t1.angle != t2.angle) and (
        (t1.disp.x == t2.disp.x) or (t1.disp.y == t2.disp.y)
    ):
        raise ValueError(
            "for a standard loopback the ports must point in the same direction and"
            "have to be parallel"
        )

    pz = kdb.Point(0, 0)

    if (start_straight > 0 and bend180_radius is None) or (
        start_straight <= 0 and bend180_radius is None
    ):
        pts_start = [
            t1 * pz,
            t1 * kdb.Trans(0, False, start_straight + bend90_radius, 0) * pz,
        ]
    elif start_straight > 0:
        pts_start = [t1 * pz, t1 * kdb.Trans(0, False, start_straight, 0) * pz]
    else:
        pts_start = [t1 * pz]
    if (end_straight > 0 and bend180_radius is None) or (
        end_straight <= 0 and bend180_radius is None
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
    elif bend180_radius is not None:
        t1 *= kdb.Trans(2, False, start_straight, bend180_radius)
        t2 *= kdb.Trans(2, False, end_straight, -bend180_radius)
    else:
        t1 *= kdb.Trans(2, False, start_straight + bend90_radius, 2 * bend90_radius)
        t2 *= kdb.Trans(2, False, end_straight + bend90_radius, -2 * bend90_radius)

    pts = (
        pts_start
        + route_manhattan(
            t1,
            t2,
            bend90_radius,
            start_steps=[Straight(dist=start_straight + d_loop)],
        )
        + pts_end
    )

    if port1_ == port1:
        return pts
    return list(reversed(pts))


def vec_angle(v: kdb.Vector) -> int:
    """Determine vector angle in increments of 90°.

    Returns:
        The angle of the vector in increments of 90° (0, 1, 2, 3).

    Raises:
        ValueError: If the vector is not a manhattan vector.
    """
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


def _is_sbend_vec(v: kdb.Vector) -> bool:
    return v.x != 0 and v.y != 0


def vec_angle_sbend(old_angle: int, v: kdb.Vector) -> Literal[0, 1, 2, 3]:
    if old_angle in {0, 2}:
        return 1 if v.y > 0 else 3
    return 0 if v.x > 0 else 2

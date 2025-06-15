"""Optical routing allows the creation of photonic (or any route using bends)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast, overload

from .. import kdb
from ..conf import (
    ANGLE_270,
    MIN_POINTS_FOR_PLACEMENT,
    NUM_PORTS_FOR_ROUTING,
    config,
    logger,
)
from ..instance import Instance, ProtoTInstance
from ..instance_group import InstanceGroup
from ..kcell import DKCell, KCell, ProtoTKCell
from .generic import ManhattanRoute, PlacerFunction, get_radius
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

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..factories import SBendFactoryDBU, StraightFactoryDBU, StraightFactoryUM
    from ..port import DPort, Port
    from ..typings import dbu, um

__all__ = [
    "get_radius",
    "place90",
    "place_manhattan",
    "place_manhattan_with_sbends",
    "route",
    "route_bundle",
    "route_loopback",
    "vec_angle",
]


@overload
def route_bundle(
    c: KCell,
    start_ports: Sequence[Port],
    end_ports: Sequence[Port],
    separation: dbu,
    straight_factory: StraightFactoryDBU,
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
    start_straights: um | list[um] | None = None,
    end_straights: um | list[um] | None = None,
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
    sbend_factory: SBendFactoryDBU | None = None,
) -> list[ManhattanRoute]: ...


def route_bundle(
    c: KCell | DKCell,
    start_ports: Sequence[Port] | Sequence[DPort],
    end_ports: Sequence[Port] | Sequence[DPort],
    separation: dbu | um,
    straight_factory: StraightFactoryDBU | StraightFactoryUM,
    bend90_cell: KCell | DKCell,
    taper_cell: KCell | DKCell | None = None,
    start_straights: dbu | list[dbu] | um | list[um] | None = None,
    end_straights: dbu | list[dbu] | um | list[um] | None = None,
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
    sbend_factory: SBendFactoryDBU | None = None,
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

    Returns:
        list[ManhattanRoute]: The route object with the placed components.
    """
    if ends is None:
        ends = []
    if starts is None:
        starts = []
    if bboxes is None:
        bboxes = []
    if start_straights is not None:
        logger.warning("start_straights is deprecated. Use `starts` instead.")
        starts = start_straights
    if end_straights is not None:
        logger.warning("end_straights is deprecated. Use `ends` instead.")
        ends = end_straights
    bend90_radius = get_radius(bend90_cell.ports.filter(port_type=place_port_type))
    start_ports_ = [p.base.model_copy() for p in start_ports]
    end_ports_ = [p.base.model_copy() for p in end_ports]
    if sbend_factory is None:
        placer: PlacerFunction = place_manhattan
        placer_kwargs: dict[str, Any] = {
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
            "route_width": route_width,
        }
    else:
        # Not a type error
        placer = place_manhattan_with_sbends  # type: ignore[assignment]
        placer_kwargs = {
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
            "route_width": route_width,
            "sbend_factory": sbend_factory,
        }
    if isinstance(c, KCell):
        return route_bundle_generic(
            c=c,
            start_ports=start_ports_,
            end_ports=end_ports_,
            starts=cast("dbu | list[dbu] | list[Step] | list[list[Step]]", starts),
            ends=cast("dbu | list[dbu] | list[Step] | list[list[Step]]", ends),
            route_width=cast("int", route_width),
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
                "allow_sbend": sbend_factory is not None,
            },
            placer_function=placer,
            placer_kwargs=placer_kwargs,
            start_angles=cast("list[int] | int", start_angles),
            end_angles=cast("list[int] | int", end_angles),
        )
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
            starts = [c.kcl.to_dbu(start) for start in starts]  # type: ignore[arg-type]
        starts = cast("int | list[int] | list[Step] | list[list[Step]]", starts)
    if isinstance(ends, int | float):
        ends = c.kcl.to_dbu(ends)
    elif isinstance(ends, list):
        if isinstance(ends[0], int | float):
            ends = [c.kcl.to_dbu(end) for end in ends]  # type: ignore[arg-type]
        ends = cast("int | list[int] | list[Step] | list[list[Step]]", ends)

    def _straight_factory(width: int, length: int) -> KCell:
        dkc = cast("StraightFactoryUM", straight_factory)(
            width=c.kcl.to_um(width), length=c.kcl.to_um(length)
        )
        return c.kcl[dkc.cell_index()]

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

    return route_bundle_generic(
        c=c.kcl[c.cell_index()],
        start_ports=start_ports_,
        end_ports=end_ports_,
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
            "separation": c.kcl.to_dbu(separation),
            "sort_ports": sort_ports,
            "bbox_routing": bbox_routing,
            "bboxes": list(bboxes_),
            "waypoints": waypoints,
        },
        placer_function=place_manhattan,
        placer_kwargs={
            "straight_factory": _straight_factory,
            "bend90_cell": bend90_cell,
            "taper_cell": taper_cell,
            "port_type": place_port_type,
            "min_straight_taper": min_straight_taper,
            "allow_small_routes": False,
            "allow_width_mismatch": allow_width_mismatch,
            "allow_layer_mismatch": allow_width_mismatch,
            "allow_type_mismatch": allow_type_mismatch,
            "purpose": purpose,
            "route_width": route_width,
        },
        start_angles=start_angles,
        end_angles=end_angles,
    )


def _place_straight(
    c: KCell,
    straight_factory: StraightFactoryDBU,
    purpose: str | None,
    w: int,
    route: ManhattanRoute,
    p1: Port,
    p2: Port,
    route_width: int | None,
    *,
    port_type: str,
    allow_small_routes: bool,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> tuple[Port, Port]:
    length = int((p1.trans.disp.to_p() - p2.trans.disp.to_p()).length())
    wg = c << straight_factory(width=w, length=length)
    wg.purpose = purpose
    wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
    wg.connect(
        wg_p1,
        p1,
        allow_width_mismatch=route_width is not None or allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )
    wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
    route.instances.append(wg)
    route.length_straights += length
    return wg_p1, wg_p2


def _place_sbend(
    c: KCell,
    sbend_factory: SBendFactoryDBU,
    purpose: str | None,
    w: int,
    route: ManhattanRoute,
    p1: Port,
    p2: Port,
    route_width: int | None,
    *,
    port_type: str,
    allow_small_routes: bool,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> tuple[Port, Port]:
    p1_ = p1.copy()
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

    sp1_ = sp1.copy_polar()
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
    w: int,
    route: ManhattanRoute,
    p1: Port,
    p2: Port,
    route_width: int | None,
    taper_ports: tuple[Port, Port],
    *,
    port_type: str,
    allow_small_routes: bool,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> tuple[Port, Port]:
    taperp1, taperp2 = taper_ports
    length = int((p1.trans.disp.to_p() - p2.trans.disp.to_p()).length())
    t1 = c << taper_cell
    t1.purpose = purpose
    t1.connect(
        taperp1.name,
        p1,
        allow_width_mismatch=route_width is not None or allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )
    route.instances.append(t1)
    t2 = c << taper_cell
    t2.purpose = purpose
    t2.connect(
        taperp1.name,
        p2,
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
        _, p2_ = _place_straight(
            c=c,
            straight_factory=straight_factory,
            purpose=purpose,
            w=taperp2.width,
            p1=p1_,
            p2=p2_,
            route_width=route_width,
            route=route,
            port_type=port_type,
            allow_small_routes=allow_small_routes,
            allow_width_mismatch=allow_width_mismatch,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
        )
    else:
        p2_ = t1.ports[taperp2.name]

    return t1.ports[taperp1.name], t2.ports[taperp1.name]


def _place_tapered_sbend_or_straight(
    c: KCell,
    sbend_factory: SBendFactoryDBU,
    straight_factory: StraightFactoryDBU,
    taper_cell: KCell,
    purpose: str | None,
    w: int,
    route: ManhattanRoute,
    p1: Port,
    p2: Port,
    route_width: int | None,
    taper_ports: tuple[Port, Port],
    *,
    port_type: str,
    allow_small_routes: bool,
    allow_width_mismatch: bool,
    allow_layer_mismatch: bool,
    allow_type_mismatch: bool,
) -> tuple[Port, Port]:
    taperp1, taperp2 = taper_ports
    length = int((p1.trans.disp.to_p() - p2.trans.disp.to_p()).length())
    t1 = c << taper_cell
    t1.purpose = purpose
    t1.connect(
        taperp1.name,
        p1,
        allow_width_mismatch=route_width is not None or allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
    )
    route.instances.append(t1)
    t2 = c << taper_cell
    t2.purpose = purpose
    t2.connect(
        taperp1.name,
        p2,
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
        _, p2_ = _place_sbend(
            c=c,
            sbend_factory=sbend_factory,
            purpose=purpose,
            w=taperp2.width,
            p1=p1_,
            p2=p2_,
            route_width=route_width,
            route=route,
            port_type=port_type,
            allow_small_routes=allow_small_routes,
            allow_width_mismatch=allow_width_mismatch,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
        )
    else:
        p2_ = t1.ports[taperp2.name]

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
    route_start_port = p1.copy()
    route_start_port.name = None
    route_start_port.trans.angle = (route_start_port.angle + 2) % 4
    route_end_port = p2.copy()
    route_end_port.name = None
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
                p1=route.start_port.copy_polar(),
                p2=route.end_port.copy_polar(),
                route_width=w,
                port_type=port_type,
                allow_small_routes=allow_small_routes,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
        else:
            p1_, p2_ = _place_tapered_straight(
                c=c,
                straight_factory=straight_factory,
                purpose=purpose,
                w=w,
                taper_ports=(taperp1, taperp2),
                route=route,
                p1=route.start_port.copy_polar(),
                p2=route.end_port.copy_polar(),
                route_width=w,
                port_type=port_type,
                allow_small_routes=allow_small_routes,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
                taper_cell=taper_cell,
            )
        p1_.name = None
        p2_.name = None
        route.start_port = p1
        route.end_port = p2
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
        new_bend_port = bend90.ports[b90p1.name]
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
                    allow_small_routes=allow_small_routes,
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
                    w=w,
                    route=route,
                    p1=old_bend_port,
                    p2=new_bend_port,
                    route_width=route_width,
                    taper_ports=(taperp1, taperp2),
                    port_type=port_type,
                    allow_small_routes=allow_small_routes,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            if i == 1:
                route.start_port = p1_
        route.instances.append(bend90)
        old_pt = pt
        old_bend_port = bend90.ports[b90p2.name]
    length = int((bend90.ports[b90p2.name].trans.disp - p2.trans.disp).length())
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
                p2=p2,
                route_width=route_width,
                port_type=port_type,
                allow_small_routes=allow_small_routes,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
        else:
            p1_, p2_ = _place_tapered_straight(
                c=c,
                straight_factory=straight_factory,
                taper_cell=taper_cell,
                purpose=purpose,
                w=w,
                route=route,
                p1=old_bend_port,
                p2=p2,
                route_width=route_width,
                taper_ports=(taperp1, taperp2),
                port_type=port_type,
                allow_small_routes=allow_small_routes,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
        route.end_port = p2_.copy()
    else:
        route.end_port = old_bend_port.copy()
    route.start_port.name = None
    route.end_port.name = None
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
    sbend_factory: SBendFactoryDBU,
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
    route_start_port = p1.copy()
    route_start_port.name = None
    route_start_port.trans.angle = (route_start_port.angle + 2) % 4
    route_end_port = p2.copy()
    route_end_port.name = None
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
                p2=old_bend_port.copy_polar(d=sbend_vec.x, d_orth=sbend_vec.y, angle=2),
                route_width=route_width,
                allow_small_routes=allow_small_routes,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
                port_type=port_type,
            )
        else:
            length = int(vec.length())
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
                    p1=route.start_port.copy_polar(),
                    p2=route.end_port.copy_polar(),
                    route_width=w,
                    port_type=port_type,
                    allow_small_routes=allow_small_routes,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            else:
                p1_, p2_ = _place_tapered_straight(
                    c=c,
                    straight_factory=straight_factory,
                    purpose=purpose,
                    w=w,
                    taper_ports=(taperp1, taperp2),
                    route=route,
                    p1=route.start_port.copy_polar(),
                    p2=route.end_port.copy_polar(),
                    route_width=w,
                    port_type=port_type,
                    allow_small_routes=allow_small_routes,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                    taper_cell=taper_cell,
                )
        p1.name = None
        p2.name = None
        route.start_port = p1
        route.end_port = p2
        return route

    # in other cases, place the bend and then route
    for i in range(1, len(pts) - 1):
        pt = pts[i]
        new_pt = pts[i + 1]
        old_angle = old_bend_port.angle

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
        if _is_sbend_vec(vec):
            sbend_vec = (kdb.Trans(-old_angle, False, 0, 0) * vec.to_p()).to_v()
            bend_port = old_bend_port.copy_polar(
                d=sbend_vec.x, d_orth=sbend_vec.y, angle=2
            )
            p1_, p2_ = _place_sbend(
                c=c,
                sbend_factory=sbend_factory,
                purpose=purpose,
                w=w,
                route=route,
                p1=old_bend_port,
                p2=bend_port,
                route_width=route_width,
                allow_small_routes=allow_small_routes,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
                port_type=port_type,
            )
            old_pt = pt
            old_bend_port = p2_
            if i == 1:
                route.start_port = p1_
            continue

        vec_n = new_pt - pt

        if _is_sbend_vec(vec_n):
            new_bend_port = old_bend_port.copy_polar(int(vec.length()))
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
                        allow_small_routes=allow_small_routes,
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
                        w=w,
                        route=route,
                        p1=old_bend_port,
                        p2=new_bend_port,
                        route_width=route_width,
                        taper_ports=(taperp1, taperp2),
                        port_type=port_type,
                        allow_small_routes=allow_small_routes,
                        allow_width_mismatch=allow_width_mismatch,
                        allow_layer_mismatch=allow_layer_mismatch,
                        allow_type_mismatch=allow_type_mismatch,
                    )
            old_pt = pt
            old_bend_port = p2_
            continue

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
        new_bend_port = bend90.ports[b90p1.name]
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
                    allow_small_routes=allow_small_routes,
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
                    w=w,
                    route=route,
                    p1=old_bend_port,
                    p2=new_bend_port,
                    route_width=route_width,
                    taper_ports=(taperp1, taperp2),
                    port_type=port_type,
                    allow_small_routes=allow_small_routes,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            if i == 1:
                route.start_port = p1_
        route.instances.append(bend90)
        old_pt = pt
        old_bend_port = bend90.ports[b90p2.name]
    vec = pts[-1] - pts[-2]
    if _is_sbend_vec(vec):
        sbend_vec = (old_bend_port.trans.inverted() * pts[-1]).to_v()
        bend_port = old_bend_port.copy_polar(d=sbend_vec.x, d_orth=sbend_vec.y, angle=2)
        _place_sbend(
            c=c,
            sbend_factory=sbend_factory,
            purpose=purpose,
            w=w,
            route=route,
            p1=old_bend_port,
            p2=bend_port,
            route_width=route_width,
            allow_small_routes=allow_small_routes,
            allow_width_mismatch=allow_width_mismatch,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
            port_type=port_type,
        )
        old_pt = pt
        old_bend_port = bend_port
        route.end_port = bend_port
    else:
        length = int((bend90.ports[b90p2.name].trans.disp - p2.trans.disp).length())
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
                    p2=p2,
                    route_width=route_width,
                    port_type=port_type,
                    allow_small_routes=allow_small_routes,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            else:
                p1_, p2_ = _place_tapered_straight(
                    c=c,
                    straight_factory=straight_factory,
                    taper_cell=taper_cell,
                    purpose=purpose,
                    w=w,
                    route=route,
                    p1=old_bend_port,
                    p2=p2,
                    route_width=route_width,
                    taper_ports=(taperp1, taperp2),
                    port_type=port_type,
                    allow_small_routes=allow_small_routes,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            route.end_port = p2_.copy()
        else:
            route.end_port = old_bend_port.copy()
    route.start_port.name = None
    route.end_port.name = None
    return route


def place90(
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
    sbend_factory: SBendFactoryDBU | None = None,
    **kwargs: Any,
) -> ManhattanRoute:
    """Deprecated, use place_manhattan instead.

    Will be removed with kfactory 2.0.
    """
    logger.warning(
        "place90 is deprecated, please use kfactory.routing.optical.place_manhattan"
        " instead. place90 will be removed in kfactory 2.0."
    )

    return place_manhattan(
        c=c,
        p1=p1,
        p2=p2,
        pts=pts,
        route_width=route_width,
        straight_factory=straight_factory,
        bend90_cell=bend90_cell,
        taper_cell=taper_cell,
        port_type=port_type,
        min_straight_taper=min_straight_taper,
        allow_small_routes=allow_small_routes,
        allow_width_mismatch=allow_width_mismatch,
        allow_layer_mismatch=allow_layer_mismatch,
        allow_type_mismatch=allow_type_mismatch,
        purpose=purpose,
        **kwargs,
    )


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
    straight_factory: StraightFactoryDBU,
    bend90_cell: KCell,
    bend180_cell: KCell | None = None,
    taper_cell: KCell | None = None,
    start_straight: dbu = 0,
    end_straight: dbu = 0,
    route_path_function: ManhattanRoutePathFunction = route_manhattan,
    port_type: str = "optical",
    allow_small_routes: bool = False,
    route_kwargs: dict[str, Any] | None = None,
    route_width: dbu | None = None,
    min_straight_taper: dbu = 0,
    allow_width_mismatch: bool | None = None,
    allow_layer_mismatch: bool | None = None,
    allow_type_mismatch: bool | None = None,
    purpose: str | None = "routing",
) -> ManhattanRoute:
    """Places a route between two ports.

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

    Raises:
        ValueError: If the route cannot be placed due to small space.
        AttributeError: If the bend90_cell or taper_cell do not have the correct.

    Returns:
        ManhattanRoute: The route object with the placed components.
    """
    if route_kwargs is None:
        route_kwargs = {}
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

    if len(bend90_ports) != NUM_PORTS_FOR_ROUTING:
        raise ValueError(
            f"{bend90_cell.name} should have 2 ports but has {len(bend90_ports)} ports"
        )

    if abs((bend90_ports[0].trans.angle - bend90_ports[1].trans.angle) % 4) != 1:
        raise ValueError(
            f"{bend90_cell.name} bend ports should be 90° apart from each other. "
            f"{bend90_ports[0]=} {bend90_ports[1]=}"
        )
    if (bend90_ports[1].trans.angle - bend90_ports[0].trans.angle) % 4 == ANGLE_270:
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
        bend180_ports = list(bend180_cell.ports.filter(port_type=port_type))
        if len(bend180_ports) != NUM_PORTS_FOR_ROUTING:
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
        b180p1, b180p2 = sorted(
            bend180_ports,
            key=lambda port: (d * port.trans.disp.x, d * port.trans.disp.y),
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

        if len(pts) > 2:  # noqa: PLR2004
            if (vec := pts[1] - pts[0]).length() == b180r:
                match (p1.trans.angle - vec_angle(vec)) % 4:
                    case 1:
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.connect(
                            b180p1.name,
                            p1,
                            allow_width_mismatch=allow_width_mismatch,
                            allow_layer_mismatch=allow_layer_mismatch,
                            allow_type_mismatch=allow_type_mismatch,
                        )
                        start_port = bend180.ports[b180p2.name]
                        pts = pts[1:]
                    case 3:
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.connect(
                            b180p2.name,
                            p1,
                            allow_width_mismatch=allow_width_mismatch,
                            allow_layer_mismatch=allow_layer_mismatch,
                            allow_type_mismatch=allow_type_mismatch,
                        )
                        start_port = bend180.ports[b180p1.name]
                        pts = pts[1:]
            if (vec := pts[-1] - pts[-2]).length() == b180r:
                match (vec_angle(vec) - p2.trans.angle) % 4:
                    case 1:
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.connect(
                            b180p1.name,
                            p2,
                            allow_width_mismatch=allow_width_mismatch,
                            allow_layer_mismatch=allow_layer_mismatch,
                            allow_type_mismatch=allow_type_mismatch,
                        )
                        end_port = bend180.ports[b180p2.name]
                        pts = pts[:-1]
                    case 3:
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.connect(
                            b180p2.name,
                            p2,
                            allow_width_mismatch=allow_width_mismatch,
                            allow_layer_mismatch=allow_layer_mismatch,
                            allow_type_mismatch=allow_type_mismatch,
                        )
                        end_port = bend180.ports[b180p1.name]
                        pts = pts[:-1]

            if len(pts) > 3:  # noqa: PLR2004
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
                            bend180.connect(
                                b180p1.name,
                                start_port,
                                allow_width_mismatch=allow_width_mismatch,
                                allow_layer_mismatch=allow_layer_mismatch,
                                allow_type_mismatch=allow_type_mismatch,
                            )
                            start_port = bend180.ports[b180p2.name]
                        else:
                            bend180.connect(
                                b180p2.name,
                                start_port,
                                allow_width_mismatch=allow_width_mismatch,
                                allow_layer_mismatch=allow_layer_mismatch,
                                allow_type_mismatch=allow_type_mismatch,
                            )
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
                        place_manhattan(
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
                        and (ang2 - ang1) % 4 == ANGLE_270
                        and (ang3 - ang2) % 4 == ANGLE_270
                    ):
                        bend180 = c << bend180_cell
                        bend180.purpose = purpose
                        bend180.transform(
                            kdb.Trans((ang1 + 2) % 4, False, pt2.x, pt2.y)
                            * b180p2.trans.inverted()
                        )
                        place_manhattan(
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

        route = place_manhattan(
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

        route = place_manhattan(
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

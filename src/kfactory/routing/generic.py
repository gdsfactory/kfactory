"""Generic routing functions which are independent of the potential use."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any, Literal, Protocol, cast

from pydantic import BaseModel, Field

from .. import kdb, rdb
from ..conf import config, logger
from ..kcell import Instance, KCell, Port
from ..kf_types import dbu
from .manhattan import (
    ManhattanBundleRoutingFunction,
    ManhattanRouter,
    route_smart,
)
from .steps import Step, Straight

__all__ = [
    "PlacerFunction",
    "ManhattanRoute",
    "check_collisions",
    "get_radius",
    "route_bundle",
]


class PlacerError(ValueError):
    pass


class PlacerFunction(Protocol):
    """A placer function. Used to place Instances given a path."""

    def __call__(
        self,
        c: KCell,
        p1: Port,
        p2: Port,
        pts: Sequence[kdb.Point],
        route_width: dbu | None = None,
        **kwargs: Any,
    ) -> ManhattanRoute:
        """Implementation of the function."""


class RouterPostProcessFunction(Protocol):
    """A function that can be used to post process functions."""

    def __call__(
        self,
        *,
        c: KCell,
        routers: list[ManhattanRouter],
        start_ports: list[Port],
        end_ports: list[Port],
        **kwargs: Any,
    ) -> None:
        """Implementation of post process function."""


class ManhattanRoute(BaseModel, arbitrary_types_allowed=True):
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
    instances: list[Instance] = Field(default_factory=list)
    n_bend90: int = 0
    n_taper: int = 0
    bend90_radius: dbu = 0
    taper_length: dbu = 0
    length: dbu = 0
    """Length of backbone without the bends."""
    length_straights: dbu = 0
    polygons: dict[kdb.LayerInfo, list[kdb.Polygon]] = Field(default_factory=dict)

    @property
    def length_backbone(self) -> dbu:
        """Length of the backbone in dbu."""
        length = 0
        p_old = self.backbone[0]
        for p in self.backbone[1:]:
            length += int((p - p_old).length())
            p_old = p
        return length


def check_collisions(
    c: KCell,
    start_ports: list[Port],
    end_ports: list[Port],
    routers: list[ManhattanRouter],
    routes: list[ManhattanRoute],
    on_collision: Literal["error", "show_error"] | None = "show_error",
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
) -> None:
    """Checks for collisions given manhattan routes.

    Args:
        c: The KCell to check.
        start_ports: Ports from which the routes are supposed to start.
        end_ports: Ports where the routes are supposed to end.
        routers: The ManhattanRouters that constructed the routes.
        routes: The ManhatnnaRoutes which were used by the placer.
        on_collision: What to do on error. Can either do nothing (None),
            throw an error ("error"), or throw an error and open the
            cell with report in Klayout ("show_error").
        collision_check_layers: Sequence of layers which should be checked for
            overlaps to determine error. If not defined, all layers occurring in
            ports will be used.
    """
    if on_collision is None:
        return
    collision_edges: dict[str, kdb.Edges] = {}
    inter_route_collisions = kdb.Edges()
    all_router_edges = kdb.Edges()
    for i, (ps, pe, router) in enumerate(zip(start_ports, end_ports, routers)):
        _edges, router_edges = router.collisions(log_errors=None)
        if not _edges.is_empty():
            collision_edges[f"{ps.name} - {pe.name} (index: {i})"] = _edges
        inter_route_collision = all_router_edges.interacting(router_edges)
        if not inter_route_collision.is_empty():
            inter_route_collisions.join_with(inter_route_collision)
        all_router_edges.join_with(router_edges)

    if collision_edges or not inter_route_collisions.is_empty():
        if collision_check_layers is None:
            collision_check_layers = list({p.layer_info for p in start_ports})
        dbu = c.kcl.dbu
        db = rdb.ReportDatabase("Routing Errors")
        cat = db.create_category("Manhattan Routing Collisions")
        c.name = c.name[: config.max_cellname_length]
        cell = db.create_cell(c.name)
        for name, edges in collision_edges.items():
            item = db.create_item(cell, cat)
            item.add_value(name)
            for edge in edges.each():
                item.add_value(edge.to_dtype(dbu))
        insts = [inst for route in routes for inst in route.instances]
        shapes: dict[kdb.LayerInfo, list[kdb.Region]] = defaultdict(list)
        for route in routes:
            for layer, _shapes in route.polygons.items():
                shapes[layer].append(kdb.Region(_shapes))
        layer_cats: dict[kdb.LayerInfo, rdb.RdbCategory] = {}

        def layer_cat(layer_info: kdb.LayerInfo) -> rdb.RdbCategory:
            if layer_info not in layer_cats:
                layer_cats[layer_info] = db.category_by_path(
                    layer_info.to_s()
                ) or db.create_category(layer_info.to_s())
            return layer_cats[layer_info]

        any_layer_collision = False

        for layer_info in collision_check_layers:
            shapes_regions = shapes[layer_info]
            layer = c.kcl.layer(layer_info)
            error_region_instances = kdb.Region()
            error_region_shapes = kdb.Region()
            inst_regions: dict[int, kdb.Region] = {}
            inst_region = kdb.Region()
            shape_region = kdb.Region()
            for r in shapes_regions:
                if not (shape_region & r).is_empty():
                    error_region_shapes.insert(shape_region & r)
                shape_region.insert(r)
            for i, inst in enumerate(insts):
                _inst_region = kdb.Region(inst.bbox(layer))
                # inst_shapes: kdb.Region | None = None
                if not (inst_region & _inst_region).is_empty():
                    # if inst_shapes is None:
                    inst_shapes = kdb.Region()
                    shape_it = c.begin_shapes_rec_overlapping(layer, inst.bbox(layer))
                    shape_it.select_cells([inst.cell.cell_index()])
                    shape_it.min_depth = 1
                    for _it in shape_it.each():
                        if _it.path()[0].inst() == inst._instance:
                            inst_shapes.insert(
                                _it.shape().polygon.transformed(_it.trans())
                            )
                    for j, _reg in inst_regions.items():
                        if _reg & _inst_region:
                            __reg = kdb.Region()
                            shape_it = c.begin_shapes_rec_touching(
                                layer, (_reg & _inst_region).bbox()
                            )
                            shape_it.select_cells([insts[j].cell.cell_index()])
                            shape_it.min_depth = 1
                            for _it in shape_it.each():
                                if _it.path()[0].inst() == insts[j]._instance:
                                    __reg.insert(
                                        _it.shape().polygon.transformed(_it.trans())
                                    )

                            error_region_instances.insert(__reg & inst_shapes)
                inst_region += _inst_region
                inst_regions[i] = _inst_region

            if not error_region_shapes.is_empty():
                any_layer_collision = True
                if on_collision == "error":
                    continue
                cat = layer_cat(layer_info)
                sc = db.category_by_path(
                    f"{cat.path()}.RoutingErrors"
                ) or db.create_category(layer_cat(layer_info), "RoutingErrors")
                for poly in error_region_shapes.merge().each():
                    it = db.create_item(cell, sc)
                    it.add_value("Route shapes overlapping with other shapes")
                    it.add_value(c.kcl.to_um(poly))
            if not error_region_instances.is_empty():
                any_layer_collision = True
                if on_collision == "error":
                    continue
                cat = layer_cat(layer_info)
                sc = db.category_by_path(
                    f"{cat.path()}.RoutingErrors"
                ) or db.create_category(layer_cat(layer_info), "RoutingErrors")
                for poly in error_region_instances.merge().each():
                    it = db.create_item(cell, sc)
                    it.add_value("Route instances overlapping with other instances")
                    it.add_value(c.kcl.to_um(poly))

        if any_layer_collision:
            match on_collision:
                case "show_error":
                    c.show(lyrdb=db)
                    raise RuntimeError(
                        f"Routing collision in {c.kcl.future_cell_name or c.name}"
                    )
                case "error":
                    raise RuntimeError(
                        f"Routing collision in {c.kcl.future_cell_name or c.name}"
                    )


def get_radius(
    ports: Iterable[Port],
) -> dbu:
    """Calculates a radius between two ports.

    This can be used to determine the radius of two bend ports.
    """
    ports = tuple(ports)
    if len(ports) != 2:
        raise ValueError(
            "Cannot determine the maximal radius of a bend with more than two ports."
        )
    p1, p2 = ports
    if p1.angle == p2.angle:
        return int((p1.trans.disp - p2.trans.disp).length())
    _p = kdb.Point(1, 0)
    e1 = kdb.Edge(p1.trans.disp.to_p(), p1.trans * _p)
    e2 = kdb.Edge(p2.trans.disp.to_p(), p2.trans * _p)

    center = e1.cut_point(e2)
    if center is None:
        raise ValueError("Could not determine the radius. Something went very wrong.")
    return int(
        max((p1.trans.disp - center).length(), (p2.trans.disp - center).length())
    )


def route_bundle(
    *,
    c: KCell,
    start_ports: list[Port],
    end_ports: list[Port],
    route_width: dbu | list[dbu] | None = None,
    sort_ports: bool = False,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    routing_function: ManhattanBundleRoutingFunction = route_smart,
    routing_kwargs: dict[str, Any] = {"bbox_routing": "minimal"},
    placer_function: PlacerFunction,
    placer_kwargs: dict[str, Any] = {},
    router_post_process_function: RouterPostProcessFunction | None = None,
    router_post_process_kwargs: dict[str, Any] = {},
    starts: dbu | list[dbu] | list[Step] | list[list[Step]] = [],
    ends: dbu | list[dbu] | list[Step] | list[list[Step]] = [],
    start_angles: int | list[int] | None = None,
    end_angles: int | list[int] | None = None,
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
        starts: List of steps to use on each starting port or all of them.
        ends: List of steps to use on each end port or all of them.
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
        route_width: Width of the route. If None, the width of the ports is used.
        sort_ports: Automatically sort ports.
        bbox_routing: "minimal": only route to the bbox so that it can be safely routed
            around, but start or end bends might encroach on the bounding boxes when
            leaving them.
        bend90_radius: The radius with which the router will try to router. This should
            normally be the maximal radius used.
        placer_function: Function to place the routes. Must return a corresponding list
            of OpticalManhattan routes.
            Must accept the following protocol:
            ```
            placer_function(
                c: KCell, p1: Port, p2: Port, pts: list[Point], **placer_kwargs
            )
            ```
        placer_kwargs: Additional kwargs passed to the placer_function.
        routing_function: Function to place the routes. Must return a corresponding list
            of OpticalManhattan routes.
            Must accept the following protocol:
            ```
            routing_function(
                c: KCell, p1: Port, p2: Port, pts: list[Point], **placer_kwargs
            )
            ```
        routing_kwargs: Additional kwargs passed to the placer_function.
        router_post_process_function: Function used to modify the routers returned by
            the routing function. This is particularly useful for operations such as
            path length matching.
        router_post_process_kwargs: Kwargs for router_post_process_function.
        start_angles: Overwrite the port orientation of all start_ports together
            (single value) or each one (list of values which is as long as start_ports).
        end_angles: Overwrite the port orientation of all start_ports together
            (single value) or each one (list of values which is as long as end_ports).
    """
    if not start_ports:
        return []
    if not (len(start_ports) == len(end_ports)):
        raise ValueError(
            "For bundle routing the input port list must have"
            " the same size as the end ports and be the same length."
        )
    length = len(start_ports)
    if starts == []:
        starts = [starts] * length  # type: ignore[assignment]
    elif isinstance(starts, int):
        starts = [[Straight(dist=starts)] for _ in range(length)]  # type: ignore[assignment]
    elif isinstance(starts[0], Step):
        starts = [starts for _ in range(len(start_ports))]  # type: ignore[assignment]
    if ends == []:
        ends = [ends] * length  # type: ignore[assignment]
    elif isinstance(ends, int):
        ends = [[Straight(dist=ends)] for _ in range(length)]  # type: ignore[assignment]
    elif isinstance(ends[0], Step):
        ends = [ends for _ in range(len(start_ports))]  # type: ignore[assignment]

    if start_angles is not None:
        if isinstance(start_angles, int):
            start_ports = [
                p.copy(post_trans=kdb.Trans(start_angles - p.trans.angle))
                for p in start_ports
            ]
        else:
            if not len(start_angles) == len(start_ports):
                raise ValueError(
                    "If more than one end port should be rotated,"
                    " a rotation for all ports must be provided."
                )
            start_ports = [
                p.copy(post_trans=kdb.Trans(a - p.trans.angle))
                for a, p in zip(start_angles, start_ports)
            ]

    if end_angles is not None:
        if isinstance(end_angles, int):
            end_ports = [
                p.copy(post_trans=kdb.Trans(end_angles - p.trans.angle))
                for p in end_ports
            ]
        else:
            if not len(end_angles) == len(end_ports):
                raise ValueError(
                    "If more than one end port should be rotated,"
                    " a rotation for all ports must be provided."
                )
            end_ports = [
                p.copy(post_trans=kdb.Trans(a - p.trans.angle))
                for a, p in zip(end_angles, start_ports)
            ]

    if route_width:
        if isinstance(route_width, int):
            widths = [route_width] * len(start_ports)
        else:
            widths = route_width
    else:
        widths = [p.width for p in start_ports]

    routers = routing_function(
        start_ports=start_ports,
        end_ports=end_ports,
        widths=widths,
        starts=cast(list[list[Step]], starts),
        ends=cast(list[list[Step]], ends),
        **routing_kwargs,
    )

    if not routers:
        return []

    start_mapping = {sp.trans: sp for sp in start_ports}
    end_mapping = {ep.trans: ep for ep in end_ports}
    routes: list[ManhattanRoute] = []
    start_ports = []
    end_ports = []

    for router in routers:
        sp = start_mapping[router.start_transformation]
        ep = end_mapping[router.end_transformation]
        start_ports.append(sp)
        end_ports.append(ep)

    if router_post_process_function is not None:
        router_post_process_function(
            c=c,
            start_ports=start_ports,
            end_ports=end_ports,
            routers=routers,
            **router_post_process_kwargs,
        )
    placer_errors: list[Exception] = []
    error_routes: list[tuple[Port, Port, list[kdb.Point], int]] = []
    for router, ps, pe in zip(routers, start_ports, end_ports):
        try:
            route = placer_function(
                c,
                ps,
                pe,
                router.start.pts,
                **placer_kwargs,
            )
            routes.append(route)
        except Exception as e:
            placer_errors.append(e)
            error_routes.append((ps, pe, router.start.pts, router.width))
    if placer_errors and on_placer_error == "show_error":
        print(len(placer_errors))
        db = rdb.ReportDatabase("Route Placing Errors")
        cell = db.create_cell(
            c.name
            if not c.name.startswith("Unnamed_")
            else c.kcl.future_cell_name or c.name
        )
        for error, (ps, pe, pts, width) in zip(placer_errors, error_routes):
            cat = db.create_category(f"{ps.name} - {pe.name}")
            it = db.create_item(cell=cell, category=cat)
            it.add_value(
                f"Error while trying to place route from {ps.name} to {pe.name} at"
                f" points (dbu): {pts}"
            )
            it.add_value(f"Exception: {error}")
            path = kdb.Path(pts, width or ps.width)
            print(f"{width=}")
            it.add_value(c.kcl.to_um(path.polygon()))
        c.show(lyrdb=db)
    if placer_errors and on_placer_error is not None:
        for error in placer_errors:
            logger.error(error)
        raise PlacerError(
            "Failed to place routes for bundle routing from "
            f"{[p.name for p in start_ports]} to {[p.name for p in end_ports]}"
        )

    check_collisions(
        c=c,
        start_ports=start_ports,
        end_ports=end_ports,
        on_collision=on_collision,
        collision_check_layers=collision_check_layers,
        routers=routers,
        routes=routes,
    )
    return routes

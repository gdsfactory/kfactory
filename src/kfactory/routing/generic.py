"""Generic routing functions which are independent of the potential use."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

import klayout.db as kdb
from klayout import rdb
from pydantic import BaseModel, Field

from ..conf import config, logger
from ..instance import Instance  # noqa: TC001
from ..port import BasePort, Port, ProtoPort
from ..typings import dbu  # noqa: TC001
from .length_functions import LengthFunction, get_length_from_area
from .manhattan import (
    ManhattanBundleRoutingFunction,
    ManhattanRouter,
    route_smart,
)
from .steps import Step, Straight

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..kcell import KCell

__all__ = [
    "ManhattanRoute",
    "PlacerFunction",
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
        route_width: int | None = None,
        **kwargs: Any,
    ) -> ManhattanRoute:
        """Implementation of the function."""
        ...


class RouterPostProcessFunction(Protocol):
    """A function that can be used to post process functions."""

    def __call__(
        self,
        *,
        c: KCell,
        routers: Sequence[ManhattanRouter],
        start_ports: Sequence[BasePort],
        end_ports: Sequence[BasePort],
        **kwargs: Any,
    ) -> None:
        """Implementation of post process function."""
        ...


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
    """Length of backbone without the bends."""
    length_straights: dbu = 0
    polygons: dict[kdb.LayerInfo, list[kdb.Polygon]] = Field(default_factory=dict)
    length_function: LengthFunction = Field(default_factory=get_length_from_area)

    @property
    def length_backbone(self) -> dbu:
        """Length of the backbone in dbu."""
        length = 0
        p_old = self.backbone[0]
        for p in self.backbone[1:]:
            length += int((p - p_old).length())
            p_old = p
        return length

    @property
    def length(self) -> int | float:
        return self.length_function(self)


def check_collisions(
    c: KCell,
    start_ports: Sequence[BasePort],
    end_ports: Sequence[BasePort],
    routers: Sequence[ManhattanRouter],
    routes: Sequence[ManhattanRoute],
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
    for i, (ps, pe, router) in enumerate(
        zip(start_ports, end_ports, routers, strict=False)
    ):
        edges_, router_edges = router.collisions(log_errors=None)
        if not edges_.is_empty():
            collision_edges[f"{ps.name} - {pe.name} (index: {i})"] = edges_
        inter_route_collision = all_router_edges.interacting(router_edges)
        if not inter_route_collision.is_empty():
            inter_route_collisions.join_with(inter_route_collision)
        all_router_edges.join_with(router_edges)

    if collision_edges or not inter_route_collisions.is_empty():
        if collision_check_layers is None:
            collision_check_layers = list(
                {p.cross_section.main_layer for p in start_ports}
            )
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
            layer_ = c.kcl.layout.layer(layer_info)
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
                inst_region_ = kdb.Region(inst.bbox(layer_))
                if not (inst_region & inst_region_).is_empty():
                    # if inst_shapes is None:
                    inst_shapes = kdb.Region()
                    shape_it = c.begin_shapes_rec_overlapping(layer_, inst.bbox(layer_))
                    shape_it.select_cells([inst.cell.cell_index()])
                    shape_it.min_depth = 1
                    for _it in shape_it.each():
                        if _it.path()[0].inst() == inst.instance:
                            inst_shapes.insert(
                                _it.shape().polygon.transformed(_it.trans())
                            )
                    for j, _reg in inst_regions.items():
                        if _reg & inst_region_:
                            reg = kdb.Region()
                            shape_it = c.begin_shapes_rec_touching(
                                layer_, (_reg & inst_region_).bbox()
                            )
                            shape_it.select_cells([insts[j].cell.cell_index()])
                            shape_it.min_depth = 1
                            for _it in shape_it.each():
                                if _it.path()[0].inst() == insts[j].instance:
                                    reg.insert(
                                        _it.shape().polygon.transformed(_it.trans())
                                    )

                            error_region_instances.insert(reg & inst_shapes)
                inst_region += inst_region_
                inst_regions[i] = inst_region_

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
                    it.add_value(c.kcl.to_um(poly.downcast()))
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
                    it.add_value(c.kcl.to_um(poly.downcast()))

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


PORTS_FOR_RADIUS = 2


def get_radius(ports: Sequence[ProtoPort[Any]]) -> dbu:
    """Calculates a radius between two ports.

    This can be used to determine the radius of two bend ports.

    Args:
        ports: A sequence of exactly two ports.

    Returns:
        Radius in dbu.

    Raises:
        ValueError: Radius cannot be determined
    """
    ports_ = tuple(p.to_itype() for p in ports)
    if len(ports_) != PORTS_FOR_RADIUS:
        raise ValueError(
            "Cannot determine the maximal radius of a bend with more than two ports."
        )
    p1, p2 = ports_
    if p1.angle == p2.angle:
        return int((p1.trans.disp - p2.trans.disp).length())
    p = kdb.Point(1, 0)
    e1 = kdb.Edge(p1.trans.disp.to_p(), p1.trans * p)
    e2 = kdb.Edge(p2.trans.disp.to_p(), p2.trans * p)

    center = e1.cut_point(e2)
    if center is None:
        raise ValueError("Could not determine the radius. Something went very wrong.")
    return int(
        max((p1.trans.disp - center).length(), (p2.trans.disp - center).length())
    )


def route_bundle(
    *,
    c: KCell,
    start_ports: list[BasePort],
    end_ports: list[BasePort],
    route_width: dbu | list[dbu] | None = None,
    sort_ports: bool = False,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    on_placer_error: Literal["error", "show_error"] | None = "show_error",
    collision_check_layers: Sequence[kdb.LayerInfo] | None = None,
    routing_function: ManhattanBundleRoutingFunction = route_smart,
    routing_kwargs: dict[str, Any] | None = None,
    placer_function: PlacerFunction,
    placer_kwargs: dict[str, Any] | None = None,
    router_post_process_function: RouterPostProcessFunction | None = None,
    router_post_process_kwargs: dict[str, Any] | None = None,
    starts: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None,
    ends: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None,
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
        route_width: Width of the route. If None, the width of the ports is used.
        sort_ports: Automatically sort ports.
        on_collision: Define what to do on routing collision. Default behaviour is to
            open send the layout of c to klive and open an error lyrdb with the
            collisions. "error" will simply raise an error. None will ignore any error.
        on_placer_error: If a placing of the components fails, use the strategy above to
            handle the error. show_error will visualize it in klayout with the intended
            route along the already placed parts of c. Error will just throw an error.
            None will ignore the error.
        collision_check_layers: Layers to check for actual errors if manhattan routes
            detect potential collisions.
        routing_function: Function to place the routes. Must return a corresponding list
            of OpticalManhattan routes.
            Must accept the following protocol:
            ```
            routing_function(
                c: KCell, p1: Port, p2: Port, pts: list[Point], **placer_kwargs
            )
            ```
        routing_kwargs: Additional kwargs passed to the placer_function.
        placer_function: Function to place the routes. Must return a corresponding list
            of OpticalManhattan routes.
            Must accept the following protocol:
            ```
            placer_function(
                c: KCell, p1: Port, p2: Port, pts: list[Point], **placer_kwargs
            )
            ```
        placer_kwargs: Additional kwargs passed to the placer_function.
        router_post_process_function: Function used to modify the routers returned by
            the routing function. This is particularly useful for operations such as
            path length matching.
        router_post_process_kwargs: Kwargs for router_post_process_function.
        starts: List of steps to use on each starting port or all of them.
        ends: List of steps to use on each end port or all of them.
        start_angles: Overwrite the port orientation of all start_ports together
            (single value) or each one (list of values which is as long as start_ports).
        end_angles: Overwrite the port orientation of all start_ports together
            (single value) or each one (list of values which is as long as end_ports).

    Returns:
        List of ManattanRoutes containing the instances of the route.

    Raises:
        PlacerError: Something went wrong and the resulting route of the placer function
            is not manhattan or the elements cannot be fitted.
        ValueError: Ports or places or args are misconfigured.
    """
    if ends is None:
        ends = []
    if starts is None:
        starts = []
    if router_post_process_kwargs is None:
        router_post_process_kwargs = {}
    if placer_kwargs is None:
        placer_kwargs = {}
    if routing_kwargs is None:
        routing_kwargs = {"bbox_routing": "minimal"}
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
                p.transformed(post_trans=kdb.Trans(start_angles - p.get_trans().angle))
                for p in start_ports
            ]
        else:
            if not len(start_angles) == len(start_ports):
                raise ValueError(
                    "If more than one end port should be rotated,"
                    " a rotation for all ports must be provided."
                )
            start_ports = [
                p.transformed(post_trans=kdb.Trans(a - p.get_trans().angle))
                for a, p in zip(start_angles, start_ports, strict=False)
            ]

    if end_angles is not None:
        if isinstance(end_angles, int):
            end_ports = [
                p.transformed(post_trans=kdb.Trans(end_angles - p.get_trans().angle))
                for p in end_ports
            ]
        else:
            if not len(end_angles) == len(end_ports):
                raise ValueError(
                    "If more than one end port should be rotated,"
                    " a rotation for all ports must be provided."
                )
            end_ports = [
                p.transformed(post_trans=kdb.Trans(a - p.get_trans().angle))
                for a, p in zip(end_angles, start_ports, strict=False)
            ]

    if route_width:
        if isinstance(route_width, int):
            widths = [route_width] * len(start_ports)
        else:
            widths = route_width
    else:
        widths = [p.cross_section.width for p in start_ports]

    routers = routing_function(
        start_ports=start_ports,
        end_ports=end_ports,
        widths=widths,
        starts=cast("list[list[Step]]", starts),
        ends=cast("list[list[Step]]", ends),
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
    error_routes: list[tuple[BasePort, BasePort, list[kdb.Point], int]] = []
    for router, ps, pe in zip(routers, start_ports, end_ports, strict=False):
        try:
            route = placer_function(
                c,
                Port(base=ps),
                Port(base=pe),
                router.start.pts,
                **placer_kwargs,
            )
            routes.append(route)
        except Exception as e:
            placer_errors.append(e)
            error_routes.append((ps, pe, router.start.pts, router.width))
    if placer_errors and on_placer_error == "show_error":
        db = rdb.ReportDatabase("Route Placing Errors")
        cell = db.create_cell(
            c.name
            if not c.name.startswith("Unnamed_")
            else c.kcl.future_cell_name or c.name
        )
        for error, (ps, pe, pts, width) in zip(
            placer_errors, error_routes, strict=False
        ):
            cat = db.create_category(f"{ps.name} - {pe.name}")
            it = db.create_item(cell=cell, category=cat)
            it.add_value(
                f"Error while trying to place route from {ps.name} to {pe.name} at"
                f" points (dbu): {pts}"
            )
            it.add_value(f"Exception: {error}")
            path = kdb.Path(pts, width or ps.cross_section.width)
            it.add_value(c.kcl.to_um(path.polygon()))
        c.show(lyrdb=db)
    if placer_errors and on_placer_error is not None:
        for error in placer_errors:
            logger.error(error)
        if c.name.startswith("Unnamed_"):
            c.name = c.kcl.future_cell_name or c.name
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

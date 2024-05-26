"""Optical routing allows the creation of photonic (or any route using bends)."""

from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel

from .. import kdb, rdb
from ..conf import config
from ..factories import StraightFactory
from ..kcell import Instance, KCell, LayerEnum, Port
from .manhattan import (
    ManhattanRoutePathFunction,
    route_manhattan,
    route_smart,
)

__all__ = [
    "OpticalManhattanRoute",
    "vec_angle",
    "route_loopback",
    "route",
    "route_bundle",
    "place90",
]


class OpticalManhattanRoute(BaseModel, arbitrary_types_allowed=True):
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
    instances: list[Instance]
    n_bend90: int = 0
    length: int = 0
    length_straights: int = 0

    @property
    def length_backbone(self) -> int:
        """Length of the backbone in dbu."""
        length = 0
        p_old = self.backbone[0]
        for p in self.backbone[1:]:
            length += int((p - p_old).length())
            p_old = p
        return length


def vec_angle(v: kdb.Vector) -> int:
    """Determine vector angle in increments of 90°."""
    if v.x != 0 and v.y != 0:
        raise NotImplementedError("only manhattan vectors supported")

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
            config.logger.warning(f"{v} is not a manhattan, cannot determine direction")
    return -1


def route_loopback(
    port1: Port | kdb.Trans,
    port2: Port | kdb.Trans,
    bend90_radius: int,
    bend180_radius: int | None = None,
    start_straight: int = 0,
    end_straight: int = 0,
    d_loop: int = 200000,
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

    if (
        start_straight > 0
        and bend180_radius is None
        or start_straight <= 0
        and bend180_radius is None
    ):
        pts_start = [
            t1 * pz,
            t1 * kdb.Trans(0, False, start_straight + bend90_radius, 0) * pz,
        ]
    elif start_straight > 0:
        pts_start = [t1 * pz, t1 * kdb.Trans(0, False, start_straight, 0) * pz]
    else:
        pts_start = [t1 * pz]
    if (
        end_straight > 0
        and bend180_radius is None
        or end_straight <= 0
        and bend180_radius is None
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
    else:
        if bend180_radius is not None:
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
            start_straight=start_straight + d_loop,
            end_straight=0,
        )
        + pts_end
    )


@config.logger.catch(reraise=True)
def route(
    c: KCell,
    p1: Port,
    p2: Port,
    straight_factory: StraightFactory,
    bend90_cell: KCell,
    bend180_cell: KCell | None = None,
    taper_cell: KCell | None = None,
    start_straight: int = 0,
    end_straight: int = 0,
    route_path_function: ManhattanRoutePathFunction = route_manhattan,
    port_type: str = "optical",
    allow_small_routes: bool = False,
    route_kwargs: dict[str, Any] | None = {},
    min_straight_taper: int = 0,
    allow_width_mismatch: bool = config.allow_width_mismatch,
    allow_layer_mismatch: bool = config.allow_layer_mismatch,
    allow_type_mismatch: bool = config.allow_type_mismatch,
) -> OpticalManhattanRoute:
    """Places a route.

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
        min_straight_taper: Minimum straight [dbu] before attempting to place tapers.
        allow_width_mismatch: If True, the width of the ports is ignored
            (config default: False).
        allow_layer_mismatch: If True, the layer of the ports is ignored
            (config default: False).
        allow_type_mismatch: If True, the type of the ports is ignored
            (config default: False).
    """
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

    if len(bend90_ports) != 2:
        raise ValueError(
            f"{bend90_cell.name} should have 2 ports but has {len(bend90_ports)} ports"
        )

    if abs((bend90_ports[0].trans.angle - bend90_ports[1].trans.angle) % 4) != 1:
        raise ValueError(
            f"{bend90_cell.name} bend ports should be 90° apart from each other"
        )
    if (bend90_ports[1].trans.angle - bend90_ports[0].trans.angle) % 4 == 3:
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
        bend180_ports = [p for p in bend180_cell.ports if p.port_type == port_type]
        if len(bend180_ports) != 2:
            raise AttributeError(
                f"{bend180_cell.name} should have 2 ports but has {len(bend180_ports)}"
                " ports"
            )
        if abs((bend180_ports[0].trans.angle - bend180_ports[1].trans.angle) % 4) != 0:
            raise AttributeError(
                f"{bend180_cell.name} bend ports for bend180 should be 0° apart from"
                " each other"
            )
        d = 1 if bend180_ports[0].trans.angle in [0, 3] else -1
        b180p1, b180p2 = list(
            sorted(
                bend180_ports,
                key=lambda port: (d * port.trans.disp.x, d * port.trans.disp.y),
            )
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

        if len(pts) > 2:
            if (vec := pts[1] - pts[0]).length() == b180r:
                match (p1.trans.angle - vec_angle(vec)) % 4:
                    case 1:
                        bend180 = c << bend180_cell
                        bend180.connect(b180p1.name, p1)
                        start_port = bend180.ports[b180p2.name]
                        pts = pts[1:]
                    case 3:
                        bend180 = c << bend180_cell
                        bend180.connect(b180p2.name, p1)
                        start_port = bend180.ports[b180p1.name]
                        pts = pts[1:]
            if (vec := pts[-1] - pts[-2]).length() == b180r:
                match (vec_angle(vec) - p2.trans.angle) % 4:
                    case 1:
                        bend180 = c << bend180_cell
                        bend180.connect(b180p1.name, p2)
                        end_port = bend180.ports[b180p2.name]
                        pts = pts[:-1]
                    case 3:
                        bend180 = c << bend180_cell
                        # bend180.mirror = True
                        bend180.connect(b180p2.name, p2)
                        end_port = bend180.ports[b180p1.name]
                        pts = pts[:-1]

            if len(pts) > 3:
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
                        if start_port.name == b180p2.name:
                            bend180.connect(b180p1.name, start_port)
                            start_port = bend180.ports[b180p2.name]
                        else:
                            bend180.connect(b180p2.name, start_port)
                            start_port = bend180.ports[b180p1.name]
                        j = i - 1
                    elif (
                        vec.length() == b180r
                        and (ang2 - ang1) % 4 == 1
                        and (ang3 - ang2) % 4 == 1
                    ):
                        bend180 = c << bend180_cell
                        bend180.transform(
                            kdb.Trans((ang1 + 2) % 4, False, pt2.x, pt2.y)
                            * b180p1.trans.inverted()
                        )
                        place90(
                            c,
                            start_port.copy(),
                            bend180.ports[b180p1.name],
                            pts[j : i - 2],
                            straight_factory,
                            bend90_cell,
                            taper_cell,
                            port_type=port_type,
                            allow_small_routes=allow_small_routes,
                            allow_width_mismatch=allow_width_mismatch,
                            allow_layer_mismatch=allow_layer_mismatch,
                            allow_type_mismatch=allow_type_mismatch,
                        )
                        j = i - 1
                        start_port = bend180.ports[b180p2.name]
                    elif (
                        vec.length() == b180r
                        and (ang2 - ang1) % 4 == 3
                        and (ang3 - ang2) % 4 == 3
                    ):
                        bend180 = c << bend180_cell
                        bend180.transform(
                            kdb.Trans((ang1 + 2) % 4, False, pt2.x, pt2.y)
                            * b180p2.trans.inverted()
                        )
                        place90(
                            c,
                            start_port.copy(),
                            bend180.ports[b180p2.name],
                            pts[j : i - 2],
                            straight_factory,
                            bend90_cell,
                            taper_cell,
                            port_type=port_type,
                            allow_small_routes=allow_small_routes,
                            allow_width_mismatch=allow_width_mismatch,
                        )
                        j = i - 1
                        start_port = bend180.ports[b180p1.name]

                    pt1 = pt2
                    pt2 = pt3
                    pt3 = pt4

        route = place90(
            c,
            start_port.copy(),
            end_port.copy(),
            pts,
            straight_factory,
            bend90_cell,
            taper_cell,
            min_straight_taper=min_straight_taper,
            port_type=port_type,
            allow_small_routes=allow_small_routes,
            allow_width_mismatch=allow_width_mismatch,
        )

    else:
        start_port = p1.copy()
        end_port = p2.copy()
        if not route_kwargs:
            pts = route_path_function(
                start_port,
                end_port,
                bend90_radius=b90r,
                start_straight=start_straight,
                end_straight=end_straight,
            )
        else:
            pts = route_path_function(
                start_port,
                end_port,
                bend90_radius=b90r,
                start_straight=start_straight,
                end_straight=end_straight,
                **route_kwargs,
            )

        route = place90(
            c,
            p1.copy(),
            p2.copy(),
            pts,
            straight_factory,
            bend90_cell,
            taper_cell,
            allow_small_routes=allow_small_routes,
            min_straight_taper=min_straight_taper,
            port_type=port_type,
            allow_width_mismatch=allow_width_mismatch,
        )
    return route


@config.logger.catch(reraise=True)
def route_bundle(
    c: KCell,
    start_ports: list[Port],
    end_ports: list[Port],
    separation: int,
    straight_factory: StraightFactory,
    bend90_cell: KCell,
    taper_cell: KCell | None = None,
    start_straights: int | list[int] = 0,
    end_straights: int | list[int] = 0,
    min_straight_taper: int = 0,
    place_port_type: str = "optical",
    place_allow_small_routes: bool = False,
    collision_check_layers: Sequence[int] | None = None,
    on_collision: Literal["error", "show_error"] | None = "show_error",
    bboxes: list[kdb.Box] = [],
    allow_width_mismatch: bool = config.allow_width_mismatch,
    allow_layer_mismatch: bool = config.allow_layer_mismatch,
    allow_type_mismatch: bool = config.allow_type_mismatch,
    route_width: int | list[int] | None = None,
    sort_ports: bool = False,
) -> list[OpticalManhattanRoute]:
    """Route a bundle from starting ports to end_ports.

    Args:
        c: Cell to place the route in.
        start_ports: List of start ports.
        end_ports: List of end ports.
        separation: Separation between the routes.
        straight_factory: Factory function for straight cells. in DBU.
        bend90_cell: 90° bend cell.
        taper_cell: Taper cell.
        start_straights: Minimal straight segment after `p1`.
        end_straights: Minimal straight segment before `p2`.
        min_straight_taper: Minimum straight [dbu] before attempting to place tapers.
        place_port_type: Port type to use for the bend90_cell.
        place_allow_small_routes: Don't throw an error if two corners cannot be placed.
        collision_check_layers: Layers to check for actual errors if manhattan routes
            detect potential collisions.
        on_collision: Define what to do on routing collision. Default behaviour is to
            open send the layout of c to klive and open an error lyrdb with the
            collisions. "error" will simply raise an error. None will ignore any error.

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
    """
    radius = max(
        abs(bend90_cell.ports[0].x - bend90_cell.ports[1].x),
        abs(bend90_cell.ports[0].y - bend90_cell.ports[1].y),
    )
    if not (len(start_ports) == len(end_ports) and start_ports):
        raise ValueError(
            "For bundle routing the input port list must have"
            " the same size as the end ports and be the same length."
        )

    if isinstance(start_straights, int):
        start_straights = [start_straights] * len(start_ports)
    if isinstance(end_straights, int):
        end_straights = [end_straights] * len(start_ports)

    if route_width:
        if isinstance(route_width, int):
            widths = [route_width] * len(start_ports)
        else:
            widths = route_width
    else:
        widths = [p.width for p in start_ports]

    routers = route_smart(
        start_ports=start_ports,
        end_ports=end_ports,
        bend90_radius=radius,
        separation=separation,
        start_straights=start_straights,
        end_straights=end_straights,
        bboxes=bboxes.copy(),
        widths=widths,
        sort_ports=sort_ports,
    )

    routes: list[OpticalManhattanRoute] = []
    if sort_ports:
        start_mapping = {sp.trans.disp.to_p(): sp for sp in start_ports}
        end_mapping = {ep.trans.disp.to_p(): ep for ep in end_ports}
        for router in routers:
            routes.append(
                place90(
                    c,
                    p1=start_mapping[router.start.pts[0]],
                    p2=end_mapping[router.start.pts[-1]],
                    pts=router.start.pts,
                    straight_factory=straight_factory,
                    bend90_cell=bend90_cell,
                    taper_cell=taper_cell,
                    min_straight_taper=min_straight_taper,
                    allow_small_routes=place_allow_small_routes,
                    port_type=place_port_type,
                    allow_width_mismatch=allow_width_mismatch,
                    route_width=router.width,
                )
            )
    else:
        for router, ps, pe in zip(routers, start_ports, end_ports):
            routes.append(
                place90(
                    c,
                    p1=ps,
                    p2=pe,
                    pts=router.start.pts,
                    straight_factory=straight_factory,
                    bend90_cell=bend90_cell,
                    taper_cell=taper_cell,
                    min_straight_taper=min_straight_taper,
                    allow_small_routes=place_allow_small_routes,
                    port_type=place_port_type,
                    allow_width_mismatch=allow_width_mismatch,
                    route_width=router.width,
                )
            )

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
            collision_check_layers = list(set(p.layer for p in start_ports))
        dbu = c.kcl.dbu
        db = rdb.ReportDatabase("Routing Errors")
        cat = db.create_category("Manhattan Routing Collisions")
        cell = db.create_cell(c.name)
        for name, edges in collision_edges.items():
            item = db.create_item(cell, cat)
            item.add_value(name)
            for edge in edges.each():
                item.add_value(edge.to_dtype(dbu))
        insts = [inst for route in routes for inst in route.instances]
        layer_cats: dict[int, rdb.RdbCategory] = {}

        def layer_cat(layer: int) -> rdb.RdbCategory:
            if layer not in layer_cats:
                if isinstance(layer, LayerEnum):
                    ln = layer.name
                else:
                    li = c.kcl.get_info(layer)
                    ln = str(li).replace("/", "_")
                layer_cats[layer] = db.category_by_path(ln) or db.create_category(ln)
            return layer_cats[layer]

        any_layer_collision = False

        for layer in collision_check_layers:
            error_region_instances = kdb.Region()
            inst_regions: dict[int, kdb.Region] = {}
            inst_region = kdb.Region()
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

                if not error_region_instances.is_empty():
                    any_layer_collision = True
                    sc = db.category_by_path(
                        layer_cat(layer).path() + ".RoutingErrors"
                    ) or db.create_category(layer_cat(layer), "InstanceshapeOverlap")
                    it = db.create_item(cell, sc)
                    it.add_value(
                        "Instance shapes overlapping with shapes of other instances"
                    )
                    for poly in error_region_instances.merge().each():
                        it.add_value(poly.to_dtype(c.kcl.dbu))

        if any_layer_collision:
            match on_collision:
                case "show_error":
                    c.show(lyrdb=db)
                    raise RuntimeError(f"Routing collision in {c.name}")
                case "error":
                    raise RuntimeError(f"Routing collision in {c.name}")

    return routes


def place90(
    c: KCell,
    p1: Port,
    p2: Port,
    pts: Sequence[kdb.Point],
    straight_factory: StraightFactory,
    bend90_cell: KCell,
    taper_cell: KCell | None = None,
    port_type: str = "optical",
    min_straight_taper: int = 0,
    allow_small_routes: bool = False,
    allow_width_mismatch: bool = config.allow_width_mismatch,
    allow_layer_mismatch: bool = config.allow_layer_mismatch,
    allow_type_mismatch: bool = config.allow_type_mismatch,
    route_width: int | None = None,
) -> OpticalManhattanRoute:
    """Place bends and straight waveguides based on a sequence of points.

    This version will not take any non-90° bends. If the taper is not `None`, tapers
    will be added to straights that fulfill the minimum length.

    This function will throw an error in case it cannot place bends due to too small
    routings, E.g. two corner are too close for two bends to be safely placed.


    Args:
        c: Cell in which the route should be placed.
        p1: Start port.
        p2: End port.
        pts: The points
        straight_factory: A function which takes two keyword arguments `width`
            and `length`. It returns a :py:class:~`KCell` with two named ports with
            port_type `port_type` and matching layer as the `bend90_cell` ports.
        bend90_cell: Bend to use in corners of the `pts`. Must have two named ports on
            `port_type`
        taper_cell: Optional taper cell to use if straights and bends should have a
            different width on the connection layer. Must have two named ports on
            `port_type` and share the port layer with `bend90_cell` and
            `straight_factory`.
        port_type: Filter the port type by this to e.g. ignore potential electrical
            ports.
        min_straight_taper: Do not put tapers on a straight if its length
            is below this minimum length.
        allow_small_routes: Don't throw an error if two corners cannot be safely placed
            due to small space and place them anyway.
        allow_width_mismatch: If True, the width of the ports is ignored
            (config default: False).
        allow_layer_mismatch: If True, the layer of the ports is ignored
            (config default: False).
        allow_type_mismatch: If True, the type of the ports is ignored
            (config default: False).
        route_width: Width of the route. If None, the width of the ports is used.
    """
    route_start_port = p1.copy()
    route_start_port.name = None
    route_start_port.trans.angle = (route_start_port.angle + 2) % 4
    route_end_port = p2.copy()
    route_end_port.name = None
    route_end_port.trans.angle = (route_end_port.angle + 2) % 4
    route = OpticalManhattanRoute(
        parent=c,
        backbone=list(pts).copy(),
        start_port=route_start_port,
        end_port=route_end_port,
        instances=[],
    )
    if not pts or len(pts) < 2:
        # Nothing to be placed
        return route

    w = route_width or p1.width
    old_pt = pts[0]
    old_bend_port = p1
    bend90_ports = [p for p in bend90_cell.ports if p.port_type == port_type]

    if len(bend90_ports) != 2:
        raise AttributeError(
            f"{bend90_cell.name} should have 2 ports but has {len(bend90_ports)} ports"
            f"with {port_type=}"
        )
    if abs((bend90_ports[0].trans.angle - bend90_ports[1].trans.angle) % 4) != 1:
        raise AttributeError(
            f"{bend90_cell.name} bend ports should be 90° apart from each other"
        )

    if (bend90_ports[1].trans.angle - bend90_ports[0].trans.angle) % 4 == 3:
        b90p1 = bend90_ports[1]
        b90p2 = bend90_ports[0]
    else:
        b90p1 = bend90_ports[0]
        b90p2 = bend90_ports[1]
    assert b90p1.name is not None, config.logger.error(
        "bend90_cell needs named ports, {}", b90p1
    )
    assert b90p2.name is not None, config.logger.error(
        "bend90_cell needs named ports, {}", b90p2
    )
    b90c = kdb.Trans(
        b90p1.trans.rot,
        b90p1.trans.is_mirror(),
        b90p1.trans.disp.x if b90p1.trans.angle % 2 else b90p2.trans.disp.x,
        b90p2.trans.disp.y if b90p1.trans.angle % 2 else b90p1.trans.disp.y,
    )
    b90r = max(
        (b90p1.trans.disp - b90c.disp).length(), (b90p2.trans.disp - b90c.disp).length()
    )
    if taper_cell is not None:
        taper_ports = [p for p in taper_cell.ports if p.port_type == "optical"]
        if (
            len(taper_ports) != 2
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
                "At least one optical ports of the taper must be the same width as"
                " the bend's ports"
            )

    if len(pts) == 2:
        length = int((pts[1] - pts[0]).length())
        route.length += int(length)
        if (
            taper_cell is None
            or length
            < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
            + min_straight_taper
        ):
            wg = c << straight_factory(width=w, length=int((pts[1] - pts[0]).length()))
            wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
            wg.connect(wg_p1, p1)
            route.instances.append(wg)
            route.start_port = wg_p1.copy()
            route.start_port.name = None
            route.length_straights += int(length)
        else:
            t1 = c << taper_cell
            t1.connect(taperp1.name, p1)
            route.instances.append(t1)
            route.start_port = t1.ports[taperp1.name].copy()
            route.start_port.name = None
            _l = int(length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2)
            if _l != 0:
                wg = c << straight_factory(
                    width=taperp2.width,
                    length=length
                    - int((taperp1.trans.disp - taperp2.trans.disp).length() * 2),
                )
                wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                wg.connect(wg_p1, t1, taperp2.name)
                route.instances.append(wg)
                t2 = c << taper_cell
                t2.connect(taperp2.name, wg_p2)
                route.length_straights += _l
            else:
                t2 = c << taper_cell
                t2.connect(taperp2.name, t1, taperp2.name)
            route.instances.append(t2)
            route.end_port = t2.ports[taperp1.name]
        return route
    for i in range(1, len(pts) - 1):
        pt = pts[i]
        new_pt = pts[i + 1]

        if (pt.distance(old_pt) < b90r) and not allow_small_routes:
            raise ValueError(
                f"distance between points {str(old_pt)} and {str(pt)} is too small to"
                f" safely place bends {pt.to_s()=}, {old_pt.to_s()=},"
                f" {pt.distance(old_pt)=} < {b90r=}"
            )
        elif (
            pt.distance(old_pt) < 2 * b90r
            and i not in [1, len(pts) - 1]
            and not allow_small_routes
        ):
            raise ValueError(
                f"distance between points {str(old_pt)} and {str(pt)} is too small to"
                f" safely place bends {str(pt)=}, {str(old_pt)=},"
                f" {pt.distance(old_pt)=} < {2 * b90r=}"
            )

        vec = pt - old_pt
        vec_n = new_pt - pt

        bend90 = c << bend90_cell
        route.n_bend90 += 1
        mirror = (vec_angle(vec_n) - vec_angle(vec)) % 4 != 3
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
        length = int(
            (bend90.ports[b90p1.name].trans.disp - old_bend_port.trans.disp).length()
        )
        route.length += int(length)
        if length > 0:
            if (
                taper_cell is None
                or length
                < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                + min_straight_taper
            ):
                wg = c << straight_factory(width=w, length=length)
                wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                wg.connect(
                    wg_p1,
                    bend90,
                    b90p1.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
                route.instances.append(wg)
                route.length_straights += int(length)
            else:
                t1 = c << taper_cell
                t1.connect(taperp1.name, bend90, b90p1.name)
                route.instances.append(t1)
                _l = int(
                    length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                )
                if length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2 != 0:
                    wg = c << straight_factory(
                        width=taperp2.width,
                        length=int(
                            length
                            - (taperp1.trans.disp - taperp2.trans.disp).length() * 2,
                        ),
                    )
                    wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                    wg.connect(wg_p1.name, t1, taperp2.name)
                    route.instances.append(wg)
                    t2 = c << taper_cell
                    t2.connect(taperp2.name, wg, wg_p2.name)
                    route.length_straights += _l
                else:
                    t2 = c << taper_cell
                    t2.connect(taperp2.name, t1, taperp2.name)
                route.instances.append(t2)
        route.instances.append(bend90)
        old_pt = pt
        old_bend_port = bend90.ports[b90p2.name]
    length = int((bend90.ports[b90p2.name].trans.disp - p2.trans.disp).length())
    route.length += int(length)
    if length > 0:
        if (
            taper_cell is None
            or length
            < (taperp1.trans.disp - taperp2.trans.disp).length() * 2
            + min_straight_taper
        ):
            wg = c << straight_factory(width=w, length=length)
            wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
            wg.connect(
                wg_p1.name,
                bend90,
                b90p2.name,
                allow_width_mismatch=allow_width_mismatch,
                allow_layer_mismatch=allow_layer_mismatch,
                allow_type_mismatch=allow_type_mismatch,
            )
            route.instances.append(wg)
            route.end_port = wg.ports[wg_p2.name].copy()
            route.end_port.name = None
            route.length_straights += int(length)
        else:
            t1 = c << taper_cell
            t1.connect(taperp1.name, bend90, b90p2.name)
            route.instances.append(t1)
            if length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2 != 0:
                _l = int(
                    length - (taperp1.trans.disp - taperp2.trans.disp).length() * 2
                )
                wg = c << straight_factory(
                    width=taperp2.width,
                    length=_l,
                )
                route.instances.append(wg)
                wg_p1, wg_p2 = (v for v in wg.ports if v.port_type == port_type)
                wg.connect(
                    wg_p1.name,
                    t1,
                    taperp2.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
                t2 = c << taper_cell
                t2.connect(
                    taperp2.name,
                    wg,
                    wg_p2.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
                route.length_straights += int(_l)
            else:
                t2 = c << taper_cell
                t2.connect(
                    taperp2.name,
                    t1,
                    taperp2.name,
                    allow_width_mismatch=allow_width_mismatch,
                    allow_layer_mismatch=allow_layer_mismatch,
                    allow_type_mismatch=allow_type_mismatch,
                )
            route.instances.append(t2)
            route.end_port = t2.ports[taperp1.name].copy()
            route.end_port.name = None
    else:
        route.end_port = old_bend_port.copy()
        route.end_port.name = None
    return route

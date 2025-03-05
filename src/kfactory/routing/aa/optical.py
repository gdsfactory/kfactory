"""Optical routing allows the creation of photonic (or any route using bends)."""

from collections.abc import Sequence
from typing import Any, Protocol

import numpy as np
from pydantic import BaseModel
from scipy.optimize import minimize_scalar

from ... import kdb
from ...conf import MIN_ALL_ANGLE_ROUTES_POINTS, MIN_WAYPOINTS_FOR_ROUTING
from ...instance import VInstance
from ...kcell import DKCell, KCell, VKCell
from ...port import DPort, Port, ProtoPort

__all__ = ["OpticalAllAngleRoute", "route"]


class OpticalAllAngleRoute(BaseModel, arbitrary_types_allowed=True):
    """Optical route containing a connection between two ports."""

    backbone: list[kdb.DPoint]
    start_port: Port
    end_port: Port
    instances: list[VInstance]
    length: float = 0
    length_straights: float = 0


def _angle(v: kdb.DVector) -> float:
    return float(np.rad2deg(np.arctan2(v.y, v.x)))


class VirtualStraightFactory(Protocol):
    def __call__(self, width: float, length: float) -> VKCell: ...


class VirtualBendFactory(Protocol):
    def __call__(self, width: float, angle: float) -> VKCell: ...


def route(
    c: VKCell | KCell | DKCell,
    width: float,
    backbone: Sequence[kdb.DPoint],
    straight_factory: VirtualStraightFactory,
    bend_factory: VirtualBendFactory,
    bend_ports: tuple[str, str] = ("o1", "o2"),
    straight_ports: tuple[str, str] = ("o1", "o2"),
    tolerance: float = 0.1,
    angle_tolerance: float = 0.0001,
) -> OpticalAllAngleRoute:
    """Places an all-angle route.

    Args:
        c: The virtual or real KCell to place the route in.
        width: width of the rotue (passed to straight_factory and bend_factory).
            The layer the route ports will be extracted from bend port layers.
        backbone: The points of the route.
        straight_factory: Function to create straights from length and width.
            [um]
        bend_factory: Function to  create bends from length and width. [um]
        bend_ports: Names of the ports of the bend to use for connecting
            straights and bends.
        straight_ports: Names of the ports of the straight to use for connecting
            straights and bends.
        tolerance: Allow for a small tolerance when placing bends and straights. If
            the distance is below this tolerance, the route will be placed.
        angle_tolerance: If a resulting bend from a point in the backbone would have an
            angle below this tolerance, the point will be skipped and a straight between
            the point before and the following will be created.
    """
    if len(backbone) < MIN_ALL_ANGLE_ROUTES_POINTS:
        raise ValueError("All angle routes with less than 3 points are not supported.")

    bends: dict[float, VKCell] = {90: bend_factory(width=width, angle=90)}
    layer = bends[90].ports[bend_ports[0]].layer

    _p0 = kdb.DPoint(0, 0)
    _p1 = kdb.DPoint(1, 0)

    start_v = backbone[1] - backbone[0]
    end_v = backbone[-1] - backbone[-2]
    start_angle = np.rad2deg(np.arctan2(start_v.y, start_v.x))
    end_angle = (np.rad2deg(np.arctan2(end_v.y, end_v.x)) + 180) % 360

    start_port = Port(
        name="o1",
        width=c.kcl.to_dbu(width),
        layer=layer,
        dcplx_trans=kdb.DCplxTrans(1, start_angle, False, backbone[0].to_v()),
        kcl=c.kcl,
    )
    end_port = Port(
        name="o1",
        width=c.kcl.to_dbu(width),
        layer=layer,
        dcplx_trans=kdb.DCplxTrans(1, end_angle, False, backbone[-1].to_v()),
        kcl=c.kcl,
    )

    old_pt = backbone[0]
    pt = backbone[1]
    start_offset = 0.0
    _port = start_port
    insts: list[VInstance] = []

    length = (pt - old_pt).abs()
    length_straights: float = 0

    for new_pt in backbone[2:]:
        # Calculate (4 quadrant) angle between the three points
        s_v = pt - old_pt
        e_v = new_pt - pt
        length += e_v.abs()
        s_a = _angle(s_v)
        e_a = _angle(e_v)
        _a = (e_a - s_a + 180) % 360 - 180

        if abs(_a) >= angle_tolerance:
            # create a virtual bend with the angle if non-existent
            if _a not in bends:
                bends[_a] = bend_factory(width=width, angle=abs(_a))
            bend = bends[_a]

            p1, p2 = (bend.ports[_p] for _p in bend_ports)

            # get the center of the bend
            # the center must be on the crossing point between the two

            # from this the effective radius can be calculated (the bend must be
            # symmetric so each lengths needs 1*eff_radius)
            effective_radius = _get_effective_radius(p1, p2, _p1=_p0, _p2=_p1)
            # if the resulting straight is < old_eff_radius + new_eff_radius
            # the route is invalid
            if (pt - old_pt).length() - effective_radius - start_offset < -(
                c.kcl.dbu * tolerance
            ):
                raise ValueError(
                    f"Not enough space to place bends at points {[old_pt, pt]}."
                    f"Needed space={start_offset + effective_radius}, available "
                    f"space={(pt - old_pt).length()}"
                )
        else:
            effective_radius = 0
            _a = 0

        # calculate and place the resulting straight if != 0
        _l = (pt - old_pt).length() - effective_radius - start_offset
        if _l > 0:
            s = c.create_vinst(straight_factory(width=width, length=_l))
            length_straights += _l
            s.connect(straight_ports[0], _port)
            _port = Port(base=s.ports[straight_ports[1]].base)
            insts.append(s)
        if _a != 0:
            # after the straight place the bend
            b = c.create_vinst(bend)
            if _a < 0:
                b.connect(bend_ports[1], _port)
                _port = Port(base=b.ports[bend_ports[0]].base)
            else:
                b.connect(bend_ports[0], _port)
                _port = Port(base=b.ports[bend_ports[1]].base)
            insts.append(b)
        start_offset = effective_radius
        old_pt = pt
        pt = new_pt
    # place last straight
    _l = (pt - old_pt).length() - effective_radius
    # if the resulting straight is < old_eff_radius + new_eff_radius
    # the route is invalid
    if _l < -(c.kcl.dbu * tolerance):
        raise ValueError(
            f"Not enough space to place bends at points {[old_pt, pt]}."
            f"Needed space={effective_radius}, available "
            f"space={(pt - old_pt).length()}"
        )
    if _l > 0:
        s = c.create_vinst(straight_factory(width=width, length=_l))
        length_straights += _l
        s.connect(straight_ports[0], _port)
        _port = Port(base=s.ports[straight_ports[1]].base)
        insts.append(s)

    return OpticalAllAngleRoute(
        backbone=list(backbone),
        start_port=start_port,
        end_port=end_port,
        instances=insts,
        length=length,
        length_straights=length_straights,
    )


def route_bundle(
    c: KCell | DKCell | VKCell,
    start_ports: Sequence[DPort | Port],
    end_ports: Sequence[DPort | Port],
    backbone: Sequence[kdb.DPoint],
    separation: float | list[float],
    straight_factory: VirtualStraightFactory,
    bend_factory: VirtualBendFactory,
    bend_ports: tuple[str, str] = ("o1", "o2"),
    straight_ports: tuple[str, str] = ("o1", "o2"),
) -> list[OpticalAllAngleRoute]:
    """Places all-angle routes.

    Args:
        c: The virtual or real KCell to place the route in.
        start_ports: Ports denoting the beginning of each route. Must be
            sorted in anti-clockwise orientation with regards to the desired
            bundle order.
        end_ports: Ports denoting the end of each route. Must be
            sorted in clockwise orientation with regards to the desired
            bundle order.
        backbone: The points of the route. The router will route to the first point
            and then create a bundle which follows this points as a backbone. Bends
            leading the first or following the last backbone point are guaranteed to be
            outside the backbone.
        separation: Minimal separation between each piece of the bundle.
            This is only guaranteed from the backbone start to backbone end.
        straight_factory: Function to create straights from length and width.
            [um]
        bend_factory: Function to  create bends from length and width. [um]
        bend_ports: Names of the ports of the bend to use for connecting
            straights and bends.
        straight_ports: Names of the ports of the straight to use for connecting
            straights and bends.
    """
    routes: list[OpticalAllAngleRoute] = []

    if backbone:
        if len(backbone) < MIN_WAYPOINTS_FOR_ROUTING:
            raise NotImplementedError(
                "A bundle with less than two points has no orientation. "
                "Cannot automatically determine orientation."
            )

        if isinstance(separation, int | float):
            separation = [separation] * len(start_ports)
        pts_list = backbone2bundle(
            backbone=backbone,
            port_widths=[p.dwidth for p in start_ports],
            spacings=separation,
        )

        for ps, pe, pts in zip(start_ports, end_ports, pts_list, strict=False):
            # use edges and transformation to get distances to calculate crossings
            # and types of crossings
            pts_ = pts
            vector_bundle_start = pts_[0] - pts_[1]
            vector_bundle_end = pts_[-1] - pts_[-2]
            trans_bundle_start = kdb.DCplxTrans(
                1,
                np.rad2deg(np.arctan2(vector_bundle_start.y, vector_bundle_start.x)),
                False,
                pts_[0].to_v(),
            )
            trans_bundle_end = kdb.DCplxTrans(
                1,
                np.rad2deg(np.arctan2(vector_bundle_end.y, vector_bundle_end.x)),
                False,
                pts_[-1].to_v(),
            )
            psb = ps.copy()
            psb.dcplx_trans = trans_bundle_start
            peb = pe.copy()
            peb.dcplx_trans = trans_bundle_end

            pts_ = _get_connection_between_ports(
                port_start=ps,
                port_end=psb,
                bend_factory=bend_factory,
                bend_ports=bend_ports,
                backbone=pts_,
            )

            pts_.reverse()
            pts_ = _get_connection_between_ports(
                port_start=pe,
                port_end=peb,
                bend_factory=bend_factory,
                backbone=pts_,
                bend_ports=bend_ports,
            )
            pts_.reverse()
            routes.append(
                route(
                    c,
                    ps.dwidth,
                    pts_,
                    straight_factory=straight_factory,
                    bend_factory=bend_factory,
                    bend_ports=bend_ports,
                    straight_ports=straight_ports,
                )
            )
    else:
        for ps, pe in zip(start_ports, end_ports, strict=False):
            pts_ = _get_connection_between_ports(
                port_start=ps,
                port_end=pe,
                bend_factory=bend_factory,
                bend_ports=bend_ports,
                backbone=[],
            )
            # the connection will not write the end point
            pts_.append(pe.dcplx_trans.disp.to_p())
            routes.append(
                route(
                    c,
                    ps.dwidth,
                    pts_,
                    straight_factory=straight_factory,
                    bend_factory=bend_factory,
                    bend_ports=bend_ports,
                    straight_ports=straight_ports,
                )
            )

    return routes


def _get_connection_between_ports(
    port_start: ProtoPort[Any],
    port_end: ProtoPort[Any],
    bend_factory: VirtualBendFactory,
    backbone: list[kdb.DPoint],
    bend_ports: tuple[str, str] = ("o1", "o2"),
) -> list[kdb.DPoint]:
    """Modify route backbone for proper connection to a port.

    This will connect the start_port to the end_port and in the process
    modify the backbone points to reflect this connection in the points. The resulting
    new connection can cause that the first point in the backbone must be moved. It is
    Guaranteed to be further away from the bundle though, it will not move into the
    bundle.

    Args:
        port_start: Start Port
        port_end: Target Port
        bend_factory: Needed to optimize the bends.
        backbone: The backbone to be modified.
        bend_ports: Names of the ports created by the bend_factory.
    """
    port_start_ = Port(base=port_start.base)
    port_end_ = Port(base=port_end.base)

    _p0 = kdb.DPoint(0, 0)
    _p1 = kdb.DPoint(1, 0)
    trans_start = port_start_.dcplx_trans
    trans_end = port_end_.dcplx_trans
    edge_start = kdb.DEdge(trans_start * _p0, trans_start * _p1)
    edge_end = kdb.DEdge(trans_end * _p0, trans_end * _p1)
    xing = edge_start.cut_point(edge_end)
    if xing is not None:
        # if the crossings point to each other use one bend, otherwise use two
        vector_xing = trans_start.inverted() * xing
        vector_xing_bundle_start = trans_end.inverted() * xing
        if vector_xing.x > 0 and vector_xing_bundle_start.x > 0:
            backbone[:0] = [trans_start.disp.to_p(), xing]
        else:
            v = trans_end.disp - trans_start.disp
            result = optimize_route(
                bend_factory=bend_factory,
                bend_ports=bend_ports,
                start_port=port_start_,
                end_port=port_end_,
                angle=np.arctan2(v.y, v.x),
                _p0=_p0,
                _p1=_p1,
            )
            if result is None:
                raise RuntimeError(
                    f"Cannot find an automatic route from {port_start_}"
                    f" to bundle port {port_end_}"
                )
            p_start_port, p_start_bundle = result
            backbone[:1] = [
                trans_start.disp.to_p(),
                p_start_port,
                p_start_bundle,
            ]
    else:
        v = trans_end.disp - trans_start.disp
        result = optimize_route(
            bend_factory=bend_factory,
            bend_ports=bend_ports,
            start_port=port_start_,
            end_port=port_end_,
            angle=np.arctan2(v.y, v.x),
            _p0=_p0,
            _p1=_p1,
        )
        if result is None:
            raise RuntimeError(
                f"Cannot find an automatic route from {port_start_}"
                f" to bundle port {port_end_}"
            )
        p_start_port, p_start_bundle = result
        backbone[:1] = [
            trans_start.disp.to_p(),
            p_start_port,
            p_start_bundle,
        ]

    return backbone


def _get_partial_route(
    angle: float,
    bend_factory: VirtualBendFactory,
    bend_ports: tuple[str, str],
    start_port: Port,
    end_port: Port,
    _p0: kdb.DPoint,
    _p1: kdb.DPoint,
) -> tuple[kdb.DPoint, kdb.DPoint, float]:
    bend_angle = (180 - angle + start_port.dcplx_trans.angle) % 180
    bend = bend_factory(width=start_port.width, angle=abs(bend_angle))
    radius = _get_effective_radius(
        bend.ports[bend_ports[0]], bend.ports[bend_ports[1]], _p0, _p1
    )
    if radius is None:
        return np.inf
    _e2 = kdb.DEdge(end_port.dcplx_trans.disp.to_p(), end_port.dcplx_trans * _p1)
    rp = start_port.dcplx_trans * kdb.DPoint(radius, 0)
    _e = kdb.DEdge(rp, kdb.DCplxTrans(1, angle, False, rp.to_v()) * _p1)
    xe = _e.cut_point(_e2)
    if xe is None:
        return rp, kdb.DPoint(), np.inf
    bend2 = bend_factory(
        width=start_port.width,
        angle=abs((-angle + end_port.dcplx_trans.angle + 180) % 360 - 180),
    )
    er2 = _get_effective_radius(
        bend2.ports[bend_ports[0]], bend2.ports[bend_ports[1]], _p0, _p1
    )
    r2 = (xe - end_port.dcplx_trans.disp.to_p()).abs() - er2
    if r2 < 0 or (end_port.dcplx_trans.inverted() * xe).x < 0:
        r2 = r2 / bend.kcl.dbu * 10
        return rp, xe, abs(r2 / bend.kcl.dbu * 10)
    return rp, xe, abs(r2)


def optimize_route(
    bend_factory: VirtualBendFactory,
    bend_ports: tuple[str, str],
    start_port: Port,
    end_port: Port,
    angle: float,
    angle_step: float = 5,
    stop_angle: tuple[float, float] | None = None,
    _p0: kdb.DPoint | None = None,
    _p1: kdb.DPoint | None = None,
    stop_min_dist: float = 0.005,
    min_angle_step: float = 0.001,
) -> tuple[kdb.DPoint, kdb.DPoint]:
    if _p0 is None:
        _p0 = kdb.DPoint(0, 0)
    if _p1 is None:
        _p1 = kdb.DPoint(1, 0)

    def _optimize_func(
        angle: float,
        bend_factory: VirtualBendFactory,
        bend_ports: tuple[str, str],
        start_port: Port,
        end_port: Port,
        _p0: kdb.DPoint,
        _p1: kdb.DPoint,
    ) -> float:
        return _get_partial_route(
            angle=angle,
            bend_factory=bend_factory,
            bend_ports=bend_ports,
            start_port=start_port,
            end_port=end_port,
            _p0=_p0,
            _p1=_p1,
        )[2]

    result = minimize_scalar(
        _optimize_func,
        args=(bend_factory, bend_ports, start_port, end_port, _p0, _p1),
        bounds=(-180, 180),
    )

    end_result = _get_partial_route2(
        angle=result.x,
        bend_factory=bend_factory,
        bend_ports=bend_ports,
        start_port=start_port,
        end_port=end_port,
        _p0=_p0,
        _p1=_p1,
    )
    return end_result[:2]


def _get_partial_route2(
    angle: float,
    bend_factory: VirtualBendFactory,
    bend_ports: tuple[str, str],
    start_port: Port,
    end_port: Port,
    _p0: kdb.DPoint,
    _p1: kdb.DPoint,
) -> tuple[kdb.DPoint, kdb.DPoint, float]:
    # we only care about the absolute angle as it needs to be between 0 and 180
    bend_angle = (180 - angle + start_port.dcplx_trans.angle) % 180
    bend = bend_factory(width=start_port.width, angle=abs(bend_angle))
    radius = _get_effective_radius(
        bend.ports[bend_ports[0]], bend.ports[bend_ports[1]], _p0, _p1
    )
    if radius is None:
        return np.inf
    _e2 = kdb.DEdge(end_port.dcplx_trans.disp.to_p(), end_port.dcplx_trans * _p1)
    rp = start_port.dcplx_trans * kdb.DPoint(radius, 0)
    _e = kdb.DEdge(rp, kdb.DCplxTrans(1, angle, False, rp.to_v()) * _p1)
    xe = _e.cut_point(_e2)
    if xe is None:
        return rp, kdb.DPoint(), np.inf
    bend2 = bend_factory(
        width=start_port.width,
        angle=abs((-angle + end_port.dcplx_trans.angle + 180) % 360 - 180),
    )
    er2 = _get_effective_radius(
        bend2.ports[bend_ports[0]], bend2.ports[bend_ports[1]], _p0, _p1
    )
    r2 = (xe - end_port.dcplx_trans.disp.to_p()).abs() - er2
    if r2 < 0 or (end_port.dcplx_trans.inverted() * xe).x < 0:
        r2 = r2 / bend.kcl.dbu * 10
        return rp, xe, abs(r2 / bend.kcl.dbu * 10)
    return rp, xe, abs(r2)


def _get_effective_radius(
    port1: ProtoPort[Any], port2: ProtoPort[Any], _p1: kdb.DPoint, _p2: kdb.DPoint
) -> float:
    e1 = kdb.DEdge(port1.dcplx_trans * _p1, port1.dcplx_trans * _p2)
    e2 = kdb.DEdge(port2.dcplx_trans * _p1, port2.dcplx_trans * _p2)
    xp = e1.cut_point(e2)

    if xp is None:
        return float("inf")
    return (xp - port1.dcplx_trans.disp.to_p()).abs()  # type: ignore[no-any-return]


def _get_effective_radius_debug(
    port1: Port, port2: Port, _p1: kdb.DPoint, _p2: kdb.DPoint
) -> float:
    e1 = kdb.DEdge(port1.dcplx_trans * _p1, port1.dcplx_trans * _p2)
    e2 = kdb.DEdge(port2.dcplx_trans * _p1, port2.dcplx_trans * _p2)
    xp = e1.cut_point(e2)

    if xp is None:
        return float("inf")
    return (xp - port1.dcplx_trans.disp.to_p()).abs()  # type: ignore[no-any-return]


def backbone2bundle(
    backbone: Sequence[kdb.DPoint],
    port_widths: list[float],
    spacings: list[float],
) -> list[list[kdb.DPoint]]:
    """Used to extract a bundle from a backbone."""
    pts: list[list[kdb.DPoint]] = []

    edges: list[kdb.DEdge] = []
    p1 = backbone[0]

    for p2 in backbone[1:]:
        edges.append(kdb.DEdge(p1, p2))
        p1 = p2

    width = sum(port_widths) + sum(spacings)

    x = -width // 2

    for pw, spacing in zip(port_widths, spacings, strict=False):
        x += pw // 2 + spacing // 2

        _e1 = edges[0].shifted(-x)
        _pts = [_e1.p1]

        for e in edges[1:]:
            _e2 = e.shifted(-x)
            _pts.append(_e2.cut_point(_e1))
            _e1 = _e2
        _pts.append(_e1.p2)

        x += spacing - spacing // 2 + pw - pw // 2
        pts.append(_pts)

    return pts

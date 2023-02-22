from typing import Optional

import numpy as np
from scipy.optimize import brentq  # type: ignore[import]
from scipy.special import fresnel  # type: ignore[import]

from .. import kdb
from ..kcell import KCell, LayerEnum, autocell
from ..utils import Enclosure
from ..utils.geo import extrude_path, extrude_path_dynamic

__all__ = [
    "euler_bend_points",
    "euler_sbend_points",
    "bend_euler",
    "bend_s_euler",
]


def euler_bend_points(
    angle_amount: float = 90, radius: float = 100, resolution: float = 150
) -> list[kdb.DPoint]:
    """Base euler bend, no transformation, emerging from the origin."""

    if angle_amount < 0:
        raise ValueError(f"angle_amount should be positive. Got {angle_amount}")
    # End angle
    eth = angle_amount * np.pi / 180

    # If bend is trivial, return a trivial shape
    if eth == 0:
        return [kdb.DPoint(0, 0)]

    # Curve min radius
    R = radius

    # Total displaced angle
    th = eth / 2

    # Total length of curve
    Ltot = 4 * R * th

    # Compute curve ##
    a = np.sqrt(R**2 * np.abs(th))
    sq2pi = np.sqrt(2 * np.pi)

    # Function for computing curve coords
    (fasin, facos) = fresnel(np.sqrt(2 / np.pi) * R * th / a)

    def _xy(s: float) -> kdb.DPoint:
        if th == 0:
            return kdb.DPoint(0, 0)
        elif s <= Ltot / 2:
            (fsin, fcos) = fresnel(s / (sq2pi * a))
            X = sq2pi * a * fcos
            Y = sq2pi * a * fsin
        else:
            (fsin, fcos) = fresnel((Ltot - s) / (sq2pi * a))
            X = (
                sq2pi
                * a
                * (
                    facos
                    + np.cos(2 * th) * (facos - fcos)
                    + np.sin(2 * th) * (fasin - fsin)
                )
            )
            Y = (
                sq2pi
                * a
                * (
                    fasin
                    - np.cos(2 * th) * (fasin - fsin)
                    + np.sin(2 * th) * (facos - fcos)
                )
            )
        return kdb.DPoint(X, Y)

    # Parametric step size
    step = Ltot / int(th * resolution)

    # Generate points
    points = []
    for i in range(int(round(Ltot / step)) + 1):
        points.append(_xy(i * step))

    return points


def euler_endpoint(
    start_point: tuple[float, float] = (0.0, 0.0),
    radius: float = 10.0,
    input_angle: float = 0.0,
    angle_amount: float = 90.0,
) -> tuple[float, float]:
    """Gives the end point of a simple Euler bend as a i3.Coord2"""

    th = abs(angle_amount) * np.pi / 180 / 2
    R = radius
    clockwise = angle_amount < 0

    (fsin, fcos) = fresnel(np.sqrt(2 * th / np.pi))

    a = 2 * np.sqrt(2 * np.pi * th) * (np.cos(th) * fcos + np.sin(th) * fsin)
    r = a * R
    X = r * np.cos(th)
    Y = r * np.sin(th)

    if clockwise:
        Y *= -1

    return X + start_point[0], Y + start_point[1]


def euler_sbend_points(
    offset: float = 5.0, radius: float = 10.0e-6, resolution: float = 150
) -> list[kdb.DPoint]:
    """An Euler s-bend with parallel input and output, separated by an offset"""

    # Function to find root of
    def froot(th: float) -> float:
        end_point = euler_endpoint((0.0, 0.0), radius, 0.0, th)
        return 2 * end_point[1] - abs(offset)

    # Get direction
    dir = +1 if offset >= 0 else -1
    # Check whether offset requires straight section
    a = 0.0
    b = 90.0
    fa = froot(a)
    fb = froot(b)

    if fa * fb < 0:
        # Offset can be produced just by bends alone
        angle = dir * brentq(froot, 0.0, 90.0)
        extra_y = 0.0
    else:
        # Offset is greater than max height of bends
        angle = dir * 90.0
        extra_y = -dir * fb

    spoints = []
    right_point = []
    points_left_half = euler_bend_points(abs(angle), radius, resolution)

    # Second bend
    for pts in points_left_half:
        r_pt_x = 2 * points_left_half[-1].x - pts.x
        r_pt_y = 2 * points_left_half[-1].y - pts.y + extra_y * dir
        pts.y = pts.y * dir
        r_pt_y = r_pt_y * dir
        spoints.append(pts)
        right_point.append(kdb.DPoint(r_pt_x, r_pt_y))
    spoints += right_point[::-1]

    return spoints


@autocell
def bend_euler(
    width: float,
    radius: float,
    layer: int | LayerEnum,
    enclosure: Optional[Enclosure] = None,
    theta: float = 90,
    resolution: float = 150,
) -> KCell:
    c = KCell()
    dbu = c.layout().dbu
    backbone = euler_bend_points(theta, radius=radius, resolution=resolution)

    extrude_path(
        target=c,
        layer=layer,
        path=backbone,
        width=width,
        enclosure=enclosure,
        start_angle=0,
        end_angle=theta,
    )

    if theta == 90:
        c.create_port(
            name="W0",
            layer=layer,
            width=int(width / c.klib.dbu),
            trans=kdb.Trans(2, False, backbone[0].to_itype(dbu).to_v()),
        )
        c.create_port(
            name="N0",
            layer=layer,
            width=int(width / c.klib.dbu),
            trans=kdb.Trans(1, False, backbone[-1].to_itype(dbu).to_v()),
        )
    elif theta == 180:
        c.create_port(
            name="W0",
            layer=layer,
            width=int(width / c.klib.dbu),
            trans=kdb.Trans(2, False, backbone[0].to_itype(dbu).to_v()),
        )
        c.create_port(
            name="W1",
            layer=layer,
            width=int(width / c.klib.dbu),
            trans=kdb.Trans(2, False, backbone[-1].to_itype(dbu).to_v()),
        )

    return c


@autocell
def bend_s_euler(
    offset: float,
    width: float,
    radius: float,
    layer: int,
    enclosure: Optional[Enclosure] = None,
    resolution: float = 150,
) -> KCell:
    c = KCell()
    dbu = c.layout().dbu
    backbone = euler_sbend_points(
        offset=offset,
        radius=radius,
        resolution=resolution,
    )
    extrude_path(
        target=c,
        layer=layer,
        path=backbone,
        width=width,
        enclosure=enclosure,
        start_angle=0,
        end_angle=0,
    )

    v = backbone[-1] - backbone[0]
    if v.x < 0:
        p1 = backbone[-1].to_itype(dbu)
        p2 = backbone[0].to_itype(dbu)
    else:
        p1 = backbone[0].to_itype(dbu)
        p2 = backbone[-1].to_itype(dbu)
    c.create_port(
        name="W0",
        trans=kdb.Trans(2, False, p1.to_v()),
        width=int(width / c.klib.dbu),
        port_type="optical",
        layer=layer,
    )
    c.create_port(
        name="E0",
        trans=kdb.Trans(0, False, p2.to_v()),
        width=int(width / c.klib.dbu),
        port_type="optical",
        layer=layer,
    )
    return c

"""Euler bends.

Euler bends are bends with a constantly changing radius
from zero to a maximum radius and back to 0 at the other
end.

There are two kinds of euler bends. One that snaps the ports and one that doesn't.
All the default bends use snapping. To use no snapping make an instance of
BendEulerCustom(KCell.kcl) and use that one.
"""

import numpy as np
from scipy.optimize import brentq  # type:ignore[import-untyped,unused-ignore]
from scipy.special import fresnel  # type:ignore[import-untyped,unused-ignore]

from .. import kdb
from ..conf import config
from ..enclosure import LayerEnclosure, extrude_path
from ..kcell import KCell, KCLayout, LayerEnum, cell, kcl

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
    """Gives the end point of a simple Euler bend as a i3.Coord2."""
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
    """An Euler s-bend with parallel input and output, separated by an offset."""

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


class BendEuler:
    kcl: KCLayout

    def __init__(self, kcl: KCLayout) -> None:
        """Create a euler_bend function on a custom KCLayout."""
        self.kcl = kcl

    @cell(snap_ports=False)
    def __call__(
        self,
        width: float,
        radius: float,
        layer: int | LayerEnum,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        resolution: float = 150,
    ) -> KCell:
        """Create a euler bend.

        Args:
            width: Width of the core. [um]
            radius: Radius off the backbone. [um]
            layer: Layer index / LayerEnum of the core.
            enclosure: Slab/exclude definition. [dbu]
            angle: Angle of the bend.
            resolution: Angle resolution for the backbone.
        """
        return self._kcell(
            width=width,
            radius=radius,
            layer=layer,
            enclosure=enclosure,
            angle=angle,
            resolution=resolution,
        )

    def _kcell(
        self,
        width: float,
        radius: float,
        layer: int | LayerEnum,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        resolution: float = 150,
    ) -> KCell:
        """Create a euler bend.

        Args:
            width: Width of the core. [um]
            radius: Radius off the backbone. [um]
            layer: Layer index / LayerEnum of the core.
            enclosure: Slab/exclude definition. [dbu]
            angle: Angle of the bend.
            resolution: Angle resolution for the backbone.
        """
        c = self.kcl.kcell()
        if angle < 0:
            config.logger.critical(
                f"Negative lengths are not allowed {angle} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            angle = -angle
        if width < 0:
            config.logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width
        dbu = c.layout().dbu
        backbone = euler_bend_points(angle, radius=radius, resolution=resolution)

        center_path = extrude_path(
            target=c,
            layer=layer,
            path=backbone,
            width=width,
            enclosure=enclosure,
            start_angle=0,
            end_angle=angle,
        )
        c.create_port(
            layer=layer,
            width=round(width / c.kcl.dbu),
            trans=kdb.Trans(2, False, backbone[0].to_itype(dbu).to_v()),
        )

        if abs(angle % 90) < 0.001:
            _ang = round(angle)
            c.create_port(
                trans=kdb.Trans(
                    _ang // 90, False, backbone[-1].to_itype(c.kcl.dbu).to_v()
                ),
                width=round(width / c.kcl.dbu),
                layer=layer,
            )
        else:
            c.create_port(
                dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
                dwidth=width,
                layer=layer,
            )

        c.boundary = center_path

        c.auto_rename_ports()
        return c


class BendSEuler:
    kcl: KCLayout

    def __init__(self, kcl: KCLayout) -> None:
        self.kcl = kcl

    @cell
    def __call__(
        self,
        offset: float,
        width: float,
        radius: float,
        layer: LayerEnum | int,
        enclosure: LayerEnclosure | None = None,
        resolution: float = 150,
    ) -> KCell:
        """Create a euler s-bend.

        Args:
            offset: Offset between left/right. [um]
            width: Width of the core. [um]
            radius: Radius off the backbone. [um]
            layer: Layer index / LayerEnum of the core.
            enclosure: Slab/exclude definition. [dbu]
            resolution: Angle resolution for the backbone.
        """
        return self._kcell(
            offset=offset,
            width=width,
            radius=radius,
            layer=layer,
            enclosure=enclosure,
            resolution=resolution,
        )

    def _kcell(
        self,
        offset: float,
        width: float,
        radius: float,
        layer: LayerEnum | int,
        enclosure: LayerEnclosure | None = None,
        resolution: float = 150,
    ) -> KCell:
        """Create a euler s-bend.

        Args:
            offset: Offset between left/right. [um]
            width: Width of the core. [um]
            radius: Radius off the backbone. [um]
            layer: Layer index / LayerEnum of the core.
            enclosure: Slab/exclude definition. [dbu]
            resolution: Angle resolution for the backbone.
        """
        c = self.kcl.kcell()
        if width < 0:
            config.logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width
        dbu = c.layout().dbu
        backbone = euler_sbend_points(
            offset=offset,
            radius=radius,
            resolution=resolution,
        )
        center_path = extrude_path(
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
            trans=kdb.Trans(2, False, p1.to_v()),
            width=int(width / c.kcl.dbu),
            port_type="optical",
            layer=layer,
        )
        c.create_port(
            trans=kdb.Trans(0, False, p2.to_v()),
            width=int(width / c.kcl.dbu),
            port_type="optical",
            layer=layer,
        )
        c.boundary = center_path

        c.auto_rename_ports()
        return c


bend_euler = BendEuler(kcl)
bend_s_euler = BendSEuler(kcl)

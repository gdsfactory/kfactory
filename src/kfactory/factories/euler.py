"""Euler bends.

Euler bends are bends with a constantly changing radius
from zero to a maximum radius and back to 0 at the other
end.

There are two kinds of euler bends. One that snaps the ports and one that doesn't.
All the default bends use snapping. To use no snapping make an instance of
BendEulerCustom(KCell.kcl) and use that one.
"""

from collections.abc import Callable
from typing import Any, Protocol

import numpy as np
from scipy.optimize import brentq  # type:ignore[import-untyped,unused-ignore]
from scipy.special import fresnel  # type:ignore[import-untyped,unused-ignore]

from .. import kdb
from ..conf import logger
from ..enclosure import LayerEnclosure, extrude_path
from ..kcell import KCell
from ..layout import KCLayout
from ..settings import Info
from ..typings import MetaData, deg, um

__all__ = [
    "bend_euler_factory",
    "bend_s_euler_factory",
    "euler_bend_points",
    "euler_sbend_points",
]


class BendEulerFactory(Protocol):
    def __call__(
        self,
        width: um,
        radius: um,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
        angle: deg = 90,
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
        ...


class BendSEulerFactory(Protocol):
    def __call__(
        self,
        offset: um,
        width: um,
        radius: um,
        layer: kdb.LayerInfo,
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
        ...


def euler_bend_points(
    angle_amount: deg = 90, radius: um = 100, resolution: float = 150
) -> list[kdb.DPoint]:
    """Base euler bend, no transformation, emerging from the origin."""
    if angle_amount < 0:
        raise ValueError(f"angle_amount should be positive. Got {angle_amount}")
    # End angle
    eth = angle_amount * np.pi / 180

    # If bend is trivial, return a trivial shape
    if eth == 0:
        return [kdb.DPoint(0, 0)]

    # Total displaced angle
    th = eth / 2

    # Total length of curve
    total_length = 4 * radius * th

    # Compute curve ##
    a = np.sqrt(radius**2 * np.abs(th))
    sq2pi = np.sqrt(2 * np.pi)

    # Function for computing curve coords
    (fasin, facos) = fresnel(np.sqrt(2 / np.pi) * radius * th / a)

    def _xy(s: float) -> kdb.DPoint:
        if th == 0:
            return kdb.DPoint(0, 0)
        if s <= total_length / 2:
            (fsin, fcos) = fresnel(s / (sq2pi * a))
            x = sq2pi * a * fcos
            y = sq2pi * a * fsin
        else:
            (fsin, fcos) = fresnel((total_length - s) / (sq2pi * a))
            x = (
                sq2pi
                * a
                * (
                    facos
                    + np.cos(2 * th) * (facos - fcos)
                    + np.sin(2 * th) * (fasin - fsin)
                )
            )
            y = (
                sq2pi
                * a
                * (
                    fasin
                    - np.cos(2 * th) * (fasin - fsin)
                    + np.sin(2 * th) * (facos - fcos)
                )
            )
        return kdb.DPoint(x, y)

    # Parametric step size
    step = total_length / max(int(th * resolution), 1)

    # Generate points
    return [_xy(i * step) for i in range(round(total_length / step) + 1)]


def euler_endpoint(
    start_point: tuple[float, float] = (0.0, 0.0),
    radius: um = 10.0,
    input_angle: deg = 0.0,
    angle_amount: deg = 90.0,
) -> tuple[float, float]:
    """Gives the end point of a simple Euler bend as a i3.Coord2."""
    th = abs(angle_amount) * np.pi / 180 / 2
    clockwise = angle_amount < 0

    (fsin, fcos) = fresnel(np.sqrt(2 * th / np.pi))

    a = 2 * np.sqrt(2 * np.pi * th) * (np.cos(th) * fcos + np.sin(th) * fsin)
    r = a * radius
    x = r * np.cos(th)
    y = r * np.sin(th)

    if clockwise:
        y *= -1

    return x + start_point[0], y + start_point[1]


def euler_sbend_points(
    offset: um = 5.0, radius: um = 10.0e-6, resolution: float = 150
) -> list[kdb.DPoint]:
    """An Euler s-bend with parallel input and output, separated by an offset."""

    # Function to find root of
    def froot(th: float) -> float:
        end_point = euler_endpoint((0.0, 0.0), radius, 0.0, th)
        return 2 * end_point[1] - abs(offset)

    # Get direction
    direction = 1 if offset >= 0 else -1
    # Check whether offset requires straight section
    a = 0.0
    b = 90.0
    fa = froot(a)
    fb = froot(b)

    if fa * fb < 0:
        # Offset can be produced just by bends alone
        angle = direction * brentq(froot, 0.0, 90.0)
        extra_y = 0.0
    else:
        # Offset is greater than max height of bends
        angle = direction * 90.0
        extra_y = -direction * fb

    spoints = []
    right_point = []
    points_left_half = euler_bend_points(abs(angle), radius, resolution)

    # Second bend
    for pts in points_left_half:
        r_pt_x = 2 * points_left_half[-1].x - pts.x
        r_pt_y = 2 * points_left_half[-1].y - pts.y + extra_y * direction
        pts.y = pts.y * direction
        r_pt_y = r_pt_y * direction
        spoints.append(pts)
        right_point.append(kdb.DPoint(r_pt_x, r_pt_y))
    spoints += right_point[::-1]

    return spoints


def bend_euler_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    basename: str | None = None,
    snap_ports: bool = False,
    **cell_kwargs: Any,
) -> BendEulerFactory:
    """Returns a function generating euler bends.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.kcell.KCell.info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting KCell's name. By default
            the KCell will be named 'straight_dbu[...]'.
        snap_ports: Whether to snap ports to grid. If snapping is turned of, ports
            ports are still snapped to grid if they are within 0.0001° of multiples
            of 90°.
        cell_kwargs: Additional arguments passed as `@kcl.cell(**cell_kwargs)`.
    """
    if callable(additional_info) and additional_info is not None:
        _additional_info_func: Callable[
            ...,
            dict[str, MetaData],
        ] = additional_info
        _additional_info: dict[str, MetaData] = {}
    else:

        def additional_info_func(
            **kwargs: Any,
        ) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}

    @kcl.cell(
        snap_ports=snap_ports,
        basename=basename,
        output_type=KCell,
        **cell_kwargs,
    )
    def bend_euler(
        width: um,
        radius: um,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
        angle: deg = 90,
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
        c = kcl.kcell()
        if angle < 0:
            logger.critical(
                f"Negative lengths are not allowed {angle} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            angle = -angle
        if width < 0:
            logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width
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
        li = c.kcl.layer(layer)
        c.create_port(
            layer=li,
            width=c.kcl.to_dbu(width),
            trans=kdb.Trans(2, False, c.kcl.to_dbu(backbone[0]).to_v()),
        )

        if abs(angle % 90) < 0.001:  # noqa: PLR2004
            _ang = round(angle)
            c.create_port(
                trans=kdb.Trans(_ang // 90, False, c.kcl.to_dbu(backbone[-1]).to_v()),
                width=round(width / c.kcl.dbu),
                layer=li,
            )
        else:
            c.create_port(
                dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
                width=c.kcl.to_dbu(width),
                layer=li,
            )
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                width=width,
                radius=radius,
                layer=li,
                enclosure=enclosure,
                angle=angle,
                resolution=resolution,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)
        c.boundary = center_path

        c.auto_rename_ports()
        return c

    return bend_euler


def bend_s_euler_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    basename: str | None = None,
    **cell_kwargs: Any,
) -> BendSEulerFactory:
    """Returns a function generating euler s-bends.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.kcell.KCell.info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting KCell's name. By default
            the KCell will be named 'straight_dbu[...]'.
        cell_kwargs: Additional arguments passed as `@kcl.cell(**cell_kwargs)`.
    """
    if callable(additional_info):
        _additional_info_func: Callable[
            ...,
            dict[str, MetaData],
        ] = additional_info
        _additional_info: dict[str, MetaData] = {}
    else:

        def additional_info_func(
            **kwargs: Any,
        ) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}

    @kcl.cell(basename=basename, output_type=KCell, **cell_kwargs)
    def bend_s_euler(
        offset: um,
        width: um,
        radius: um,
        layer: kdb.LayerInfo,
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
        c = kcl.kcell()
        if width < 0:
            logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width
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
            p1 = c.kcl.to_dbu(backbone[-1])
            p2 = c.kcl.to_dbu(backbone[0])
        else:
            p1 = c.kcl.to_dbu(backbone[0])
            p2 = c.kcl.to_dbu(backbone[-1])
        li = c.kcl.layer(layer)
        c.create_port(
            trans=kdb.Trans(2, False, p1.to_v()),
            width=c.kcl.to_dbu(width),
            port_type="optical",
            layer=li,
        )
        c.create_port(
            trans=kdb.Trans(0, False, p2.to_v()),
            width=c.kcl.to_dbu(width),
            port_type="optical",
            layer=li,
        )
        c.boundary = center_path
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                offset=offset,
                width=width,
                radius=radius,
                layer=layer,
                enclosure=enclosure,
                resolution=resolution,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)

        c.auto_rename_ports()
        return c

    return bend_s_euler

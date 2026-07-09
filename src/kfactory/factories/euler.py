"""Euler bends.

Euler bends are bends with a constantly changing radius
from zero to a maximum radius and back to 0 at the other
end.

There are two kinds of euler bends. One that snaps the ports and one that doesn't.
All the default bends use snapping. To use no snapping make an instance of
BendEulerCustom(KCell.kcl) and use that one.
"""

from collections.abc import Callable
from typing import Any, Protocol, Unpack, cast, overload

import numpy as np
from scipy.optimize import brentq
from scipy.special import fresnel

from .. import kdb
from ..conf import logger
from ..cross_section import (
    AnyCrossSectionInput,
    CrossSectionSpecDict,
    DCrossSectionSpecDict,
)
from ..enclosure import LayerEnclosure, extrude_path_cross_section
from ..kcell import KCell
from ..layout import CellKWargs, KCLayout
from ..settings import Info
from ..typings import KC, KC_co, MetaData, deg, um
from .utils import (
    _is_additional_info_func,
    boundary_from_shapes,
    cross_section_from_width,
)

__all__ = [
    "bend_euler_factory",
    "bend_s_euler_factory",
    "euler_bend_points",
    "euler_sbend_points",
]


class BendEulerFactory(Protocol[KC_co]):
    def __call__(
        self,
        *,
        radius: um,
        angle: deg = 90,
        resolution: float = 150,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC_co:
        """Create a euler bend.

        Either pass a ``cross_section`` or the legacy ``width``/``layer``/``enclosure``.

        Args:
            radius: Radius off the backbone. [um]
            angle: Angle of the bend.
            resolution: Angle resolution for the backbone.
            cross_section: Cross section of the bend.
            width: Width of the core. [um] (legacy; requires ``layer``)
            layer: Main layer of the bend. (legacy)
            enclosure: Slab/exclude definition. (legacy)
        """
        ...


class BendSEulerFactory(Protocol[KC_co]):
    def __call__(
        self,
        *,
        offset: um,
        radius: um,
        resolution: float = 150,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC_co:
        """Create a euler s-bend.

        Either pass a ``cross_section`` or the legacy ``width``/``layer``/``enclosure``.

        Args:
            offset: Offset between left/right. [um]
            radius: Radius off the backbone. [um]
            resolution: Angle resolution for the backbone.
            cross_section: Cross section of the bend.
            width: Width of the core. [um] (legacy; requires ``layer``)
            layer: Main layer of the bend. (legacy)
            enclosure: Slab/exclude definition. (legacy)
        """
        ...


def _euler_bend_xy(
    angle_amount: deg = 90, radius: um = 100, resolution: float = 150
) -> tuple[np.ndarray, np.ndarray]:
    if angle_amount < 0:
        raise ValueError(f"angle_amount should be positive. Got {angle_amount}")

    eth = angle_amount * np.pi / 180
    if eth == 0:
        return np.array([0.0]), np.array([0.0])

    th = eth / 2
    total_length = 4 * radius * th
    a = np.sqrt(radius**2 * np.abs(th))
    sq2pi = np.sqrt(2 * np.pi)
    fasin, facos = fresnel(np.sqrt(2 / np.pi) * radius * th / a)
    step = total_length / max(int(th * resolution), 1)
    s_vals = np.linspace(0.0, total_length, round(total_length / step) + 1)
    left_mask = s_vals <= total_length / 2
    fresnel_arg = np.where(left_mask, s_vals, total_length - s_vals) / (sq2pi * a)
    fsin, fcos = fresnel(fresnel_arg)

    x = np.where(
        left_mask,
        sq2pi * a * fcos,
        sq2pi
        * a
        * (facos + np.cos(2 * th) * (facos - fcos) + np.sin(2 * th) * (fasin - fsin)),
    )
    y = np.where(
        left_mask,
        sq2pi * a * fsin,
        sq2pi
        * a
        * (fasin - np.cos(2 * th) * (fasin - fsin) + np.sin(2 * th) * (facos - fcos)),
    )
    return x, y


def euler_bend_points(
    angle_amount: deg = 90, radius: um = 100, resolution: float = 150
) -> list[kdb.DPoint]:
    """Base euler bend, no transformation, emerging from the origin."""
    x_vals, y_vals = _euler_bend_xy(
        angle_amount=angle_amount, radius=radius, resolution=resolution
    )
    return [
        kdb.DPoint(x, y)
        for x, y in zip(x_vals.tolist(), y_vals.tolist(), strict=False)
    ]


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

    left_x, orig_y = _euler_bend_xy(abs(angle), radius, resolution)
    left_y = orig_y * direction
    right_x = 2 * left_x[-1] - left_x
    right_y = (2 * orig_y[-1] - orig_y + extra_y * direction) * direction

    left_points = [
        kdb.DPoint(x, y) for x, y in zip(left_x.tolist(), left_y.tolist(), strict=False)
    ]
    right_points = [
        kdb.DPoint(x, y)
        for x, y in zip(right_x.tolist(), right_y.tolist(), strict=False)
    ]
    return left_points + right_points[::-1]


@overload
def bend_euler_factory(
    kcl: KCLayout,
    *,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BendEulerFactory[KCell]: ...
@overload
def bend_euler_factory(
    kcl: KCLayout,
    *,
    output_type: type[KC],
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BendEulerFactory[KC]: ...
def bend_euler_factory(
    kcl: KCLayout,
    *,
    output_type: type[KC] | None = None,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BendEulerFactory[KC]:
    """Returns a function generating euler bends.

    The returned function is the generic interface (``cross_section`` or the legacy
    ``width``/``layer``/``enclosure``). Will snap ports by default.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.settings.Info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the bend
            functions' parameters as kwargs and returns a dict with the mapping.
        cell_kwargs: Additional arguments passed as `@kcl.cell(**cell_kwargs)`.
    """
    _additional_info: dict[str, MetaData] = {}
    if _is_additional_info_func(additional_info):
        _additional_info_func: Callable[
            ...,
            dict[str, MetaData],
        ] = additional_info
    else:

        def additional_info_func(
            **kwargs: Any,
        ) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}  # ty:ignore[invalid-assignment]
    if cell_kwargs.get("snap_ports") is None:
        cell_kwargs["snap_ports"] = False
    cell_kwargs.setdefault("basename", "bend_euler")
    basename = cell_kwargs["basename"]

    if output_type is not None:
        cell = kcl.cell(output_type=output_type, **cell_kwargs)
    else:
        cell = kcl.cell(output_type=cast("type[KC]", KCell), **cell_kwargs)

    @cell
    def _bend_euler(
        cross_section: str | AnyCrossSectionInput,
        radius: um,
        angle: deg = 90,
        resolution: float = 150,
    ) -> KCell:
        """Euler bend [um] from a cross section."""
        c = kcl.kcell()
        if angle < 0:
            logger.critical(
                f"Negative lengths are not allowed {angle} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            angle = -angle

        xs = kcl.get_base_cross_section(cross_section)
        backbone = euler_bend_points(angle, radius=radius, resolution=resolution)

        extrude_path_cross_section(c, backbone, xs, start_angle=0, end_angle=angle)

        c.create_port(
            name="o1",
            cross_section=xs,
            trans=kdb.Trans(2, False, c.kcl.to_dbu(backbone[0]).to_v()),
            port_type=port_type,
        )

        if abs(angle % 90) < 0.001:
            _ang = round(angle)
            c.create_port(
                name="o2",
                trans=kdb.Trans(_ang // 90, False, c.kcl.to_dbu(backbone[-1]).to_v()),
                cross_section=xs,
                port_type=port_type,
            )
        else:
            c.create_port(
                name="o2",
                dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
                cross_section=xs,
                port_type=port_type,
            )
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                cross_section=xs,
                radius=radius,
                angle=angle,
                resolution=resolution,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)
        boundary = boundary_from_shapes(c)
        if boundary is not None:
            c.boundary = boundary

        c.auto_rename_ports()
        return c

    @kcl.generic_factory(name=basename)
    def bend_euler(
        *,
        radius: um,
        angle: deg = 90,
        resolution: float = 150,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC:
        if cross_section is None:
            if width is None or layer is None:
                raise ValueError(
                    "Provide a cross_section, or width and layer (legacy call)."
                )
            xs = cross_section_from_width(kcl, kcl.to_dbu(width), layer, enclosure)
        else:
            xs = kcl.get_icross_section(cross_section)
        return _bend_euler(
            cross_section=xs, radius=radius, angle=angle, resolution=resolution
        )

    return bend_euler


@overload
def bend_s_euler_factory(
    kcl: KCLayout,
    *,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BendSEulerFactory[KCell]: ...
@overload
def bend_s_euler_factory(
    kcl: KCLayout,
    *,
    output_type: type[KC],
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BendSEulerFactory[KC]: ...


def bend_s_euler_factory(
    kcl: KCLayout,
    output_type: type[KC] | None = None,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BendSEulerFactory[KC]:
    """Returns a function generating euler s-bends (generic interface).

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.settings.Info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the bend
            functions' parameters as kwargs and returns a dict with the mapping.
        cell_kwargs: Additional arguments passed as `@kcl.cell(**cell_kwargs)`.
    """
    _additional_info: dict[str, MetaData] = {}
    if _is_additional_info_func(additional_info):
        _additional_info_func: Callable[
            ...,
            dict[str, MetaData],
        ] = additional_info
    else:

        def additional_info_func(
            **kwargs: Any,
        ) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}  # ty:ignore[invalid-assignment]
    cell_kwargs.setdefault("basename", "bend_s_euler")
    basename = cell_kwargs["basename"]
    if output_type is not None:
        cell = kcl.cell(output_type=output_type, **cell_kwargs)
    else:
        cell = kcl.cell(output_type=cast("type[KC]", KCell), **cell_kwargs)

    @cell
    def _bend_s_euler(
        cross_section: str | AnyCrossSectionInput,
        offset: um,
        radius: um,
        resolution: float = 150,
    ) -> KCell:
        """Euler s-bend [um] from a cross section."""
        c = kcl.kcell()
        xs = kcl.get_base_cross_section(cross_section)
        backbone = euler_sbend_points(
            offset=offset,
            radius=radius,
            resolution=resolution,
        )
        extrude_path_cross_section(c, backbone, xs, start_angle=0, end_angle=0)

        v = backbone[-1] - backbone[0]
        if v.x < 0:
            p1 = c.kcl.to_dbu(backbone[-1])
            p2 = c.kcl.to_dbu(backbone[0])
        else:
            p1 = c.kcl.to_dbu(backbone[0])
            p2 = c.kcl.to_dbu(backbone[-1])
        c.create_port(
            name="o1",
            trans=kdb.Trans(2, False, p1.to_v()),
            cross_section=xs,
            port_type=port_type,
        )
        c.create_port(
            name="o2",
            trans=kdb.Trans(0, False, p2.to_v()),
            cross_section=xs,
            port_type=port_type,
        )
        boundary = boundary_from_shapes(c)
        if boundary is not None:
            c.boundary = boundary
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                cross_section=xs,
                offset=offset,
                radius=radius,
                resolution=resolution,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)

        c.auto_rename_ports()
        return c

    @kcl.generic_factory(name=basename)
    def bend_s_euler(
        *,
        offset: um,
        radius: um,
        resolution: float = 150,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC:
        if cross_section is None:
            if width is None or layer is None:
                raise ValueError(
                    "Provide a cross_section, or width and layer (legacy call)."
                )
            xs = cross_section_from_width(kcl, kcl.to_dbu(width), layer, enclosure)
        else:
            xs = kcl.get_icross_section(cross_section)
        return _bend_s_euler(
            cross_section=xs, offset=offset, radius=radius, resolution=resolution
        )

    return bend_s_euler

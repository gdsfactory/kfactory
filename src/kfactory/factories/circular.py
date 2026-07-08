"""Circular bends.

A circular bend has a constant radius.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, Unpack, cast, overload

import numpy as np

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

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..kcell import KCell

__all__ = ["bend_circular_factory"]


class BendCircularFactory(Protocol[KC_co]):
    def __call__(
        self,
        *,
        radius: um,
        angle: deg = 90,
        angle_step: deg = 1,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC_co:
        """Circular radius bend [um].

        Either pass a ``cross_section`` (name, spec, or instance) or the legacy
        ``width``/``layer``/``enclosure`` which is normalized into a cross section.

        Args:
            radius: Radius of the backbone. [um]
            angle: Angle amount of the bend.
            angle_step: Angle amount per backbone point of the bend.
            cross_section: Cross section of the bend.
            width: Width of the core. [um] (legacy; requires ``layer``)
            layer: Main layer of the bend. (legacy)
            enclosure: Optional enclosure. (legacy)
        """
        ...


def _circular_backbone_points(
    *, radius: um, angle: deg, angle_step: deg
) -> list[kdb.DPoint]:
    points = max(int(angle // angle_step + 0.5), 1)
    angles = np.linspace(0, angle, points, endpoint=True)
    radians = np.deg2rad(angles)
    x = np.sin(radians) * radius
    y = (-np.cos(radians) + 1) * radius
    return [kdb.DPoint(float(_x), float(_y)) for _x, _y in zip(x, y, strict=False)]


@overload
def bend_circular_factory(
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
) -> BendCircularFactory[KCell]: ...
@overload
def bend_circular_factory(
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
) -> BendCircularFactory[KC]: ...


def bend_circular_factory(
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
) -> BendCircularFactory[KC]:
    """Returns a function generating circular bends.

    The returned function is the generic interface: it accepts either a
    ``cross_section`` or the legacy ``width``/``layer``/``enclosure`` (normalized into a
    symmetric cross section). Will snap ports by default.

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
    cell_kwargs.setdefault("basename", "bend_circular")
    basename = cell_kwargs["basename"]

    if output_type is not None:
        cell = kcl.cell(output_type=output_type, **cell_kwargs)
    else:
        cell = kcl.cell(output_type=cast("type[KC]", KCell), **cell_kwargs)

    @cell
    def _bend_circular(
        cross_section: str | AnyCrossSectionInput,
        radius: um,
        angle: deg = 90,
        angle_step: deg = 1,
    ) -> KCell:
        """Circular radius bend [um] from a cross section."""
        c = kcl.kcell()
        r = radius

        if angle < 0:
            logger.critical(
                f"Negative angles are not allowed {angle} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            angle = -angle

        xs = kcl.get_base_cross_section(cross_section)
        backbone = _circular_backbone_points(
            radius=r, angle=angle, angle_step=angle_step
        )

        extrude_path_cross_section(c, backbone, xs, start_angle=0, end_angle=angle)

        c.create_port(
            name="o1",
            trans=kdb.Trans(2, False, 0, 0),
            cross_section=xs,
            port_type=port_type,
        )
        c.create_port(
            name="o2",
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            cross_section=xs,
            port_type=port_type,
        )
        c.auto_rename_ports()
        boundary = boundary_from_shapes(c)
        if boundary is not None:
            c.boundary = boundary
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                cross_section=xs,
                radius=radius,
                angle=angle,
                angle_step=angle_step,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)
        return c

    @kcl.generic_factory(name=basename)
    def bend_circular(
        *,
        radius: um,
        angle: deg = 90,
        angle_step: deg = 1,
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
        return _bend_circular(
            cross_section=xs, radius=radius, angle=angle, angle_step=angle_step
        )

    return bend_circular

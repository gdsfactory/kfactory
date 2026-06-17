"""Virtual circular cell factories."""

from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

from ... import kdb
from ...conf import logger
from ...cross_section import (
    AnyCrossSectionInput,
    CrossSectionSpecDict,
    DCrossSectionSpecDict,
)
from ...enclosure import LayerEnclosure
from ...kcell import VKCell
from ...layout import KCLayout
from ...settings import Info
from ...typings import MetaData, deg, um
from ..utils import (
    _is_additional_info_func,
    cross_section_from_width,
    extrude_backbone_cross_section,
)

__all__ = ["virtual_bend_circular_factory"]


class BendCircularVKCell(Protocol):
    """Factory for virtual circular bend."""

    __name__: str

    def __call__(
        self,
        *,
        radius: um,
        angle: deg = 90,
        angle_step: float = 1,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> VKCell:
        """Create a virtual circular bend.

        Either pass a ``cross_section`` or the legacy ``width``/``layer``/``enclosure``.

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


def virtual_bend_circular_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    basename: str | None = None,
    **cell_kwargs: Any,
) -> BendCircularVKCell:
    """Returns a function generating virtual circular bends.

    The returned function is the generic interface (``cross_section`` or the legacy
    ``width``/``layer``/``enclosure``).

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`VKCell.info`][kfactory.settings.Info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the bend
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting VKCell's name. By default
            the VKCell will be named 'virtual_bend_circular[...]'.
        cell_kwargs: Additional arguments passed as `@kcl.vcell(**cell_kwargs)`.
    """
    _additional_info: dict[str, MetaData]
    if _is_additional_info_func(additional_info):
        _additional_info_func: Callable[
            ...,
            dict[str, MetaData],
        ] = additional_info
        _additional_info = {}
    else:

        def additional_info_func(
            **kwargs: Any,
        ) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}  # ty:ignore[invalid-assignment]

    @kcl.vcell(
        basename=basename or "virtual_bend_circular", output_type=VKCell, **cell_kwargs
    )
    def virtual_bend_circular(
        cross_section: str | AnyCrossSectionInput,
        radius: um,
        angle: deg = 90,
        angle_step: float = 1,
    ) -> VKCell:
        """Virtual circular bend defined by a cross section (um)."""
        c = kcl.vkcell()
        if angle < 0:
            logger.critical(
                f"Negative lengths are not allowed {angle} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            angle = -angle

        xs = kcl.get_base_cross_section(cross_section)
        backbone = [
            kdb.DPoint(x, y)
            for x, y in [
                [
                    np.sin(_angle / 180 * np.pi) * radius,
                    (-np.cos(_angle / 180 * np.pi) + 1) * radius,
                ]
                for _angle in np.linspace(
                    0, angle, int(angle // angle_step + 0.5), endpoint=True
                )
            ]
        ]

        extrude_backbone_cross_section(
            c,
            backbone=backbone,
            cross_section=xs,
            start_angle=0,
            end_angle=angle,
        )
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

        c.create_port(
            name="o1",
            cross_section=xs,
            dcplx_trans=kdb.DCplxTrans(1, 180, False, backbone[0].to_v()),
        )
        c.create_port(
            name="o2",
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            cross_section=xs,
        )
        return c

    @kcl.generic_factory(name=basename or "virtual_bend_circular")
    def virtual_bend_circular_generic(
        *,
        radius: um,
        angle: deg = 90,
        angle_step: float = 1,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> VKCell:
        if cross_section is None:
            if width is None or layer is None:
                raise ValueError(
                    "Provide a cross_section, or width and layer (legacy call)."
                )
            if width < 0:
                logger.critical(
                    f"Negative widths are not allowed {width}. Forcing positive width."
                )
                width = -width
            xs = cross_section_from_width(kcl, kcl.to_dbu(width), layer, enclosure)
        else:
            xs = kcl.get_icross_section(cross_section)
        return virtual_bend_circular(
            cross_section=xs, radius=radius, angle=angle, angle_step=angle_step
        )

    return virtual_bend_circular_generic

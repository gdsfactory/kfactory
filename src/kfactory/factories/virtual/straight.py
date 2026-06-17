"""Straight virtual straight waveguide cell factories."""

from collections.abc import Callable
from typing import Any, Protocol

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
from ...typings import MetaData, um
from ..utils import (
    _is_additional_info_func,
    cross_section_from_width,
    extrude_backbone_cross_section,
)

__all__ = ["virtual_straight_factory"]


class StraightVKCell(Protocol):
    __name__: str

    def __call__(
        self,
        *,
        length: um,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> VKCell:
        """Virtual straight waveguide defined in um.

            ┌──────────────────────────────┐
            │         Slab/Exclude         │
            ├──────────────────────────────┤
            │                              │
            │             Core             │
            │                              │
            ├──────────────────────────────┤
            │         Slab/Exclude         │
            └──────────────────────────────┘

        Either pass a ``cross_section`` or the legacy ``width``/``layer``/``enclosure``.

        Args:
            length: Waveguide length. [um]
            cross_section: Cross section of the waveguide.
            width: Waveguide width. [um] (legacy; requires ``layer``)
            layer: Main layer of the waveguide. (legacy)
            enclosure: Definition of slab/excludes. (legacy)
        """
        ...


def virtual_straight_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    basename: str | None = None,
    **cell_kwargs: Any,
) -> StraightVKCell:
    """Returns a function generating virtual straight waveguides.

    The returned function is the generic interface: it accepts either a
    ``cross_section`` or the legacy ``width``/``layer``/``enclosure`` (all um),
    normalized into a symmetric cross section.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`VKCell.info`][kfactory.settings.Info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting VKCell's name. By default
            the VKCell will be named 'virtual_straight[...]'.
        cell_kwargs: Additional arguments passed as `@kcl.vcell(**cell_kwargs)`.
    """
    if _is_additional_info_func(additional_info):
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

    @kcl.vcell(
        basename=basename or "virtual_straight", output_type=VKCell, **cell_kwargs
    )
    def virtual_straight(
        cross_section: str | AnyCrossSectionInput,
        length: um,
    ) -> VKCell:
        """Virtual waveguide defined by a cross section (um)."""
        c = kcl.vkcell()
        if length < 0:
            logger.critical(
                f"Negative lengths are not allowed {length} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length = -length

        xs = kcl.get_base_cross_section(cross_section)

        extrude_backbone_cross_section(
            c,
            backbone=[kdb.DPoint(0, 0), kdb.DPoint(length, 0)],
            cross_section=xs,
            start_angle=0,
            end_angle=0,
        )

        _info: dict[str, MetaData] = {}
        _info.update(_additional_info_func(cross_section=xs, length=length))
        _info.update(_additional_info)  # ty:ignore[no-matching-overload]
        c.info = Info(**_info)

        c.create_port(
            name="o1",
            dcplx_trans=kdb.DCplxTrans(1, 180, False, 0, 0),
            cross_section=xs,
        )
        c.create_port(
            name="o2",
            dcplx_trans=kdb.DCplxTrans(1, 0, False, length, 0),
            cross_section=xs,
        )
        return c

    @kcl.generic_factory(name=basename or "virtual_straight")
    def straight(
        *,
        length: um,
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
        return virtual_straight(cross_section=xs, length=length)

    return straight

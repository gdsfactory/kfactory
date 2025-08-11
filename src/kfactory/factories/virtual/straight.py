"""Straight virtual straight waveguide cell factories."""

from collections.abc import Callable
from typing import Any, Protocol

from ... import kdb
from ...conf import logger
from ...enclosure import LayerEnclosure
from ...kcell import VKCell
from ...layout import KCLayout, vcell
from ...settings import Info
from ...typings import MetaData
from .utils import extrude_backbone

__all__ = ["virtual_straight_factory"]


class StraightVKCell(Protocol):
    def __call__(
        self,
        width: float,
        length: float,
        layer: kdb.LayerInfo,
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
        Args:
            width: Waveguide width. [um]
            length: Waveguide length. [um]
            layer: Main layer of the waveguide.
            enclosure: Definition of slab/excludes. [dbu]
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

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`VKCell.info`][kfactory.kcell.VKCell.info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting VKCell's name. By default
            the VKCell will be named 'virtual_bend_euler[...]'.
        cell_kwargs: Additional arguments passed as `@kcl.vcell(**cell_kwargs)`.
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

    @vcell
    def virtual_straight(
        width: float,
        length: float,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
    ) -> VKCell:
        """Virtual waveguide defined in um.

            ┌──────────────────────────────┐
            │         Slab/Exclude         │
            ├──────────────────────────────┤
            │                              │
            │             Core             │
            │                              │
            ├──────────────────────────────┤
            │         Slab/Exclude         │
            └──────────────────────────────┘
        Args:
            width: Waveguide width. [um]
            length: Waveguide length. [um]
            layer: Main layer of the waveguide.
            enclosure: Definition of slab/excludes. [dbu]
        """
        c = VKCell(kcl=kcl)
        if length < 0:
            logger.critical(
                f"Negative lengths are not allowed {length} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length = -length
        if width < 0:
            logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width

        extrude_backbone(
            c,
            backbone=[kdb.DPoint(0, 0), kdb.DPoint(length, 0)],
            width=width,
            layer=layer,
            enclosure=enclosure,
            start_angle=0,
            end_angle=0,
            dbu=c.kcl.dbu,
        )

        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                width=width,
                length=length,
                layer=layer,
                enclosure=enclosure,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)

        c.create_port(
            name="o1",
            dcplx_trans=kdb.DCplxTrans(1, 180, False, 0, 0),
            layer=c.kcl.layer(layer),
            width=width,
        )
        c.create_port(
            name="o2",
            dcplx_trans=kdb.DCplxTrans(1, 0, False, length, 0),
            layer=c.kcl.layer(layer),
            width=width,
        )
        return c

    return virtual_straight

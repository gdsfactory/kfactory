"""Virtual circular cell factories."""

from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

from ... import kdb
from ...conf import logger
from ...enclosure import LayerEnclosure
from ...kcell import VKCell
from ...layout import KCLayout
from ...settings import Info
from ...typings import MetaData
from .utils import extrude_backbone

__all__ = ["virtual_bend_circular_factory"]


class BendCircularVKCell(Protocol):
    """Factory for virtual circular bend."""

    def __call__(
        self,
        width: float,
        radius: float,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        angle_step: float = 1,
    ) -> VKCell:
        """Create a virtual circular bend.

        Args:
            width: Width of the core. [um]
            radius: Radius of the backbone. [um]
            layer: Layer index of the target layer.
            enclosure: Optional enclosure.
            angle: Angle amount of the bend.
            angle_step: Angle amount per backbone point of the bend.
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

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`VKCell.info`][kfactory.kcell.VKCell.info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting VKCell's name. By default
            the VKCell will be named 'virtual_bend_circular[...]'.
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

    @kcl.vcell(
        basename=basename,
        output_type=VKCell,
        **cell_kwargs,
    )
    def virtual_bend_circular(
        width: float,
        radius: float,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        angle_step: float = 1,
    ) -> VKCell:
        """Create a virtual circular bend.

        Args:
            width: Width of the core. [um]
            radius: Radius of the backbone. [um]
            layer: Layer index of the target layer.
            enclosure: Optional enclosure.
            angle: Angle amount of the bend.
            angle_step: Angle amount per backbone point of the bend.
        """
        c = VKCell()
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
        dbu = c.kcl.dbu
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

        extrude_backbone(
            c=c,
            backbone=backbone,
            width=width,
            layer=layer,
            enclosure=enclosure,
            start_angle=0,
            end_angle=angle,
            dbu=dbu,
        )
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                width=width,
                radius=radius,
                layer=layer,
                enclosure=enclosure,
                angle=angle,
                angle_step=angle_step,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)

        c.create_port(
            name="o1",
            layer=c.kcl.find_layer(layer),
            width=round(width / c.kcl.dbu),
            dcplx_trans=kdb.DCplxTrans(1, 180, False, backbone[0].to_v()),
        )
        c.create_port(
            name="o2",
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            width=width,
            layer=c.kcl.find_layer(layer),
        )
        return c

    return virtual_bend_circular

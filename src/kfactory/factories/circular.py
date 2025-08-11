"""Circular bends.

A circular bend has a constant radius.
"""

from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

from .. import kdb
from ..conf import logger
from ..enclosure import LayerEnclosure, extrude_path
from ..kcell import KCell
from ..layout import KCLayout
from ..settings import Info
from ..typings import MetaData, deg, um

__all__ = ["bend_circular_factory"]


class BendCircularKCell(Protocol):
    def __call__(
        self,
        width: um,
        radius: um,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
        angle: deg = 90,
        angle_step: deg = 1,
    ) -> KCell:
        """Circular radius bend [um].

        Args:
            width: Width of the core. [um]
            radius: Radius of the backbone. [um]
            layer: Layer index of the target layer.
            enclosure: Optional enclosure.
            angle: Angle amount of the bend.
            angle_step: Angle amount per backbone point of the bend.
        """
        ...


def bend_circular_factory(
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
) -> BendCircularKCell:
    """Returns a function generating circular bends.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.kcell.KCell.info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting KCell's name. By default
            the KCell will be named 'straight_dbu[...]'.
        snap_ports: Whether to snap ports to grid.
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

    @kcl.cell(
        basename=basename,
        snap_ports=snap_ports,
        output_type=KCell,
        **cell_kwargs,
    )
    def bend_circular(
        width: um,
        radius: um,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
        angle: deg = 90,
        angle_step: deg = 1,
    ) -> KCell:
        """Circular radius bend [um].

        Args:
            width: Width of the core. [um]
            radius: Radius of the backbone. [um]
            layer: Layer index of the target layer.
            enclosure: Optional enclosure.
            angle: Angle amount of the bend.
            angle_step: Angle amount per backbone point of the bend.
        """
        c = kcl.kcell()
        r = radius

        if angle < 0:
            logger.critical(
                f"Negative angles are not allowed {angle} as ports"
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

        backbone = [
            kdb.DPoint(x, y)
            for x, y in [
                [
                    np.sin(_angle / 180 * np.pi) * r,
                    (-np.cos(_angle / 180 * np.pi) + 1) * r,
                ]
                for _angle in np.linspace(
                    0, angle, int(angle // angle_step + 0.5), endpoint=True
                )
            ]
        ]

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
            trans=kdb.Trans(2, False, 0, 0),
            width=int(width / c.kcl.dbu),
            layer=c.kcl.layer(layer),
        )
        c.create_port(
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            width=c.kcl.to_dbu(width),
            layer=c.kcl.layer(layer),
        )
        c.auto_rename_ports()
        c.boundary = center_path
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
        return c

    return bend_circular

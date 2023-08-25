"""Circular bends.

A circular bend has a constant radius.
"""

from collections.abc import Callable

import numpy as np

from .. import kdb
from ..enclosure import LayerEnclosure, extrude_path
from ..kcell import KCell, KCLayout, LayerEnum, cell

__all__ = ["custom_bend_circular"]


def custom_bend_circular(
    kcl: KCLayout,
) -> Callable[
    [float, float, int | LayerEnum, LayerEnclosure | None, float, float], KCell
]:
    """Circular bend on a custom KClayout."""

    @cell(snap_ports=False)
    def bend_circular(
        width: float,
        radius: float,
        layer: int | LayerEnum,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        angle_step: float = 1,
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
        c = KCell()
        r = radius
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

        extrude_path(
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
            layer=layer,
        )
        c.create_port(
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            dwidth=width,
            layer=layer,
        )
        c.autorename_ports()
        return c

    return bend_circular

"""Circular bends.

A circular bend has a constant radius.
"""

import numpy as np

from .. import kdb
from ..kcell import KCell, LayerEnum, cell
from ..utils import LayerEnclosure, extrude_path

__all__ = ["bend_circular"]


@cell
def bend_circular(
    width: float,
    radius: float,
    layer: int | LayerEnum,
    enclosure: LayerEnclosure | None = None,
    theta: float = 90,
    theta_step: float = 1,
) -> KCell:
    """Circular radius bend [um].

    Args:
        width: Width of the core. [um]
        radius: Radius of the backbone. [um]
        layer: Layer index of the target layer.
        enclosure: Optional enclosure.
        theta: Angle amount of the bend.
        theta_step: Angle amount per backbone point of the bend.
    """
    c = KCell()
    r = radius
    backbone = [
        kdb.DPoint(x, y)
        for x, y in [
            [np.sin(_theta / 180 * np.pi) * r, (-np.cos(_theta / 180 * np.pi) + 1) * r]
            for _theta in np.linspace(
                0, theta, int(theta // theta_step + 0.5), endpoint=True
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
        end_angle=theta,
    )

    c.create_port(
        trans=kdb.Trans(2, False, 0, 0),
        width=int(width / c.kcl.dbu),
        layer=layer,
    )
    c.create_port(
        dcplx_trans=kdb.DCplxTrans(1, theta, False, backbone[-1].to_v()),
        dwidth=width,
        layer=layer,
    )
    c.autorename_ports()
    return c

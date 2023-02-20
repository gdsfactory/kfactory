from typing import Optional

import numpy as np

from .. import kdb
from ..kcell import KCell, LayerEnum, autocell
from ..utils import Enclosure
from ..utils.geo import extrude_path

__all__ = ["bend_circular"]


@autocell
def bend_circular(
    width: float,
    radius: float,
    layer: int | LayerEnum,
    enclosure: Optional[Enclosure] = None,
    theta: float = 90,
    theta_step: float = 1,
) -> KCell:
    """Circular radius bend

    Args:
        width: Width in database units
        radius: Radius in database units
        layer: Layer index of the target layer
        enclosure: :py:class:`kfactory.utils.Enclosure` object to describe the claddings
    Returns:
        cell (KCell): Circular Bend KCell
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
        name="o1",
        trans=kdb.Trans(2, False, 0, 0),
        width=int(width / c.klib.dbu),
        layer=layer,
    )

    match theta:
        case 90:
            c.create_port(
                name="o2",
                trans=kdb.DTrans(1, False, radius, radius).to_itype(c.klib.dbu),
                width=int(width / c.klib.dbu),
                layer=layer,
            )
        case 180:
            c.create_port(
                name="o2",
                trans=kdb.DTrans(0, False, 0, 2 * radius).to_itype(c.klib.dbu),
                width=int(width / c.klib.dbu),
                layer=layer,
            )

    return c

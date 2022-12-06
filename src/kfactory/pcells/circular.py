from typing import Optional

import numpy as np

from .. import kdb
from ..kcell import KCell, autocell
from ..utils import Enclosure
from ..utils.geo import extrude_path

__all__ = ["bend_circular"]


@autocell
def bend_circular(
    width: int,
    radius: int,
    layer: int,
    enclosure: Optional[Enclosure] = None,
    theta: int = 90,
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
    r = radius * c.library.dbu
    backbone = [
        kdb.DPoint(x, y)
        for x, y in [
            [np.sin(_theta / 180 * np.pi) * r, (-np.cos(_theta / 180 * np.pi) + 1) * r]
            for _theta in np.linspace(
                0, theta, int(theta // theta_step + 0.5), endpoint=True
            )
        ]
    ]
    pts = extrude_path(backbone, width * c.library.dbu, snap_to_90=True)

    c.shapes(layer).insert(kdb.DPolygon(pts))

    for p1, p2 in zip(pts[:-1], pts[1:]):
        e = kdb.DEdge(p1, p2)
        c.shapes(layer).insert(e)

    if enclosure is not None:
        enclosure.apply_custom(
            c,
            lambda d: kdb.Polygon(
                [
                    p.to_itype(c.library.dbu)
                    for p in extrude_path(backbone, (d * 2 + width) * c.library.dbu)
                ]
            ),
        )

    c.create_port(name="W0", trans=kdb.Trans(2, False, 0, 0), width=width, layer=layer)

    match theta:
        case 90:
            c.create_port(
                name="N0",
                trans=kdb.Trans(1, False, radius, radius),
                width=width,
                layer=layer,
            )
        case 180:
            c.create_port(
                name="W1",
                trans=kdb.Trans(0, False, 0, 2 * radius),
                width=width,
                layer=layer,
            )

    return c

from typing import Optional

from .. import KCell, autocell, kdb
from ..utils import Enclosure


@autocell
def taper(
    w1: int, w2: int, l: int, layer: int, enclosure: Optional[Enclosure] = None
) -> KCell:
    c = KCell()

    c.shapes(layer).insert(
        kdb.Polygon(
            [
                kdb.Point(0, int(-w1 / 2)),
                kdb.Point(0, w1 // 2),
                kdb.Point(l, w2 // 2),
                kdb.Point(l, int(-w2 / 2)),
            ]
        )
    )

    c.create_port(name="W0", trans=kdb.Trans(2, False, 0, 0), width=w1, layer=layer)
    c.create_port(name="E0", trans=kdb.Trans(0, False, l, 0), width=w2, layer=layer)

    if enclosure is not None:
        enclosure.apply_minkowski_y(c, kdb.Region(c.bbox()))

    return c

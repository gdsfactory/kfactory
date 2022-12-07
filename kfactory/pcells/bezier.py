from typing import Optional

import numpy as np

from .. import KCell, autocell, kdb
from ..utils import Enclosure
from ..utils.geo import bezier_curve, extrude_path

__all__ = ["bend_s"]


@autocell
def bend_s(
    width: int,
    height: int,
    length: int,
    layer: int,
    nb_points: int = 99,
    t_start: int = 0,
    t_stop: int = 1,
    enclosure: Optional[Enclosure] = None,
) -> KCell:
    c = KCell()
    l, h = length * c.library.dbu, height * c.library.dbu
    pts = bezier_curve(
        control_points=[(0.0, 0.0), (l / 2, 0.0), (l / 2, h), (l, h)],
        t=np.linspace(t_start, t_stop, nb_points),
    )

    c.shapes(layer).insert(kdb.DPolygon(extrude_path(pts, width)))

    c.create_port(
        name="W0",
        width=width,
        trans=kdb.Trans(0, False, 0, 0),
        layer=layer,
        port_type="optical",
    )
    c.create_port(
        name="E0",
        width=width,
        trans=kdb.Trans(0, False, int(l), int(h)),
        layer=layer,
        port_type="optical",
    )

    return c


if __name__ == "__main__":
    c = bend_s()
    c.show()

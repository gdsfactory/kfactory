from typing import Optional

import numpy as np

from .. import KCell, LayerEnum, autocell, kdb
from ..utils import Enclosure
from ..utils.geo import bezier_curve, extrude_path

__all__ = ["bend_s"]


@autocell
def bend_s(
    width: float,
    height: float,
    length: float,
    layer: int | LayerEnum,
    nb_points: int = 99,
    t_start: int = 0,
    t_stop: int = 1,
    enclosure: Optional[Enclosure] = None,
) -> KCell:
    c = KCell()
    l, h = length, height
    pts = bezier_curve(
        control_points=[(0.0, 0.0), (l / 2, 0.0), (l / 2, h), (l, h)],
        t=np.linspace(t_start, t_stop, nb_points),
    )

    extrude_path(c, layer, pts, width, enclosure, start_angle=180, end_angle=0)

    c.create_port(
        name="W0",
        width=int(width / c.klib.dbu),
        trans=kdb.Trans(0, False, 0, 0),
        layer=layer,
        port_type="optical",
    )
    c.create_port(
        name="E0",
        width=int(width / c.klib.dbu),
        trans=kdb.Trans(
            0, False, c.bbox().right, c.bbox().top - int(width / c.klib.dbu) // 2
        ),
        layer=layer,
        port_type="optical",
    )

    return c

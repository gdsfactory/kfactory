from typing import Optional, Sequence

import numpy as np
from scipy.special import binom  # type: ignore[import]

from .. import KCell, LayerEnum, autocell, kdb
from ..utils import Enclosure
from ..utils.geo import extrude_path

__all__ = ["bend_s"]


def bezier_curve(
    t: np.typing.NDArray[np.float64],
    control_points: Sequence[tuple[np.float64 | float, np.float64 | float]],
) -> list[kdb.DPoint]:
    xs = np.zeros(t.shape, dtype=np.float64)
    ys = np.zeros(t.shape, dtype=np.float64)
    n = len(control_points) - 1
    for k in range(n + 1):
        ank = binom(n, k) * (1 - t) ** (n - k) * t**k
        xs += ank * control_points[k][0]
        ys += ank * control_points[k][1]

    return [kdb.DPoint(float(x), float(y)) for x, y in zip(xs, ys)]


@autocell
def bend_s(
    width: float,
    height: float,
    length: float,
    layer: int | LayerEnum,
    nb_points: int = 99,
    t_start: float = 0,
    t_stop: float = 1,
    enclosure: Optional[Enclosure] = None,
) -> KCell:
    c = KCell()
    l, h = length, height
    pts = bezier_curve(
        control_points=[(0.0, 0.0), (l / 2, 0.0), (l / 2, h), (l, h)],
        t=np.linspace(t_start, t_stop, nb_points),
    )

    if enclosure is None:
        enclosure = Enclosure()

    enclosure.extrude_path(c, path=pts, main_layer=layer, width=width)
    # extrude_path(c, layer, pts, width, enclosure, start_angle=180, end_angle=0)

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

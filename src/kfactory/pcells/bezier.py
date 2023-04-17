"""Bezier curve based bends and functions."""

from collections.abc import Sequence

import numpy as np
import numpy.typing as nty
from scipy.special import binom  # type: ignore[import]

from .. import KCell, LayerEnum, autocell, kdb
from ..utils import Enclosure

__all__ = ["bend_s"]


def bezier_curve(
    t: nty.NDArray[np.float64],
    control_points: Sequence[tuple[np.float64 | float, np.float64 | float]],
) -> list[kdb.DPoint]:
    """Calculates the backbone of a bezier bend."""
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
    enclosure: Enclosure | None = None,
) -> KCell:
    """Creat a bezier bend.

    Args:
        width: Width of the core. [um]
        height: height difference of left/right. [um]
        length: Length of the bend. [um]
        layer: Layer index of the core.
        nb_points: Number of points of the backbone.
        t_start: start
        t_stop: end
        enclosure: Slab/Exclude definition. [dbu]
    """
    c = KCell()
    _length, _height = length, height
    pts = bezier_curve(
        control_points=[
            (0.0, 0.0),
            (_length / 2, 0.0),
            (_length / 2, _height),
            (_length, _height),
        ],
        t=np.linspace(t_start, t_stop, nb_points),
    )

    if enclosure is None:
        enclosure = Enclosure()

    enclosure.extrude_path(c, path=pts, main_layer=layer, width=width)

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

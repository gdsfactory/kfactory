"""Bezier curve based bends and functions."""


from collections.abc import Callable

import numpy as np

from .. import KCell, KCLayout, LayerEnum, cell, kdb
from ..cells.bezier import bezier_curve
from ..enclosure import LayerEnclosure

__all__ = ["custom_bend_s"]


def custom_bend_s(
    kcl: KCLayout,
) -> Callable[[float, float, float, int | LayerEnum, int, float, float], KCell]:
    """Bezier cell function with a custom KCLayout object."""

    @cell
    def bend_s(
        width: float,
        height: float,
        length: float,
        layer: int | LayerEnum,
        nb_points: int = 99,
        t_start: float = 0,
        t_stop: float = 1,
        enclosure: LayerEnclosure | None = None,
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
        c = kcl.kcell()
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
            enclosure = LayerEnclosure()

        enclosure.extrude_path(
            c, path=pts, main_layer=layer, width=width, start_angle=0, end_angle=0
        )

        c.create_port(
            width=int(width / c.kcl.dbu),
            trans=kdb.Trans(2, False, 0, 0),
            layer=layer,
            port_type="optical",
        )
        c.create_port(
            width=int(width / c.kcl.dbu),
            trans=kdb.Trans(
                0, False, c.bbox().right, c.bbox().top - int(width / c.kcl.dbu) // 2
            ),
            layer=layer,
            port_type="optical",
        )

        c.autorename_ports()

        return c

    return bend_s

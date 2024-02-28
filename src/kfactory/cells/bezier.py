"""Bezier curve based bends and functions."""

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import numpy.typing as nty
from scipy.special import binom  # type:ignore[import-untyped,unused-ignore]

from .. import kdb
from ..enclosure import LayerEnclosure
from ..kcell import Info, KCell, KCLayout, LayerEnum, MetaData, kcl

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


class BendS:
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

    kcl: KCLayout

    def __init__(
        self,
        kcl: KCLayout,
        additional_info: Callable[
            ...,
            dict[str, MetaData],
        ]
        | dict[str, MetaData]
        | None = None,
        basename: str | None = None,
        **cell_kwargs: Any,
    ) -> None:
        """Bezier bend function on custom KCLayout."""
        self.kcl = kcl
        self._cell = self.kcl.cell(
            basename=basename or self.__class__.__name__, **cell_kwargs
        )(self._kcell)
        if callable(additional_info) and additional_info is not None:
            self._additional_info_func: Callable[
                ...,
                dict[str, MetaData],
            ] = additional_info
            self._additional_info: dict[str, MetaData] = {}
        else:

            def additional_info_func(
                **kwargs: Any,
            ) -> dict[str, MetaData]:
                return {}

            self._additional_info_func = additional_info_func
            self._additional_info = additional_info or {}

    def __call__(
        self,
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
        return self._cell(
            width=width,
            height=height,
            length=length,
            layer=layer,
            nb_points=nb_points,
            t_start=t_start,
            t_stop=t_stop,
            enclosure=enclosure,
        )

    def _kcell(
        self,
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
        c = self.kcl.kcell()
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
        _info: dict[str, MetaData] = {}
        _info.update(
            self._additional_info_func(
                width=width,
                height=height,
                length=length,
                layer=layer,
                nb_points=nb_points,
                t_start=t_start,
                t_stop=t_stop,
                enclosure=enclosure,
            )
        )
        _info.update(self._additional_info)
        c.info = Info(**_info)

        c.auto_rename_ports()

        return c


bend_s = BendS(kcl)

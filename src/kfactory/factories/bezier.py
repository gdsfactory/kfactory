"""Bezier curve based bends and functions."""

from collections.abc import Callable, Sequence
from typing import Any, Protocol

import numpy as np
import numpy.typing as nty
from scipy.special import binom  # type:ignore[import-untyped,unused-ignore]

from .. import kdb, kf_types
from ..enclosure import CrossSection, LayerEnclosure
from ..kcell import Info, KCell, KCLayout, MetaData

__all__ = ["bend_s_bezier_factory"]


class BezierKCell(Protocol):
    def __call__(
        self,
        cross_section: CrossSection,
        height: kf_types.um,
        length: kf_types.um,
        nb_points: int = 99,
        t_start: float = 0,
        t_stop: float = 1,
        enclosure: LayerEnclosure | None = None,
    ) -> KCell:
        """Creat a bezier bend.

        Args:
            cross_section: The cross-section to build the bend from.
            height: height difference of left/right. [um]
            length: Length of the bend. [um]
            nb_points: Number of points of the backbone.
            t_start: start
            t_stop: end
            enclosure: Slab/Exclude definition. [dbu]
        """
        ...


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


def bend_s_bezier_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    basename: str | None = None,
    **cell_kwargs: Any,
) -> BezierKCell:
    """Returns a function generating bezier s-bends.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.kcell.KCell.info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting KCell's name. By default
            the KCell will be named 'straight_dbu[...]'.
        cell_kwargs: Additional arguments passed as `@kcl.cell(**cell_kwargs)`.
    """
    if callable(additional_info) and additional_info is not None:
        _additional_info_func: Callable[
            ...,
            dict[str, MetaData],
        ] = additional_info
        _additional_info: dict[str, MetaData] = {}
    else:

        def additional_info_func(
            **kwargs: Any,
        ) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}

    @kcl.cell(basename=basename, **cell_kwargs)
    def bend_s_bezier(
        cross_section: CrossSection,
        height: kf_types.um,
        length: kf_types.um,
        nb_points: int = 99,
        t_start: float = 0,
        t_stop: float = 1,
    ) -> KCell:
        """Creat a bezier bend.

        Args:
            cross_section: The cross-section to build the bend from.
            height: height difference of left/right. [um]
            length: Length of the bend. [um]
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

        cross_section.extrude_path(target=c, path=pts, start_angle=0, end_angle=0)

        c.create_port(
            cross_section=cross_section,
            trans=kdb.Trans(2, False, 0, 0),
            port_type="optical",
        )
        c.create_port(
            cross_section=cross_section,
            trans=kdb.Trans(
                0, False, c.bbox().right, c.bbox().top - cross_section.width
            ),
            port_type="optical",
        )
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                height=height,
                length=length,
                nb_points=nb_points,
                t_start=t_start,
                t_stop=t_stop,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)

        c.auto_rename_ports()

        return c

    return bend_s_bezier

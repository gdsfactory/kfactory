"""Bezier curve based bends and functions."""

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Protocol, Unpack, cast, overload

import numpy as np
import numpy.typing as npt
from scipy.special import binom  # type:ignore[import-untyped,unused-ignore]

from .. import kdb
from ..enclosure import LayerEnclosure
from ..kcell import KCell
from ..layout import CellKWargs, KCLayout
from ..port import rename_by_direction, rename_clockwise
from ..settings import Info
from ..typings import KC, KC_co, MetaData, um

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..enclosure import LayerEnclosure
    from ..kcell import KCell

__all__ = ["bend_s_bezier_factory"]


class BezierFactory(Protocol[KC_co]):
    def __call__(
        self,
        width: um,
        height: um,
        length: um,
        layer: kdb.LayerInfo,
        nb_points: int = 99,
        t_start: float = 0,
        t_stop: float = 1,
        enclosure: LayerEnclosure | None = None,
    ) -> KC_co:
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
        ...


def bezier_curve(
    t: npt.NDArray[np.floating[Any]],
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

    return [kdb.DPoint(float(x), float(y)) for x, y in zip(xs, ys, strict=False)]


@overload
def bend_s_bezier_factory(
    kcl: KCLayout,
    *,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BezierFactory[KCell]: ...
@overload
def bend_s_bezier_factory(
    kcl: KCLayout,
    *,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    output_type: type[KC],
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BezierFactory[KC]: ...


def bend_s_bezier_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    output_type: type[KC] | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BezierFactory[KC]:
    """Returns a function generating bezier s-bends.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.settings.Info]. Can be a static dict
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

    ports = cell_kwargs.get("ports")
    if ports is None:
        if kcl.rename_function == rename_clockwise:
            cell_kwargs["ports"] = {"left": ["o1"], "right": ["o2"]}
        elif kcl.rename_function == rename_by_direction:
            cell_kwargs["ports"] = {"left": ["W0"], "right": ["E0"]}

    if output_type is not None:
        cell = kcl.cell(output_type=output_type, **cell_kwargs)
    else:
        cell = kcl.cell(output_type=cast("type[KC]", KCell), **cell_kwargs)

    @cell
    def bend_s_bezier(
        width: um,
        height: um,
        length: um,
        layer: kdb.LayerInfo,
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
            layer=c.kcl.layer(layer),
            port_type=port_type,
        )
        c.create_port(
            width=int(width / c.kcl.dbu),
            trans=kdb.Trans(0, False, c.bbox().right, kcl.to_dbu(height)),
            layer=c.kcl.layer(layer),
            port_type=port_type,
        )
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
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
        _info.update(_additional_info)
        c.info = Info(**_info)

        c.auto_rename_ports()

        return c

    return bend_s_bezier

"""Bezier curve based bends and functions."""

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Protocol, Unpack, cast, overload

import numpy as np
import numpy.typing as npt
from scipy.special import binom

from .. import kdb
from ..cross_section import (
    AnyCrossSectionInput,
    CrossSectionSpec,
    DCrossSectionSpec,
)
from ..enclosure import LayerEnclosure, extrude_path_cross_section
from ..kcell import KCell
from ..layout import CellKWargs, KCLayout
from ..port import rename_by_direction, rename_clockwise
from ..settings import Info
from ..typings import KC, KC_co, MetaData, um
from .utils import (
    _is_additional_info_func,
    boundary_from_shapes,
    cross_section_from_width,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..kcell import KCell

__all__ = ["bend_s_bezier_factory"]


class BezierFactory(Protocol[KC_co]):
    def __call__(
        self,
        *,
        height: um,
        length: um,
        nb_points: int = 99,
        t_start: float = 0,
        t_stop: float = 1,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpec
        | DCrossSectionSpec
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC_co:
        """Create a bezier bend.

        Either pass a ``cross_section`` or the legacy ``width``/``layer``/``enclosure``.

        Args:
            height: height difference of left/right. [um]
            length: Length of the bend. [um]
            nb_points: Number of points of the backbone.
            t_start: start
            t_stop: end
            cross_section: Cross section of the bend.
            width: Width of the core. [um] (legacy; requires ``layer``)
            layer: Layer index of the core. (legacy)
            enclosure: Slab/Exclude definition. (legacy)
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
    """Returns a function generating bezier s-bends (generic interface).

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.settings.Info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the bend
            functions' parameters as kwargs and returns a dict with the mapping.
        cell_kwargs: Additional arguments passed as `@kcl.cell(**cell_kwargs)`.
    """
    _additional_info: dict[str, MetaData] = {}
    if _is_additional_info_func(additional_info):
        _additional_info_func: Callable[
            ...,
            dict[str, MetaData],
        ] = additional_info
    else:

        def additional_info_func(
            **kwargs: Any,
        ) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}  # ty:ignore[invalid-assignment]

    ports = cell_kwargs.get("ports")
    if ports is None:
        if kcl.rename_function == rename_clockwise:
            cell_kwargs["ports"] = {"left": ["o1"], "right": ["o2"]}
        elif kcl.rename_function == rename_by_direction:
            cell_kwargs["ports"] = {"left": ["W0"], "right": ["E0"]}
    cell_kwargs.setdefault("basename", "bend_s_bezier")
    basename = cell_kwargs["basename"]

    if output_type is not None:
        cell = kcl.cell(output_type=output_type, **cell_kwargs)
    else:
        cell = kcl.cell(output_type=cast("type[KC]", KCell), **cell_kwargs)

    @cell
    def _bend_s_bezier(
        cross_section: str | AnyCrossSectionInput,
        height: um,
        length: um,
        nb_points: int = 99,
        t_start: float = 0,
        t_stop: float = 1,
    ) -> KCell:
        """Bezier bend [um] from a cross section."""
        c = kcl.kcell()
        xs = kcl.get_base_cross_section(cross_section)
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

        extrude_path_cross_section(c, pts, xs, start_angle=0, end_angle=0)

        c.create_port(
            name="o1",
            cross_section=xs,
            trans=kdb.Trans(2, False, 0, 0),
            port_type=port_type,
        )
        c.create_port(
            name="o2",
            cross_section=xs,
            trans=kdb.Trans(0, False, c.bbox().right, kcl.to_dbu(height)),
            port_type=port_type,
        )
        boundary = boundary_from_shapes(c)
        if boundary is not None:
            c.boundary = boundary
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                cross_section=xs,
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

    @kcl.generic_factory(name=basename)
    def bend_s_bezier(
        *,
        height: um,
        length: um,
        nb_points: int = 99,
        t_start: float = 0,
        t_stop: float = 1,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpec
        | DCrossSectionSpec
        | None = None,
        width: um | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC:
        if cross_section is None:
            if width is None or layer is None:
                raise ValueError(
                    "Provide a cross_section, or width and layer (legacy call)."
                )
            xs = cross_section_from_width(kcl, kcl.to_dbu(width), layer, enclosure)
        else:
            xs = kcl.get_icross_section(cross_section)
        return _bend_s_bezier(
            cross_section=xs,
            height=height,
            length=length,
            nb_points=nb_points,
            t_start=t_start,
            t_stop=t_stop,
        )

    return bend_s_bezier

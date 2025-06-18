"""Length function for calculating length of manhattan routes."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import klayout.db as kdb

if TYPE_CHECKING:
    from .generic import ManhattanRoute

__all__ = [
    "LengthFunction",
    "get_length_from_area",
    "get_length_from_backbone",
    "get_length_from_info",
]


@runtime_checkable
class LengthFunction(Protocol):
    """Protocol for a function which calculates the length of a route."""

    def __call__(self, route: ManhattanRoute) -> int | float: ...


@cache
def _get_area_from_layer(kcl: str, ci: int, layer: kdb.LayerInfo, width: int) -> float:
    from ..layout import kcls

    c = kcls[kcl][ci]
    return (
        kdb.Region(c.kdb_cell.begin_shapes_rec(c.kcl.layer(layer))).merge().area()
        / width
    )


def get_length_from_area(layer: kdb.LayerInfo | None = None) -> LengthFunction:
    """Get length from are in dbu.

    Args:
        layer: The layer for which to calculate the area.

    Returns:
        Length in dbu.
    """

    def get_length_(route: ManhattanRoute) -> float:
        if not route.instances:
            return 0
        layer_ = layer or route.start_port.layer_info

        length: float = 0
        width = route.start_port.width

        for inst in route.instances:
            length += _get_area_from_layer(
                inst.cell.kcl.name, inst.cell.cell_index(), layer_, width
            )

        return length

    return get_length_


def get_length_from_info(
    route: ManhattanRoute, attribute_name: str = "length"
) -> int | float:
    return sum(inst.cell.info[attribute_name] for inst in route.instances)  # type: ignore[no-any-return]


def get_length_from_backbone(route: ManhattanRoute) -> int:
    return route.length_backbone

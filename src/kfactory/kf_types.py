"""KFactory types.

Mainly units for annotating types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Protocol

from . import kdb

if TYPE_CHECKING:
    from .kcell import KCell, LayerEnum, Port  # noqa: F401
    from .routing.optical import OpticalManhattanRoute

__all__ = [
    "um",
    "dbu",
    "rad",
    "deg",
    "layer",
    "ManhattanRoutePathFunction",
    "ManhattanRoutePathFunction180",
]

um = Annotated[float, "um"]
"""Float in micrometer."""
dbu = Annotated[int, "dbu"]
"""Integer in database units."""
deg = Annotated[float, "deg"]
"""Float in degrees."""
rad = Annotated[float, "rad"]
"""Float in radians."""
layer = Annotated["int | LayerEnum", "layer"]
"""Integer or enum index of a Layer."""


class StraightFactory(Protocol):
    """Factory Protocol for routing.

    A straight factory must return a KCell with only a width and length given.
    """

    def __call__(self, width: int, length: int) -> KCell:
        """Produces the KCell.

        E.g. in a function this would amount to
        `straight_factory(length=10_000, width=1000)`
        """
        ...


class ManhattanRoutePathFunction(Protocol):
    """Minimal signature of a manhattan function."""

    def __call__(
        self,
        port1: Port | kdb.Trans,
        port2: Port | kdb.Trans,
        bend90_radius: int,
        start_straight: int,
        end_straight: int,
    ) -> list[kdb.Point]:
        """Minimal kwargs of a manhattan route function."""
        ...


class ManhattanRoutePathFunction180(Protocol):
    """Minimal signature of a manhattan function with 180° bend routing."""

    def __call__(
        self,
        port1: Port | kdb.Trans,
        port2: Port | kdb.Trans,
        bend90_radius: int,
        bend180_radius: int,
        start_straight: int,
        end_straight: int,
    ) -> list[kdb.Point]:
        """Minimal kwargs of a manhattan route function with 180° bend."""
        ...


class RouteFunction(Protocol):
    def __call__(
        self,
        start_ports: list[Port],
        end_ports: list[Port],
        separation: int,
        straight_factory: StraightFactory,
        bend90_cell: KCell,
        taper_cell: KCell | None = None,
        start_straights: int | list[int] = 0,
        end_straights: int | list[int] = 0,
        place_port_type: str = "optical",
        bboxes: list[kdb.Box] = [],
        allow_different_port_widths: bool = False,
        route_width: int | list[int] | None = None,
    ) -> list[OpticalManhattanRoute]: ...

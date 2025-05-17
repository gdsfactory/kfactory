from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, overload, runtime_checkable

from .typings import TUnit

if TYPE_CHECKING:
    from .layer import LayerEnum

__all__ = ["BoxFunction", "BoxLike", "PointLike"]


@runtime_checkable
class PointLike(Protocol[TUnit]):
    """Protocol for a point.

    Mirrors some functionality of  kdb.DPoint, kdb.Point,
    but provides generic types for the units.
    """

    x: TUnit
    y: TUnit


@runtime_checkable
class BoxLike(Protocol[TUnit]):
    """Protocol for a box.

    Mirrors some functionality of kdb.DBox, kdb.Box,
    but provides generic types for the units.
    """

    left: TUnit
    bottom: TUnit
    right: TUnit
    top: TUnit

    def center(self) -> PointLike[TUnit]:
        """Get the center of the box."""
        ...

    def width(self) -> TUnit:
        """Get the width of the box."""
        ...

    def height(self) -> TUnit:
        """Get the height of the box."""
        ...

    def empty(self) -> bool:
        """Check if the box is empty."""
        ...


@runtime_checkable
class BoxFunction(Protocol[TUnit]):
    """Protocol for a box function.

    Represents bbox/ibbox/dbbox functions.
    """

    @overload
    def __call__(self) -> BoxLike[TUnit]: ...
    @overload
    def __call__(self, layer: LayerEnum | int) -> BoxLike[TUnit]: ...

    def __call__(self, layer: LayerEnum | int | None = None) -> BoxLike[TUnit]:
        """Call the box function."""
        ...

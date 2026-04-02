from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, overload, runtime_checkable

if TYPE_CHECKING:
    from .layer import LayerEnum

__all__ = ["BoxFunction", "BoxLike", "PointLike"]


@runtime_checkable
class PointLike[T: (int, float)](Protocol):
    """Protocol for a point.

    Mirrors some functionality of  kdb.DPoint, kdb.Point,
    but provides generic types for the units.
    """

    x: T
    y: T


@runtime_checkable
class BoxLike[T: (int, float)](Protocol):
    """Protocol for a box.

    Mirrors some functionality of kdb.DBox, kdb.Box,
    but provides generic types for the units.
    """

    left: T
    bottom: T
    right: T
    top: T

    def center(self) -> PointLike[T]:
        """Get the center of the box."""
        ...

    def width(self) -> T:
        """Get the width of the box."""
        ...

    def height(self) -> T:
        """Get the height of the box."""
        ...

    def empty(self) -> bool:
        """Check if the box is empty."""
        ...


@runtime_checkable
class BoxFunction[T: (int, float)](Protocol):
    """Protocol for a box function.

    Represents bbox/ibbox/dbbox functions.
    """

    @overload
    def __call__(self) -> BoxLike[T]: ...
    @overload
    def __call__(self, layer: LayerEnum | int) -> BoxLike[T]: ...

    def __call__(self, layer: LayerEnum | int | None = None) -> BoxLike[T]:
        """Call the box function."""
        ...

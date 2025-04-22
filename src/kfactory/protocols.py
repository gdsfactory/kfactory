from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Protocol,
    overload,
    runtime_checkable,
)

from . import kdb

if TYPE_CHECKING:
    from .layer import LayerEnum
    from .port import DPort, Port, ProtoPort

from .typings import Angle, TUnit

__all__ = [
    "BoxFunction",
    "BoxLike",
    "CreatePortFunction",
    "CreatePortFunctionFloat",
    "CreatePortFunctionInt",
    "PointLike",
]


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


@runtime_checkable
class CreatePortFunction(Protocol[TUnit]):
    """Protocol for the different argument variants a function can have to create a port."""

    @overload
    def __call__(
        self,
        *,
        trans: kdb.Trans,
        width: TUnit,
        layer: int | LayerEnum,
        name: str | None = None,
        port_type: str = "optical",
    ) -> ProtoPort[TUnit]: ...

    @overload
    def __call__(
        self,
        *,
        trans: kdb.Trans,
        width: TUnit,
        layer_info: kdb.LayerInfo,
        name: str | None = None,
        port_type: str = "optical",
    ) -> ProtoPort[TUnit]: ...

    @overload
    def __call__(
        self,
        *,
        dcplx_trans: kdb.DCplxTrans,
        width: TUnit,
        layer: LayerEnum | int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> ProtoPort[TUnit]: ...

    @overload
    def __call__(
        self,
        *,
        dcplx_trans: kdb.DCplxTrans,
        width: TUnit,
        layer_info: kdb.LayerInfo,
        name: str | None = None,
        port_type: str = "optical",
    ) -> ProtoPort[TUnit]: ...


class CreatePortFunctionInt(CreatePortFunction[int], Protocol):
    @overload
    def __call__(
        self,
        *,
        width: int,
        layer: LayerEnum | int,
        center: tuple[int, int],
        angle: Angle,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    @overload
    def __call__(
        self,
        *,
        width: int,
        layer_info: kdb.LayerInfo,
        center: tuple[int, int],
        angle: Angle,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...


class CreatePortFunctionFloat(CreatePortFunction[float], Protocol):
    @overload
    def __call__(
        self,
        *,
        width: float,
        layer: LayerEnum | int,
        center: tuple[float, float],
        orientation: float,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def __call__(
        self,
        *,
        width: float,
        layer_info: kdb.LayerInfo,
        center: tuple[float, float],
        orientation: float,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

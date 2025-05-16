from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, overload, runtime_checkable

from .typings import Angle, TUnit

if TYPE_CHECKING:
    import klayout.db as kdb

    from .cross_section import SymmetricalCrossSection
    from .layer import LayerEnum
    from .layout import KCLayout
    from .port import DPort, Port, ProtoPort

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


class ICreatePort(ABC):
    """Protocol for a create_port functionality"""

    @property
    @abstractmethod
    def kcl(self) -> KCLayout: ...

    @overload
    def create_port(
        self,
        *,
        trans: kdb.Trans,
        width: int,
        layer: int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    @overload
    def create_port(
        self,
        *,
        dcplx_trans: kdb.DCplxTrans,
        width: int,
        layer: LayerEnum | int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    @overload
    def create_port(
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
    def create_port(
        self,
        *,
        trans: kdb.Trans,
        width: int,
        layer_info: kdb.LayerInfo,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    @overload
    def create_port(
        self,
        *,
        width: int,
        layer_info: kdb.LayerInfo,
        center: tuple[int, int],
        angle: Angle,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    def create_port(
        self,
        *,
        name: str | None = None,
        width: int | None = None,
        layer: LayerEnum | int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        port_type: str = "optical",
        trans: kdb.Trans | None = None,
        dcplx_trans: kdb.DCplxTrans | None = None,
        center: tuple[int, int] | None = None,
        angle: Angle | None = None,
        mirror_x: bool = False,
        cross_section: SymmetricalCrossSection | None = None,
    ) -> Port:
        """Create a port."""
        from .port import Port

        port = Port(
            name=name,
            width=width,
            layer=layer,
            layer_info=layer_info,
            port_type=port_type,
            trans=trans,
            dcplx_trans=dcplx_trans,
            center=center,
            angle=angle,
            mirror_x=mirror_x,
            cross_section=cross_section,
        )  # type: ignore[call-overload, misc]
        return self.add_port(port=port)

    @abstractmethod
    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> Port: ...


class DCreatePort(ABC):
    """Protocol for a create_port functionality"""

    @property
    @abstractmethod
    def kcl(self) -> KCLayout: ...

    @overload
    def create_port(
        self,
        *,
        trans: kdb.Trans,
        width: float,
        layer: int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def create_port(
        self,
        *,
        dcplx_trans: kdb.DCplxTrans,
        width: float,
        layer: LayerEnum | int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def create_port(
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
    def create_port(
        self,
        *,
        trans: kdb.Trans,
        width: float,
        layer_info: kdb.LayerInfo,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def create_port(
        self,
        *,
        dcplx_trans: kdb.DCplxTrans,
        width: float,
        layer_info: kdb.LayerInfo,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def create_port(
        self,
        *,
        width: float,
        layer_info: kdb.LayerInfo,
        center: tuple[float, float],
        orientation: float,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    def create_port(
        self,
        *,
        name: str | None = None,
        width: float | None = None,
        layer: LayerEnum | int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        port_type: str = "optical",
        trans: kdb.Trans | None = None,
        dcplx_trans: kdb.DCplxTrans | None = None,
        center: tuple[float, float] | None = None,
        orientation: float | None = None,
        mirror_x: bool = False,
        cross_section: SymmetricalCrossSection | None = None,
    ) -> DPort:
        """Create a port."""
        from .port import DPort

        port = DPort(
            kcl=self.kcl,
            cross_section=cross_section,
            trans=trans,
            dcplx_trans=dcplx_trans,
            center=center,
            orientation=orientation,
            mirror_x=mirror_x,
            port_type=port_type,
            layer=layer,
            layer_info=layer_info,
        )  # type: ignore[call-overload, misc]
        return self.add_port(port=port)

    @abstractmethod
    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> DPort: ...

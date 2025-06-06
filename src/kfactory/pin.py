from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, overload

from pydantic import BaseModel
from typing_extensions import TypedDict

from . import kdb
from .settings import Info
from .typings import TUnit

if TYPE_CHECKING:
    from .kcell import ProtoTKCell


class BasePinDict(TypedDict):
    name: str | None
    c: ProtoTKCell[Any]
    ports: set[str]
    info: Info
    pin_type: str


class BasePin(BaseModel, arbitrary_types_allowed=True):
    name: str | None
    c: ProtoTKCell[Any]
    ports: set[str]
    info: Info = Info()
    pin_type: str

    def __copy__(self) -> BasePin:
        """Copy the BasePin."""
        return BasePin(
            name=self.name,
            c=self.c.dup(),
            ports=self.ports,
            info=self.info.model_copy(),
            pin_type=self.pin_type,
        )

    def transformed(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> BasePin:
        base = self.__copy__()
        base.c.transform(trans)
        base.c.transform(post_trans)

        return base


class ProtoPin(Generic[TUnit], ABC):
    """Base class for kf.Pin, kf.DPin."""

    yaml_tag: str = "!Pin"
    _base: BasePin

    @abstractmethod
    def __init__(
        self,
        name: str | None = None,
        *,
        c: ProtoTKCell[TUnit] | None = None,
        ports: list[str] | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
        pin: ProtoPin[TUnit] | None = None,
        base: BasePin | None = None,
    ) -> None: ...

    @property
    def base(self) -> BasePin:
        """Get the BasePin associated with this Pin."""
        return self._base

    @property
    def name(self) -> str | None:
        """Name of the pin."""
        return self._base.name

    @name.setter
    def name(self, value: str | None) -> None:
        self._base.name = value

    @property
    @abstractmethod
    def c(self) -> ProtoTKCell[TUnit]:
        """Cell associated to the pin."""
        ...

    @c.setter
    @abstractmethod
    def c(self, value: ProtoTKCell[TUnit]) -> None: ...

    @property
    def pin_type(self) -> str:
        """Type of the pin."""
        return self._base.pin_type

    @pin_type.setter
    def pin_type(self, value: str) -> None:
        self._base.pin_type = value

    @property
    def info(self) -> Info:
        """Additional info about the pin."""
        return self._base.info

    @info.setter
    def info(self, value: Info) -> None:
        self._base.info = value

    @property
    def ports(self) -> list[str] | None:
        return list(self._base.ports)

    @ports.setter
    def ports(self, value: list[str]) -> None:
        self._base.ports = set(value)

    def to_itype(self) -> Pin:
        """Convert the pin to a dbu pin."""
        return Pin(base=self._base)

    def to_dtype(self) -> DPin:
        """Convert the pin to a um pin."""
        return DPin(base=self._base)

    def __eq__(self, other: object) -> bool:
        """Support for `pin1 == pin2` comparisons."""
        if isinstance(other, ProtoPin):
            return self._base == other._base
        return False

    @abstractmethod
    def copy(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> ProtoPin[TUnit]:
        """Copy the pin with a transformation."""
        ...

    def __repr__(self) -> str:
        """String representation of pin."""
        return (
            f"{self.__class__.__name__}({self.name},"
            f"cell={self.c}, ports={self.ports}, "
            f"pin_type={self.pin_type})"
        )


class Pin(ProtoPin[int]):
    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        c: ProtoTKCell[int] | None = None,
        ports: list[str] | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
    ) -> None: ...

    @overload
    def __init__(self, *, base: BasePin) -> None: ...

    @overload
    def __init__(self, *, pin: Pin) -> None: ...

    def __init__(
        self,
        *,
        name: str | None = None,
        c: ProtoTKCell[int] | None = None,
        ports: list[str] | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
        pin: Pin | None = None,
        base: BasePin | None = None,
    ) -> None:
        if info is None:
            info = {}
        if base is not None:
            self._base = base
            return
        if pin is not None:
            self._base = pin.base.__copy__()
            return
        info_ = Info(**info)

        if not c:
            raise ValueError("A cell must be provided to create a Pin.")
        if not ports:
            raise ValueError(
                f"Port names associated with the cell must be provided "
                f"to create a Pin. Available names for the provided cell "
                f"are {[v.name for v in c.ports._bases]}"
            )
        self._base = BasePin(
            name=name,
            c=c,
            ports=set(ports),
            info=info_,
            pin_type=pin_type,
        )

    @property
    def c(self) -> ProtoTKCell[int]:
        """Cell associated to the pin."""
        return self._base.c

    @c.setter
    @abstractmethod
    def c(self, value: ProtoTKCell[int]) -> None:
        self._base.c = value

    def copy(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> Pin:
        """Copy the pin with a transformation."""
        return Pin(base=self._base.transformed(trans=trans, post_trans=post_trans))


class DPin(ProtoPin[float]):
    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        c: ProtoTKCell[float] | None = None,
        ports: list[str] | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
    ) -> None: ...

    @overload
    def __init__(self, *, base: BasePin) -> None: ...

    @overload
    def __init__(self, *, pin: DPin) -> None: ...

    def __init__(
        self,
        *,
        name: str | None = None,
        c: ProtoTKCell[float] | None = None,
        ports: list[str] | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
        pin: DPin | None = None,
        base: BasePin | None = None,
    ) -> None:
        if info is None:
            info = {}
        if base is not None:
            self._base = base
            return
        if pin is not None:
            self._base = pin.base.__copy__()
            return
        info_ = Info(**info)

        if not c:
            raise ValueError("A cell must be provided to create a DPin.")
        if not ports:
            raise ValueError(
                f"Port names associated with the cell must be provided "
                f"to create a DPin. Available names for the provided cell "
                f"are {[v.name for v in c.ports._bases]}"
            )
        self._base = BasePin(
            name=name,
            c=c,
            ports=set(ports),
            info=info_,
            pin_type=pin_type,
        )

    @property
    def c(self) -> ProtoTKCell[float]:
        """Cell associated to the pin."""
        return self._base.c

    @c.setter
    @abstractmethod
    def c(self, value: ProtoTKCell[float]) -> None:
        self._base.c = value

    def copy(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> DPin:
        """Copy the pin with a transformation."""
        return DPin(base=self._base.transformed(trans=trans, post_trans=post_trans))

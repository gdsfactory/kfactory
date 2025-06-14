from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic

from pydantic import BaseModel
from typing_extensions import TypedDict

from .settings import Info
from .typings import TUnit

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .layout import KCLayout
    from .port import BasePort, DPort, Port, ProtoPort

__all__ = ["DPin", "Pin", "ProtoPin"]


class BasePinDict(TypedDict):
    name: str | None
    kcl: KCLayout
    ports: set[BasePort]
    info: Info
    pin_type: str


class BasePin(BaseModel, arbitrary_types_allowed=True):
    name: str | None
    kcl: KCLayout
    ports: set[BasePort]
    info: Info = Info()
    pin_type: str


class ProtoPin(Generic[TUnit], ABC):
    """Base class for kf.Pin, kf.DPin."""

    yaml_tag: str = "!Pin"
    _base: BasePin

    def __init__(self, *, base: BasePin) -> None:
        self._base = base

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
    def kcl(self) -> KCLayout:
        """KCLayout associated to the pin."""
        return self._base.kcl

    @kcl.setter
    def kcl(self, value: KCLayout) -> None:
        self._base.kcl = value

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
    def ports(self) -> set[BasePort]:
        return self._base.ports

    @ports.setter
    def ports(self, value: Iterable[BasePort]) -> None:
        self._base.ports = set(value)

    def to_itype(self) -> Pin:
        """Convert the pin to a dbu pin."""
        return Pin(base=self._base)

    def to_dtype(self) -> DPin:
        """Convert the pin to a um pin."""
        return DPin(base=self._base)

    def __repr__(self) -> str:
        """String representation of pin."""
        return (
            f"{self.__class__.__name__}({self.name},"
            f"ports={self.ports}, pin_type={self.pin_type})"
        )

    @abstractmethod
    def __getitem__(self, key: int | str | None) -> ProtoPort[TUnit]:
        """Get a port in the pin by index or name."""
        ...


class Pin(ProtoPin[int]):
    def __getitem__(self, key: int | str | None) -> Port:
        if isinstance(key, int):
            return Port(base=list(self.ports)[key])
        try:
            return Port(
                base=next(filter(lambda port_base: port_base.name == key, self.ports))
            )
        except StopIteration as e:
            raise KeyError(
                f"{key=} is not a valid port name or index within the pin. "
                f"Available ports: {[v.name for v in self.ports]}"
            ) from e


class DPin(ProtoPin[float]):
    def __getitem__(self, key: int | str | None) -> DPort:
        if isinstance(key, int):
            return DPort(base=list(self.ports)[key])
        try:
            return DPort(
                base=next(filter(lambda port_base: port_base.name == key, self.ports))
            )
        except StopIteration as e:
            raise KeyError(
                f"{key=} is not a valid port name or index within the pin. "
                f"Available ports: {[v.name for v in self.ports]}"
            ) from e

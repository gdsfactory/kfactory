from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Generic

from pydantic import BaseModel
from typing_extensions import TypedDict

from .settings import Info
from .typings import TUnit

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .port import BasePort


class BasePinDict(TypedDict):
    name: str | None
    ports: set[BasePort]
    info: Info
    pin_type: str


class BasePin(BaseModel, arbitrary_types_allowed=True):
    name: str | None
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
    def ports(self) -> list[BasePort]:
        return list(self._base.ports)

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


class Pin(ProtoPin[int]): ...


class DPin(ProtoPin[float]): ...

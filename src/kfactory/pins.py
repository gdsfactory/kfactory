from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Protocol

from .conf import config
from .pin import BasePin, DPin, Pin, ProtoPin, filter_type_reg
from .settings import Info
from .typings import TUnit
from .utilities import pprint_pins

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence

    from .layout import KCLayout
    from .port import ProtoPort

__all__ = ["DPins", "Pins", "ProtoPins"]


class ProtoPins(Protocol[TUnit]):
    _kcl: KCLayout
    _bases: list[BasePin]

    def __init__(
        self,
        *,
        kcl: KCLayout,
        bases: list[BasePin],
    ) -> None:
        self._kcl = kcl
        self._bases = bases

    def __len__(self) -> int:
        """Return Pin count."""
        return len(self._bases)

    @property
    def kcl(self) -> KCLayout:
        """KCLayout associated to the pins."""
        return self._kcl

    @kcl.setter
    def kcl(self, value: KCLayout) -> None:
        self._kcl = value

    @property
    def bases(self) -> list[BasePin]:
        """Get the bases."""
        return self._bases

    def to_itype(self) -> Pins:
        """Convert to a Ports."""
        return Pins(kcl=self.kcl, bases=self._bases)

    def to_dtype(self) -> DPins:
        """Convert to a DPins."""
        return DPins(kcl=self.kcl, bases=self._bases)

    @abstractmethod
    def __iter__(self) -> Iterator[ProtoPin[TUnit]]:
        """Iterator over the Pins."""
        ...

    @abstractmethod
    def __getitem__(self, key: int | str | None) -> ProtoPin[TUnit]:
        """Get a pin by index or name."""
        ...

    def __contains__(self, pin: str | ProtoPin[Any] | BasePin) -> bool:
        """Check whether a pin is in this pin collection."""
        if isinstance(pin, ProtoPin):
            return pin.base in self._bases
        if isinstance(pin, BasePin):
            return pin in self._bases
        return any(_pin.name == pin for _pin in self._bases)

    @abstractmethod
    def create_pin(
        self,
        *,
        ports: Iterable[ProtoPort[Any]],
        name: str | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
    ) -> ProtoPin[TUnit]:
        """Add a pin."""
        ...

    @abstractmethod
    def get_all_named(self) -> Mapping[str, ProtoPin[TUnit]]:
        """Get all pins in a dictionary with names as keys.

        This filters out Pins with `None` as name.
        """
        ...

    def filter(
        self,
        pin_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[ProtoPin[TUnit]]:
        """Filter pins by name.

        Args:
            pin_type: Filter by pin type.
            regex: Filter by regex of the name.
        Returns:
            Filtered list of pins.
        """
        pins: Iterable[ProtoPin[TUnit]] = list(self)
        return list(filter_type_reg(pins, pin_type=pin_type, regex=regex))


class Pins(ProtoPins[int]):
    yaml_tag: ClassVar[str] = "!Pins"

    def __iter__(self) -> Iterator[Pin]:
        """Iterator, that allows for loops etc to directly access the object."""
        yield from (Pin(base=b) for b in self._bases)

    def __getitem__(self, key: int | str | None) -> Pin:
        """Get a specific pin by name."""
        if isinstance(key, int):
            return Pin(base=self._bases[key])
        try:
            return Pin(base=next(filter(lambda base: base.name == key, self._bases)))
        except StopIteration as e:
            raise KeyError(
                f"{key=} is not a valid pin name or index. "
                f"Available pins: {[v.name for v in self._bases]}"
            ) from e

    def create_pin(
        self,
        *,
        ports: Iterable[ProtoPort[Any]],
        name: str | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
    ) -> Pin:
        """Add a pin to Pins."""
        if info is None:
            info = {}
        info_ = Info(**info)
        if len(list(ports)) < 1:
            raise ValueError(
                f"At least one port must provided to create pin named {name}."
            )
        port_bases = []
        for port in ports:
            port_base = port.base
            if port.kcl != self.kcl:
                raise ValueError(
                    "Cannot add a pin which belongs to a different layout or cell to a"
                    f" cell. {port=}, {self.kcl!r}"
                )
            port_bases.append(port_base)

        base_ = BasePin(
            name=name, kcl=self.kcl, ports=port_bases, pin_type=pin_type, info=info_
        )
        self._bases.append(base_)

        return Pin(base=base_)

    def get_all_named(self) -> Mapping[str, Pin]:
        """Get all pins in a dictionary with names as keys."""
        return {v.name: Pin(base=v) for v in self._bases if v.name is not None}

    def print(self, unit: Literal["dbu", "um", None] = None) -> None:
        """Pretty print ports."""
        config.console.print(pprint_pins(self, unit=unit))


class DPins(ProtoPins[float]):
    yaml_tag: ClassVar[str] = "!DPins"

    def __iter__(self) -> Iterator[DPin]:
        """Iterator, that allows for loops etc to directly access the object."""
        yield from (DPin(base=b) for b in self._bases)

    def __getitem__(self, key: int | str | None) -> DPin:
        """Get a specific pin by name."""
        if isinstance(key, int):
            return DPin(base=self._bases[key])
        try:
            return DPin(base=next(filter(lambda base: base.name == key, self._bases)))
        except StopIteration as e:
            raise KeyError(
                f"{key=} is not a valid pin name or index. "
                f"Available pins: {[v.name for v in self._bases]}"
            ) from e

    def create_pin(
        self,
        *,
        ports: Iterable[ProtoPort[Any]],
        name: str | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
    ) -> DPin:
        """Add a pin to Pins."""
        if info is None:
            info = {}
        info_ = Info(**info)
        if len(list(ports)) < 1:
            raise ValueError(
                f"At least one port must provided to create pin named {name}."
            )
        port_bases = []
        for port in ports:
            port_base = port.base
            if port.kcl != self.kcl:
                port_base.kcl = self.kcl
            port_bases.append(port_base)

        base_ = BasePin(
            name=name, kcl=self.kcl, ports=port_bases, pin_type=pin_type, info=info_
        )
        self._bases.append(base_)

        return DPin(base=base_)

    def get_all_named(self) -> Mapping[str, DPin]:
        """Get all pins in a dictionary with names as keys."""
        return {v.name: DPin(base=v) for v in self._bases if v.name is not None}

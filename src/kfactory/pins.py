from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from .pin import BasePin, DPin, Pin, ProtoPin
from .settings import Info
from .typings import TUnit

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from .port import ProtoPort


class ProtoPins(Protocol[TUnit]):
    _bases: list[BasePin]

    def __init__(
        self,
        *,
        bases: list[BasePin],
    ) -> None:
        self._bases = bases

    def __len__(self) -> int:
        """Return Pin count."""
        return len(self._bases)

    @property
    def bases(self) -> list[BasePin]:
        """Get the bases."""
        return self._bases

    def to_itype(self) -> Pins:
        """Convert to a Ports."""
        return Pins(bases=self._bases)

    def to_dtype(self) -> DPins:
        """Convert to a DPins."""
        return DPins(bases=self._bases)

    @abstractmethod
    def __iter__(self) -> Iterator[ProtoPin[TUnit]]:
        """Iterator over the Pins."""
        ...

    @abstractmethod
    def __getitem__(self, key: int | str | None) -> ProtoPin[TUnit]:
        """Get a pin by index or name."""
        ...

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
        base_ = BasePin(
            name=name, ports={p.base for p in ports}, pin_type=pin_type, info=info_
        )
        self._bases.append(base_)

        return Pin(base=base_)

    def get_all_named(self) -> Mapping[str, Pin]:
        """Get all pins in a dictionary with names as keys."""
        return {v.name: Pin(base=v) for v in self._bases if v.name is not None}


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
        """Add a pin to DPins."""
        if info is None:
            info = {}
        info_ = Info(**info)
        base_ = BasePin(
            name=name, ports={p.base for p in ports}, pin_type=pin_type, info=info_
        )
        self._bases.append(base_)

        return DPin(base=base_)

    def get_all_named(self) -> Mapping[str, DPin]:
        """Get all pins in a dictionary with names as keys."""
        return {v.name: DPin(base=v) for v in self._bases if v.name is not None}

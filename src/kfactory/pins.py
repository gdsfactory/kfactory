from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Literal, Self, overload

from .conf import config
from .pin import (
    BasePin,
    ProtoPin,
    filter_directions,
    filter_layer,
    filter_orientations,
    filter_pin_type,
    filter_regex,
)
from .utilities import pprint_pins

if TYPE_CHECKING:
    from collections.abc import (
        Callable,
        Iterable,
        Iterator,
        Mapping,
        Sequence,
    )

    from .layer import LayerEnum
    from .layout import KCLayout
    from .typings import TPin, TUnit

__all__ = ["DPins", "Pins", "ProtoPins"]


def _filter_pins(
    pins: Iterable[TPin],
    allowed_angles: list[int] | None = None,
    allowed_orientations: list[float] | None = None,
    layer: LayerEnum | int | None = None,
    pin_type: str | None = None,
    regex: str | None = None,
) -> list[TPin]:
    if regex:
        pins = filter_regex(pins, regex)
    if layer is not None:
        pins = filter_layer(pins, layer)
    if pin_type:
        pins = filter_pin_type(pins, pin_type)
    if allowed_angles is not None:
        pins = filter_directions(pins, allowed_angles)
    if allowed_orientations is not None:
        pins = filter_orientations(pins, allowed_orientations)
    return list(pins)


class ProtoPins:
    """Base class for kf.Pins, kf.DPins."""

    _kcl: KCLayout
    _locked: bool
    _bases: list[BasePin]

    @overload
    def __init__(self, *, kcl: KCLayout) -> None: ...

    @overload
    def __init__(
        self,
        *,
        kcl: KCLayout,
        pins: Iterable[ProtoPin[Any]] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        kcl: KCLayout,
        bases: list[BasePin] | None = None,
    ) -> None: ...

    def __init__(
        self,
        *,
        kcl: KCLayout,
        pins: Iterable[ProtoPin[Any]] | None = None,
        bases: list[BasePin] | None = None,
    ) -> None:
        """Initialize the Pins.

        Args:
            kcl: The KCLayout instance.
            pins: The pins to add.
            bases: The bases to add.
        """
        self.kcl = kcl
        if bases is not None:
            self._bases = bases
        elif pins is not None:
            self._bases = [p.base for p in pins]
        else:
            self._bases = []
        self._locked = False

    def __len__(self) -> int:
        """Return Pin count."""
        return len(self._bases)

    @property
    def bases(self) -> list[BasePin]:
        """Get the bases."""
        return self._bases

    @property
    def kcl(self) -> KCLayout:
        """Get the KCLayout."""
        return self._kcl

    @kcl.setter
    def kcl(self, value: KCLayout) -> None:
        """Set the KCLayout."""
        self._kcl = value

    @abstractmethod
    def copy(
        self,
        rename_function: Callable[[Sequence[ProtoPin[TUnit]]], None] | None = None,
    ) -> Self:
        """Get a copy of each pin."""
        ...

    def to_itype(self) -> Pins:
        """Convert to a Pins."""
        return Pins(kcl=self.kcl, bases=self._bases)

    def to_dtype(self) -> DPins:
        """Convert to a DPins."""
        return DPins(kcl=self.kcl, bases=self._bases)

    @abstractmethod
    def __iter__(self) -> Iterator[ProtoPin[TUnit]]:
        """Iterator over the Pins."""
        ...

    @abstractmethod
    def add_pin(
        self,
        *,
        pin: ProtoPin[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> ProtoPin[TUnit]:
        """Add a pin."""
        ...

    @abstractmethod
    def get_all_named(self) -> Mapping[str, ProtoPin[TUnit]]:
        """Get all pins in a dictionary with names as keys.

        This filters out Pins with `None` as name.
        """
        ...

    def add_pins(
        self,
        pins: Iterable[ProtoPin[Any]],
        prefix: str = "",
        keep_mirror: bool = False,
        suffix: str = "",
    ) -> None:
        """Append a list of pins."""
        for p in pins:
            name = p.name or ""
            self.add_pin(pin=p, name=prefix + name + suffix, keep_mirror=keep_mirror)

    @abstractmethod
    def __getitem__(self, key: int | str | None) -> ProtoPin[TUnit]:
        """Get a pin by index or name."""
        ...

    @abstractmethod
    def filter(
        self,
        allowed_angles: list[int] | None = None,
        allowed_orientations: list[float] | None = None,
        layer: LayerEnum | int | None = None,
        pin_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[ProtoPin[TUnit]]:
        """Filter pins.

        Args:
            allowed_angles: Filter by allowed angles. 0, 1, 2, 3.
            allowed_orientations: Filter by allowed orientations in degrees.
            layer: Filter by layer.
            pin_type: Filter by pin type.
            regex: Filter by regex of the name.
        """
        ...

    def __contains__(self, pin: str | ProtoPin[Any] | BasePin) -> bool:
        """Check whether a pin is in this pin collection."""
        if isinstance(pin, ProtoPin):
            return pin.base in self._bases
        if isinstance(pin, BasePin):
            return pin in self._bases
        return any(_pin.name == pin for _pin in self._bases)

    def clear(self) -> None:
        """Deletes all pins."""
        self._bases.clear()

    def __eq__(self, other: object) -> bool:
        """Support for `pins1 == pins2` comparisons."""
        if isinstance(other, Iterable):
            if len(self._bases) != len(list(other)):
                return False
            return all(b1 == b2 for b1, b2 in zip(iter(self), other, strict=False))
        return False

    def print(self, unit: Literal["dbu", "um", None] = None) -> None:
        """Pretty print pins."""
        config.console.print(pprint_pins(self, unit=unit))

    def pformat(self, unit: Literal["dbu", "um", None] = None) -> str:
        """Pretty print pins."""
        with config.console.capture() as capture:
            config.console.print(pprint_pins(self, unit=unit))
        return str(capture.get())

    def __hash__(self) -> int:
        """Hash the pins."""
        return hash(self._bases)


class Pins: ...


class DPins: ...

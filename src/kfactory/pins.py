from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Protocol, Self, overload

from . import kdb
from .conf import config
from .pin import (
    BasePin,
    DPin,
    Pin,
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


class ProtoPins(Protocol[TUnit]):
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


class ICreatePin(ABC):
    """Protocol for a create_pin functionality"""

    @property
    @abstractmethod
    def kcl(self) -> KCLayout: ...

    @overload
    def create_pin(
        self,
        *,
        width: int | None = None,
        layer: LayerEnum | int | None = None,
        pin_type: str = "DC",
        pos: kdb.Point | None = None,
        allowed_angles: list[int] | None = None,
        name: str | None = None,
    ) -> Pin: ...

    @overload
    def create_pin(
        self,
        *,
        width: int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        pin_type: str = "DC",
        pos: kdb.Point | None = None,
        allowed_angles: list[int] | None = None,
        name: str | None = None,
    ) -> Pin: ...

    def create_pin(
        self,
        *,
        name: str | None = None,
        width: int | None = None,
        layer: LayerEnum | int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        pin_type: str = "optical",
        pos: kdb.Point | None = None,
        allowed_angles: list[int] | None = None,
    ) -> Pin:
        """Create a pin."""

        if width is None:
            raise ValueError("width must be set.")
        if allowed_angles is None:
            raise ValueError("allowed angles must be set.")
        if layer_info is None:
            if layer is None:
                raise ValueError("layer or layer_info must be defined to create a pin.")
            layer_info = self.kcl.layout.get_info(layer)
        assert layer_info is not None
        if pos is None:
            raise ValueError("pos must be set.")
        pin = Pin(
            name=name,
            width=width,
            layer_info=layer_info,
            pin_type=pin_type,
            allowed_angles=allowed_angles,
            pos=pos,
            kcl=self.kcl,
        )

        return self.add_pin(pin=pin)

    @abstractmethod
    def add_pin(
        self,
        *,
        pin: ProtoPin[Any],
        name: str | None = None,
    ) -> Pin: ...


class DCreatePin(ABC):
    """Protocol for a create_pin functionality"""

    @property
    @abstractmethod
    def kcl(self) -> KCLayout: ...

    @overload
    def create_pin(
        self,
        *,
        width: float | None = None,
        layer: LayerEnum | int | None = None,
        pin_type: str = "DC",
        pos: kdb.Point | None = None,
        allowed_orientations: list[float] | None = None,
        name: str | None = None,
    ) -> DPin: ...

    @overload
    def create_pin(
        self,
        *,
        width: float | None = None,
        layer_info: kdb.LayerInfo | None = None,
        pin_type: str = "DC",
        pos: kdb.Point | None = None,
        allowed_orientations: list[float] | None = None,
        name: str | None = None,
    ) -> DPin: ...

    def create_pin(
        self,
        *,
        name: str | None = None,
        width: float | None = None,
        layer: LayerEnum | int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        pin_type: str = "optical",
        pos: kdb.Point | None = None,
        allowed_orientations: list[float] | None = None,
    ) -> DPin:
        """Create a pin."""

        if width is None:
            raise ValueError("width must be set.")
        if allowed_orientations is None:
            raise ValueError("allowed angles must be set.")
        if layer_info is None:
            if layer is None:
                raise ValueError("layer or layer_info must be defined to create a pin.")
            layer_info = self.kcl.layout.get_info(layer)
        assert layer_info is not None
        if pos is None:
            raise ValueError("pos must be set.")
        dpin = DPin(
            name=name,
            width=width,
            layer_info=layer_info,
            pin_type=pin_type,
            allowed_angles=allowed_orientations,
            pos=pos,
            kcl=self.kcl,
        )

        return self.add_pin(pin=dpin)

    @abstractmethod
    def add_pin(
        self,
        *,
        pin: ProtoPin[Any],
        name: str | None = None,
    ) -> DPin: ...


class Pins(ProtoPins[int], ICreatePin):
    """A collection of dbu pins.

    It is not a traditional dictionary. Elements can be retrieved as in a traditional
    dictionary. But to keep tabs on names etc, the pins are stored as a list
    """

    yaml_tag: ClassVar[str] = "!Pins"

    def __iter__(self) -> Iterator[Pin]:
        """Iterator, that allows for loops etc to directly access the object."""
        yield from (Pin(base=b) for b in self._bases)

    def add_pin(
        self,
        *,
        pin: ProtoPin[Any],
        name: str | None = None,
    ) -> Pin:
        """Add a pin object.

        Args:
            pin: The pin to add
            name: Overwrite the name of the pin
        """
        base = pin.base.model_copy()
        if name is not None:
            base.name = name
        if pin.kcl != self.kcl:
            base.kcl = self.kcl
        self._bases.append(base)

        return Pin(base=base)

    def get_all_named(self) -> Mapping[str, Pin]:
        """Get all pins in a dictionary with names as keys."""
        return {v.name: Pin(base=v) for v in self._bases if v.name is not None}

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

    def copy(
        self, rename_function: Callable[[Sequence[Pin]], None] | None = None
    ) -> Self:
        """Get a copy of each pin."""
        bases = [b.__copy__() for b in self._bases]
        if rename_function is not None:
            rename_function([Pin(base=b) for b in bases])
        return self.__class__(bases=bases, kcl=self.kcl)

    def filter(
        self,
        allowed_angles: list[int] | None = None,
        allowed_orientations: list[float] | None = None,
        layer: LayerEnum | int | None = None,
        pin_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[Pin]:
        """Filter pins.

        Args:
            allowed_angles: Filter by allowed angles. 0, 1, 2, 3.
            allowed_orientations: Filter by allowed orientations in degrees.
            layer: Filter by layer.
            pin_type: Filter by pin type.
            regex: Filter by regex of the name.
        """
        return _filter_pins(
            (Pin(base=b) for b in self._bases),
            allowed_angles,
            allowed_orientations,
            layer,
            pin_type,
            regex,
        )

    def __repr__(self) -> str:
        """Representation of the Pins as strings."""
        return repr([repr(Pin(base=b)) for b in self._bases])


class DPins(ProtoPins[float], DCreatePin):
    """A collection of um pins.

    It is not a traditional dictionary. Elements can be retrieved as in a traditional
    dictionary. But to keep tabs on names etc, the pins are stored as a list
    """

    yaml_tag: ClassVar[str] = "!DPins"

    def __iter__(self) -> Iterator[DPin]:
        """Iterator, that allows for loops etc to directly access the object."""
        yield from (DPin(base=b) for b in self._bases)

    def add_pin(
        self,
        *,
        pin: ProtoPin[Any],
        name: str | None = None,
    ) -> DPin:
        """Add a pin object.

        Args:
            pin: The pin to add
            name: Overwrite the name of the pin
        """
        base = pin.base.model_copy()
        if name is not None:
            base.name = name
        if pin.kcl != self.kcl:
            base.kcl = self.kcl
        self._bases.append(base)

        return DPin(base=base)

    def get_all_named(self) -> Mapping[str, DPin]:
        """Get all pins in a dictionary with names as keys."""
        return {v.name: DPin(base=v) for v in self._bases if v.name is not None}

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

    def copy(
        self, rename_function: Callable[[Sequence[DPin]], None] | None = None
    ) -> Self:
        """Get a copy of each pin."""
        bases = [b.__copy__() for b in self._bases]
        if rename_function is not None:
            rename_function([DPin(base=b) for b in bases])
        return self.__class__(bases=bases, kcl=self.kcl)

    def filter(
        self,
        allowed_angles: list[int] | None = None,
        allowed_orientations: list[float] | None = None,
        layer: LayerEnum | int | None = None,
        pin_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[DPin]:
        """Filter pins by name.

        Args:
            allowed_angles: Filter by allowed angles. 0, 1, 2, 3.
            allowed_orientations: Filter by allowed orientations in degrees.
            layer: Filter by layer.
            pin_type: Filter by pin type.
            regex: Filter by regex of the name.
        """
        return _filter_pins(
            (DPin(base=b) for b in self._bases),
            allowed_angles,
            allowed_orientations,
            layer,
            pin_type,
            regex,
        )

    def __repr__(self) -> str:
        """Representation of the Pins as strings."""
        return repr([repr(Pin(base=b)) for b in self._bases])

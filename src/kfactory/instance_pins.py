from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Literal, cast

from . import kdb
from .conf import config
from .instance import DInstance, Instance, ProtoTInstance, VInstance
from .pin import BasePin, DPin, Pin, ProtoPin, filter_type_reg
from .pins import DPins, Pins, ProtoPins
from .typings import TInstance_co, TUnit
from .utilities import pprint_pins

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence


class HasCellPins(ABC, Generic[TUnit]):
    @property
    @abstractmethod
    def cell_pins(self) -> ProtoPins[TUnit]: ...


class ProtoInstancePins(HasCellPins[TUnit], ABC, Generic[TUnit, TInstance_co]):
    instance: TInstance_co

    @abstractmethod
    def __len__(self) -> int: ...

    @abstractmethod
    def __contains__(self, pin: str | ProtoPin[Any]) -> bool: ...

    @abstractmethod
    def __getitem__(self, key: int | str | None) -> ProtoPin[TUnit]: ...

    @abstractmethod
    def __iter__(self) -> Iterator[ProtoPin[TUnit]]: ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(n={len(self)})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(pins={list(self)})"


class ProtoTInstancePins(
    ProtoInstancePins[TUnit, ProtoTInstance[TUnit]], ABC, Generic[TUnit]
):
    """Pins of an Instance.

    These act as virtual pins as the centers needs to change if the
    instance changes etc.


    Attributes:
        cell_pins: A pointer to the [`KCell.pins`][kfactory.kcell.KCell.pins]
            of the cell
        instance: A pointer to the Instance related to this.
            This provides a way to dynamically calculate the pins.
    """

    instance: ProtoTInstance[TUnit]

    def __len__(self) -> int:
        """Return Pin count."""
        if not self.instance.instance.is_regular_array():
            return len(self.cell_pins)
        return len(self.cell_pins) * self.instance.na * self.instance.nb

    def __contains__(self, pin: str | ProtoPin[Any]) -> bool:
        """Check whether a pin is in this pin collection."""
        if isinstance(pin, ProtoPin):
            return pin.base in [p.base for p in self.instance.pins]
        return any(_pin.name == pin for _pin in self.instance.pins)

    @property
    def pins(self) -> ProtoTInstancePins[TUnit]:
        return self.instance.pins

    @property
    def bases(self) -> list[BasePin]:
        return [p.base for p in self.instance.pins]

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

    def __getitem__(
        self, key: int | str | tuple[int | str | None, int, int] | None
    ) -> ProtoPin[TUnit]:
        """Returns pin from instance.

        The key can either be an integer, in which case the nth pin is
        returned, or a string in which case the first pin with a matching
        name is returned.

        If the instance is an array, the key can also be a tuple in the
        form of `c.pins[key_name, i_a, i_b]`, where `i_a` is the index in
        the `instance.a` direction and `i_b` the `instance.b` direction.

        E.g. `c.pins["a", 3, 5]`, accesses the pins of the instance which is
        3 times in `a` direction (4th index in the array), and 5 times in `b` direction
        (5th index in the array).

        Raises:
            IndexError: If the pin is an array pin and the index is out of range.
            KeyError: If the pin name does not exist.

        Returns:
            Pin from instance by name or name and array index.
        """
        if not self.instance.is_regular_array():
            try:
                p = self.cell_pins[cast("int | str | None", key)]
                if not self.instance.is_complex():
                    return p.copy(self.instance.trans)
                return p.copy(self.instance.dcplx_trans)
            except KeyError as e:
                raise KeyError(
                    f"{key=} is not a valid pin name or index. "
                    "Make sure the instance is an array when giving it a tuple. "
                    f"Available pins: {[v.name for v in self.cell_pins]}"
                ) from e
        else:
            if isinstance(key, tuple):
                key, i_a, i_b = key
                if i_a >= self.instance.na or i_b >= self.instance.nb:
                    raise IndexError(
                        f"The indexes {i_a=} and {i_b=} must be within the array size"
                        f" instance.na={self.instance.na} and"
                        f" instance.nb={self.instance.nb}"
                    )
            else:
                i_a = 0
                i_b = 0
            p = self.cell_pins[key]
            if not self.instance.is_complex():
                return p.copy(
                    kdb.Trans(self.instance.a * i_a + self.instance.b * i_b)
                    * self.instance.trans
                )
            return p.copy(
                kdb.DCplxTrans(self.instance.da * i_a + self.instance.db * i_b)
                * self.instance.dcplx_trans
            )

    @property
    @abstractmethod
    def cell_pins(self) -> ProtoPins[TUnit]: ...

    def each_pin(self) -> Iterator[ProtoPin[TUnit]]:
        """Create a copy of the pins to iterate through."""
        if not self.instance.is_regular_array():
            if not self.instance.is_complex():
                yield from (p.copy(self.instance.trans) for p in self.cell_pins)
            else:
                yield from (p.copy(self.instance.dcplx_trans) for p in self.cell_pins)
        elif not self.instance.is_complex():
            yield from (
                p.copy(
                    kdb.Trans(self.instance.a * i_a + self.instance.b * i_b)
                    * self.instance.trans
                )
                for i_a in range(self.instance.na)
                for i_b in range(self.instance.nb)
                for p in self.cell_pins
            )
        else:
            yield from (
                p.copy(
                    kdb.DCplxTrans(self.instance.da * i_a + self.instance.db * i_b)
                    * self.instance.dcplx_trans
                )
                for i_a in range(self.instance.na)
                for i_b in range(self.instance.nb)
                for p in self.cell_pins
            )

    @abstractmethod
    def __iter__(self) -> Iterator[ProtoPin[TUnit]]: ...

    def each_by_array_coord(self) -> Iterator[tuple[int, int, ProtoPin[TUnit]]]:
        if not self.instance.is_regular_array():
            if not self.instance.is_complex():
                yield from ((0, 0, p.copy(self.instance.trans)) for p in self.cell_pins)
            else:
                yield from (
                    (0, 0, p.copy(self.instance.dcplx_trans)) for p in self.cell_pins
                )
        elif not self.instance.is_complex():
            yield from (
                (
                    i_a,
                    i_b,
                    p.copy(
                        kdb.Trans(self.instance.a * i_a + self.instance.b * i_b)
                        * self.instance.trans
                    ),
                )
                for i_a in range(self.instance.na)
                for i_b in range(self.instance.nb)
                for p in self.cell_pins
            )
        else:
            yield from (
                (
                    i_a,
                    i_b,
                    p.copy(
                        kdb.DCplxTrans(self.instance.da * i_a + self.instance.db * i_b)
                        * self.instance.dcplx_trans
                    ),
                )
                for i_a in range(self.instance.na)
                for i_b in range(self.instance.nb)
                for p in self.cell_pins
            )

    def print(self, unit: Literal["dbu", "um", None] = None) -> None:
        config.console.print(pprint_pins(self.copy(), unit=unit))

    def copy(self, rename_function: Callable[[list[Pin]], None] | None = None) -> Pins:
        """Creates a copy in the form of [Pins][kfactory.kcell.Pins]."""
        if not self.instance.is_regular_array():
            if not self.instance.is_complex():
                return Pins(
                    kcl=self.instance.kcl,
                    bases=[
                        b.transformed(trans=self.instance.trans)
                        for b in self.cell_pins.bases
                    ],
                )
            return Pins(
                kcl=self.instance.kcl,
                bases=[
                    b.transformed(trans=self.instance.dcplx_trans)
                    for b in self.cell_pins.bases
                ],
            )
        if not self.instance.is_complex():
            return Pins(
                kcl=self.instance.kcl,
                bases=[
                    b.transformed(
                        self.instance.trans
                        * kdb.Trans(self.instance.a * i_a + self.instance.b * i_b)
                    )
                    for i_a in range(self.instance.na)
                    for i_b in range(self.instance.nb)
                    for b in self.cell_pins.bases
                ],
            )
        return Pins(
            kcl=self.instance.kcl,
            bases=[
                b.transformed(
                    self.instance.dcplx_trans
                    * kdb.DCplxTrans(self.instance.db * i_a + self.instance.db * i_b)
                )
                for i_a in range(self.instance.na)
                for i_b in range(self.instance.nb)
                for b in self.cell_pins.bases
            ],
        )


class InstancePins(ProtoTInstancePins[int]):
    def __init__(self, instance: Instance) -> None:
        """Creates the virtual pins object.

        Args:
            instance: The related instance
        """
        self.instance = instance

    @property
    def cell_pins(self) -> Pins:
        return Pins(kcl=self.instance.cell.kcl, bases=self.instance.cell.pins.bases)

    def filter(
        self,
        pin_type: str | None = None,
        regex: str | None = None,
    ) -> list[Pin]:
        """Filter pins by name.

        Args:
            pin_type: Filter by pin type.
            regex: Filter by regex of the name.
        Returns:
            Filtered list of pins.
        """
        pins: Iterable[Pin] = list(self)
        return list(filter_type_reg(pins, pin_type=pin_type, regex=regex))

    def __getitem__(
        self, key: int | str | tuple[int | str | None, int, int] | None
    ) -> Pin:
        return Pin(base=super().__getitem__(key).base)

    def __iter__(self) -> Iterator[Pin]:
        yield from (p.to_itype() for p in self.each_pin())


class DInstancePins(ProtoTInstancePins[float]):
    def __init__(self, instance: DInstance) -> None:
        """Creates the virtual pins object.

        Args:
            instance: The related instance
        """
        self.instance = instance

    @property
    def cell_pins(self) -> DPins:
        return DPins(kcl=self.instance.cell.kcl, bases=self.instance.cell.pins.bases)

    def filter(
        self,
        pin_type: str | None = None,
        regex: str | None = None,
    ) -> list[DPin]:
        """Filter pins by name.

        Args:
            pin_type: Filter by pin type.
            regex: Filter by regex of the name.
        Returns:
            Filtered list of pins.
        """
        pins: Iterable[DPin] = list(self)
        return list(filter_type_reg(pins, pin_type=pin_type, regex=regex))

    def __getitem__(
        self, key: int | str | tuple[int | str | None, int, int] | None
    ) -> DPin:
        return DPin(base=super().__getitem__(key).base)

    def __iter__(self) -> Iterator[DPin]:
        yield from (p.to_dtype() for p in self.each_pin())


class VInstancePins(ProtoInstancePins[float, VInstance]):
    """Pins of an instance.

    These act as virtual pins as the centers needs to change if the
    instance changes etc.


    Attributes:
        cell_pins: A pointer to the [`KCell.pins`][kfactory.kcell.KCell.pins]
            of the cell
        instance: A pointer to the Instance related to this.
            This provides a way to dynamically calculate the pins.
    """

    instance: VInstance

    def __init__(self, instance: VInstance) -> None:
        """Creates the virtual pins object.

        Args:
            instance: The related instance
        """
        self.instance = instance

    @property
    def cell_pins(self) -> DPins:
        return DPins(kcl=self.instance.cell.kcl, bases=self.instance.cell.pins.bases)

    def __len__(self) -> int:
        """Return Pin count."""
        return len(self.cell_pins)

    def __getitem__(self, key: int | str | None) -> DPin:
        """Get a pin by name."""
        p = self.cell_pins[key]
        return p.copy(self.instance.trans)

    def __iter__(self) -> Iterator[DPin]:
        """Create a copy of the pins to iterate through."""
        yield from (p.copy(self.instance.trans) for p in self.cell_pins)

    def __contains__(self, pin: str | ProtoPin[Any]) -> bool:
        """Check if a pin is in the instance."""
        if isinstance(pin, ProtoPin):
            return pin.base in [p.base for p in self.instance.pins]
        return any(_pin.name == pin for _pin in self.instance.pins)

    def filter(
        self,
        pin_type: str | None = None,
        regex: str | None = None,
    ) -> list[DPin]:
        """Filter pins by name.

        Args:
            pin_type: Filter by pin type.
            regex: Filter by regex of the name.
        Returns:
            Filtered list of pins.
        """
        pins: Iterable[DPin] = list(self)
        return list(filter_type_reg(pins, pin_type=pin_type, regex=regex))

    def copy(self) -> DPins:
        """Creates a copy in the form of [Pins][kfactory.kcell.Pins]."""
        return DPins(
            kcl=self.instance.cell.kcl,
            bases=[b.transformed(self.instance.trans) for b in self.cell_pins.bases],
        )

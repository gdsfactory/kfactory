from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic

import klayout.db as kdb

from .conf import PROPID
from .instance import (
    DInstance,
    Instance,
    ProtoInstance,
    ProtoTInstance,
    VInstance,
)
from .typings import TInstance_co, TUnit

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .kcell import TKCell

__all__ = [
    "DInstances",
    "Instances",
    "ProtoInstances",
    "ProtoTInstances",
    "VInstances",
]


class ProtoInstances(Generic[TUnit, TInstance_co], ABC):
    @abstractmethod
    def __iter__(self) -> Iterator[ProtoInstance[TUnit]]: ...

    @abstractmethod
    def __len__(self) -> int: ...

    @abstractmethod
    def __delitem__(self, item: TInstance_co | int) -> None: ...

    @abstractmethod
    def __getitem__(self, key: str | int) -> ProtoInstance[TUnit]: ...

    @abstractmethod
    def __contains__(self, key: str | int | TInstance_co) -> bool: ...

    @abstractmethod
    def clear(self) -> None: ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(n={len(self)})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(insts={list(self)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProtoInstances):
            return False
        return list(self) == list(other)


class ProtoTInstances(ProtoInstances[TUnit, ProtoTInstance[TUnit]], ABC):
    _tkcell: TKCell

    def __init__(self, cell: TKCell) -> None:
        """Constructor."""
        self._tkcell = cell

    @abstractmethod
    def __iter__(self) -> Iterator[ProtoTInstance[TUnit]]: ...

    def __len__(self) -> int:
        """Length of the instances."""
        return self._tkcell.kdb_cell.child_instances()

    @property
    def _insts(self) -> Iterator[kdb.Instance]:
        yield from self._tkcell.kdb_cell.each_inst()

    def _get_inst(self, item: kdb.Instance | str) -> kdb.Instance:
        try:
            if isinstance(item, kdb.Instance):
                return next(filter(lambda inst: inst == item, self._insts))
            return next(
                filter(lambda inst: inst.property(PROPID.NAME) == item, self._insts)
            )
        except StopIteration as e:
            raise ValueError(f"Instance {item} not found in {self._tkcell}") from e

    def __delitem__(self, item: ProtoTInstance[Any] | int) -> None:
        if isinstance(item, int):
            list(self._insts)[item].delete()
        else:
            self._get_inst(item.instance).delete()

    def __contains__(self, key: str | int | ProtoTInstance[Any]) -> bool:
        try:
            if isinstance(key, ProtoTInstance):
                self._get_inst(key.instance)
                return True
            if isinstance(key, str):
                self._get_inst(key)
                return True
            return key < len(self)
        except ValueError:
            return False

    @abstractmethod
    def __getitem__(self, key: str | int) -> ProtoTInstance[TUnit]: ...

    def clear(self) -> None:
        for inst in self._insts:
            inst.delete()

    def append(self, inst: ProtoTInstance[Any]) -> None:
        """Append a new instance."""
        self._tkcell.kdb_cell.insert(inst.instance)

    def remove(self, inst: ProtoTInstance[Any]) -> None:
        inst.instance.delete()

    def to_itype(self) -> Instances:
        return Instances(cell=self._tkcell)

    def to_dtype(self) -> DInstances:
        return DInstances(cell=self._tkcell)


class Instances(ProtoTInstances[int]):
    """Holder for instances.

    Allows retrieval by name or index
    """

    def __iter__(self) -> Iterator[Instance]:
        """Get instance iterator."""
        yield from (
            Instance(kcl=self._tkcell.kcl, instance=inst) for inst in self._insts
        )

    def __getitem__(self, key: str | int) -> Instance:
        """Retrieve instance by index or by name."""
        if isinstance(key, int):
            return Instance(kcl=self._tkcell.kcl, instance=list(self._insts)[key])
        return Instance(kcl=self._tkcell.kcl, instance=self._get_inst(key))


class DInstances(ProtoTInstances[float]):
    """Holder for instances.

    Allows retrieval by name or index
    """

    def __iter__(self) -> Iterator[DInstance]:
        """Get instance iterator."""
        yield from (
            DInstance(kcl=self._tkcell.kcl, instance=inst) for inst in self._insts
        )

    def __getitem__(self, key: str | int) -> DInstance:
        """Retrieve instance by index or by name."""
        if isinstance(key, int):
            return DInstance(kcl=self._tkcell.kcl, instance=list(self._insts)[key])
        return DInstance(kcl=self._tkcell.kcl, instance=self._get_inst(key))


class VInstances(ProtoInstances[float, VInstance]):
    """Holder for VInstances.

    Allows retrieval by name or index
    """

    _vinsts: list[VInstance]

    def __init__(self, vinsts: list[VInstance] | None = None) -> None:
        self._vinsts = vinsts or []

    def __iter__(self) -> Iterator[VInstance]:
        """Get instance iterator."""
        yield from self._vinsts

    def __len__(self) -> int:
        """Get the number of instances."""
        return len(self._vinsts)

    def __delitem__(self, item: VInstance | int) -> None:
        """Delete an instance by index or instance."""
        if isinstance(item, int):
            del self._vinsts[item]
        else:
            self._vinsts.remove(item)

    def __getitem__(self, key: str | int) -> VInstance:
        """Retrieve instance by index or by name."""
        if isinstance(key, int):
            return self._vinsts[key]
        for inst in self._vinsts:
            if inst.name == key:
                return inst
        raise KeyError(f"No instance found with name: {key}")

    def __contains__(self, key: str | int | VInstance) -> bool:
        if isinstance(key, VInstance):
            return key in self._vinsts
        if isinstance(key, int):
            return key < len(self)
        return any(inst.name == key for inst in self._vinsts)

    def clear(self) -> None:
        """Clear all instances."""
        self._vinsts.clear()

    def append(self, inst: VInstance) -> None:
        """Append a new instance."""
        self._vinsts.append(inst)

    def remove(self, inst: VInstance) -> None:
        """Remove an instance."""
        self._vinsts.remove(inst)

    def copy(self) -> VInstances:
        """Copy the instances."""
        return VInstances(self._vinsts)

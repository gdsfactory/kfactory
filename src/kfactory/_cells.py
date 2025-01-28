import inspect
from abc import ABC, abstractmethod
from collections import UserDict, defaultdict
from collections.abc import (
    Callable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    ValuesView,
)
from types import ModuleType
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from kfactory.kcell import DKCell, KCell
    from kfactory.layout import KCLayout
    from kfactory.typings import KC

T = TypeVar("T")


class Factories(UserDict[str, Callable[..., T]]):
    tags: dict[str, list[Callable[..., T]]]

    def __init__(self, data: dict[str, Callable[..., T]]) -> None:
        super().__init__(data)
        self.tags = defaultdict(list)

    def __getattr__(self, name: str) -> Any:
        if name != "data":
            return self.data[name]
        else:
            self.__getattribute__(name)

    def for_tags(self, tags: list[str]) -> list[Callable[..., T]]:
        if len(tags) > 0:
            tag_set = set(self.tags[tags[0]])
            for tag in tags[1:]:
                tag_set &= set(self.tags[tag])
            return list(tag_set)
        raise NotImplementedError()


class ProtoCells(Mapping[int, KC], ABC):
    _kcl: KCLayout

    def __init__(self, kcl: KCLayout) -> None:
        self._kcl = kcl

    @abstractmethod
    def __getitem__(self, key: int | str) -> KC: ...

    def __delitem__(self, key: int | str) -> None:
        """Delete a cell by key (name or index)."""
        if isinstance(key, int):
            del self._kcl.tkcells[key]
        else:
            cell_index = self._kcl[key].cell_index()
            del self._kcl.tkcells[cell_index]

    @abstractmethod
    def _generate_dict(self) -> dict[int, KC]: ...

    def __iter__(self) -> Iterator[int]:
        return iter(self._kcl.tkcells)

    def __len__(self) -> int:
        return len(self._kcl.tkcells)

    def items(self) -> ItemsView[int, KC]:
        return self._generate_dict().items()

    def values(self) -> ValuesView[KC]:
        return self._generate_dict().values()

    def keys(self) -> KeysView[int]:
        return self._generate_dict().keys()

    def __contains__(self, key: object) -> bool:
        if isinstance(key, int | str):
            return key in self._kcl.tkcells
        return False


class DKCells(ProtoCells[DKCell]):
    def __getitem__(self, key: int | str) -> DKCell:
        return DKCell(base_kcell=self._kcl[key].base_kcell)

    def _generate_dict(self) -> dict[int, DKCell]:
        return {
            i: DKCell(base_kcell=self._kcl[i].base_kcell) for i in self._kcl.tkcells
        }


class KCells(ProtoCells[KCell]):
    def __getitem__(self, key: int | str) -> KCell:
        return KCell(base_kcell=self._kcl[key].base_kcell)

    def _generate_dict(self) -> dict[int, KCell]:
        return {i: KCell(base_kcell=self._kcl[i].base_kcell) for i in self._kcl.tkcells}


def get_cells(
    modules: Iterable[ModuleType], verbose: bool = False
) -> dict[str, Callable[..., KCell]]:
    """Returns KCells (KCell functions) from a module or list of modules.

    Args:
        modules: module or iterable of modules.
        verbose: prints in case any errors occur.
    """
    cells: dict[str, Callable[..., KCell]] = {}
    for module in modules:
        for t in inspect.getmembers(module):
            if callable(t[1]) and t[0] != "partial":
                try:
                    r = inspect.signature(t[1]).return_annotation
                    if r == KCell or (isinstance(r, str) and r.endswith("KCell")):
                        cells[t[0]] = t[1]
                except ValueError:
                    if verbose:
                        print(f"error in {t[0]}")
    return cells

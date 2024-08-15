from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import cached_property
from typing import TYPE_CHECKING, Protocol, TypedDict, overload

from typing_extensions import Unpack

if TYPE_CHECKING:
    from .kcell import (
        CHECK_INSTANCES,
        KC,
        KCell,
        KCellDecorator,
        KCellFunc,
        KCellParams,
        KCLayout,
        MetaData,
    )

    class ModuleCellKWargs(TypedDict, total=False):
        set_settings: bool
        set_name: bool
        check_ports: bool
        check_instances: CHECK_INSTANCES | None
        snap_ports: bool
        drop_params: list[str]
        register_factory: bool
        overwrite_existing: bool | None
        layout_cache: bool | None
        info: dict[str, MetaData] | None
        post_process: Iterable[Callable[[KCell], None]]
        debug_names: bool | None

    class ModuleCell(Protocol):
        @overload
        def __call__(
            self, _func: KCellFunc[KCellParams, KC], /
        ) -> KCellFunc[KCellParams, KC]: ...

        @overload
        def __call__(
            self,
            **kwargs: Unpack[ModuleCellKWargs],
        ) -> Callable[[KCellFunc[KCellParams, KC]], KCellFunc[KCellParams, KC]]: ...

        def __call__(
            self,
            _func: KCellFunc[KCellParams, KC] | None = None,
            /,
            **kwargs: Unpack[ModuleCellKWargs],
        ) -> (
            Callable[[KCellFunc[KCellParams, KC]], KCellFunc[KCellParams, KC]]
            | KCellFunc[KCellParams, KC]
        ): ...


def _module_cell(
    cell_decorator: KCellDecorator,
    **kwargs: Unpack[ModuleCellKWargs],
) -> Callable[[KCellFunc[KCellParams, KC]], KCellFunc[KCellParams, KC]]:
    def decorator_cell(
        f: Callable[KCellParams, KC],
    ) -> Callable[KCellParams, KC]:
        mod = f.__module__
        if mod != "__main__":
            basename = mod + "_" + f.__name__
        else:
            basename = f.__name__

        return cell_decorator(basename=basename, **kwargs)(f)

    return decorator_cell


class Decorators:
    def __init__(self, kcl: KCLayout):
        self._cell = kcl.cell

    @cached_property
    def module_cell(
        self,
    ) -> ModuleCell:
        def mc(
            _func: KCellFunc[KCellParams, KC] | None = None,
            /,
            **kwargs: Unpack[ModuleCellKWargs],
        ) -> ModuleCell:
            if _func is None:
                return _module_cell(self._cell, **kwargs)
            return _module_cell(self._cell)(_func)

        return mc

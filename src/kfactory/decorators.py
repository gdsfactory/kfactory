"""Defines additional decorators than just `@cell`."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, overload

from typing_extensions import Unpack

if TYPE_CHECKING:
    from cachetools import Cache

    from .kcell import (
        CHECK_INSTANCES,
        KC,
        KCell,
        KCellFunc,
        KCellParams,
        KCLayout,
        MetaData,
    )


class ModuleCellKWargs(TypedDict, total=False):
    """KWargs for `@module_cell`."""

    set_settings: bool
    set_name: bool
    check_ports: bool
    check_instances: CHECK_INSTANCES | None
    snap_ports: bool
    add_port_layers: bool
    cache: Cache[int, Any] | dict[int, Any] | None
    drop_params: list[str]
    register_factory: bool
    overwrite_existing: bool | None
    layout_cache: bool | None
    info: dict[str, MetaData] | None
    post_process: Iterable[Callable[[KCell], None]]
    debug_names: bool | None


class KCellDecoratorKWargs(TypedDict, total=False):
    """KWargs for `@cell`."""

    set_settings: bool
    set_name: bool
    check_ports: bool
    check_instances: CHECK_INSTANCES | None
    snap_ports: bool
    add_port_layers: bool
    cache: Cache[int, Any] | dict[int, Any] | None
    basename: str | None
    drop_params: list[str]
    register_factory: bool
    overwrite_existing: bool | None
    layout_cache: bool | None
    info: dict[str, MetaData] | None
    post_process: Iterable[Callable[[KC], None]]
    debug_names: bool | None


class KCellDecorator(Protocol):
    """Signature of the `@cell` decorator."""

    def __call__(
        self, **kwargs: Unpack[KCellDecoratorKWargs]
    ) -> Callable[[KCellFunc[KCellParams, KC]], KCellFunc[KCellParams, KC]]:
        """__call__ implementation."""


class ModuleDecorator(Protocol):
    """Signature of the `@module_cell` decorator."""

    def __call__(
        self, /, **kwargs: Unpack[ModuleCellKWargs]
    ) -> Callable[[KCellFunc[KCellParams, KC]], KCellFunc[KCellParams, KC]]:
        """__call__ implementation."""


def _module_cell(
    cell_decorator: KCellDecorator,
    /,
    **kwargs: Unpack[ModuleCellKWargs],
) -> Callable[[KCellFunc[KCellParams, KC]], KCellFunc[KCellParams, KC]]:
    """Constructs the actual decorator.

    Modifies the basename to the module if the module is not the main one.
    """

    def decorator_cell(
        f: KCellFunc[KCellParams, KC],
    ) -> KCellFunc[KCellParams, KC]:
        mod = f.__module__
        basename = f.__name__ if mod == "__main" else f"{mod}_{f.__name__}"
        return cell_decorator(basename=basename, **kwargs)(f)

    return decorator_cell


class Decorators:
    """Various decorators intended to be attached to a KCLayout."""

    def __init__(self, kcl: KCLayout):
        """Just set the standard `@cell` decorator."""
        self._cell = kcl.cell

    @overload
    def module_cell(
        self,
        _func: KCellFunc[KCellParams, KC],
        /,
    ) -> KCellFunc[KCellParams, KC]: ...

    @overload
    def module_cell(
        self, /, **kwargs: Unpack[ModuleCellKWargs]
    ) -> Callable[[KCellFunc[KCellParams, KC]], KCellFunc[KCellParams, KC]]: ...

    def module_cell(  # type: ignore[misc]
        self,
        _func: KCellFunc[KCellParams, KC] | None = None,
        /,
        **kwargs: Unpack[ModuleCellKWargs],
    ) -> (
        KCellFunc[KCellParams, KC]
        | Callable[[KCellFunc[KCellParams, KC]], KCellFunc[KCellParams, KC]]
    ):
        """Constructs the `@module_cell` decorator on KCLayout.decorators."""

        def mc(
            **kwargs: Unpack[ModuleCellKWargs],
        ) -> Callable[[KCellFunc[KCellParams, KC]], KCellFunc[KCellParams, KC]]:
            return _module_cell(self._cell, **kwargs)  # type: ignore[arg-type]

        return mc(**kwargs) if _func is None else mc(**kwargs)(_func)

"""Defines additional decorators than just `@cell`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypedDict, overload

from typing_extensions import Unpack

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from cachetools import Cache

    from .conf import CheckInstances
    from .kcell import TKCell
    from .layout import KCLayout
    from .protocols import KCellFunc
    from .typings import KC_co, KCellParams, MetaData


class ModuleCellKWargs(TypedDict, total=False):
    """KWargs for `@module_cell`."""

    set_settings: bool
    set_name: bool
    check_ports: bool
    check_instances: CheckInstances | None
    snap_ports: bool
    add_port_layers: bool
    cache: Cache[int, Any] | dict[int, Any] | None
    drop_params: list[str]
    register_factory: bool
    overwrite_existing: bool | None
    layout_cache: bool | None
    info: dict[str, MetaData] | None
    post_process: Iterable[Callable[[TKCell], None]]
    debug_names: bool | None


class KCellDecoratorKWargs(TypedDict, total=False):
    """KWargs for `@cell`."""

    set_settings: bool
    set_name: bool
    check_ports: bool
    check_instances: CheckInstances | None
    snap_ports: bool
    add_port_layers: bool
    cache: Cache[int, Any] | dict[int, Any] | None
    basename: str | None
    drop_params: list[str]
    register_factory: bool
    overwrite_existing: bool | None
    layout_cache: bool | None
    info: dict[str, MetaData] | None
    post_process: Iterable[Callable[[TKCell], None]]
    debug_names: bool | None


class KCellDecorator(Protocol):
    """Signature of the `@cell` decorator."""

    def __call__(
        self, **kwargs: Unpack[KCellDecoratorKWargs]
    ) -> Callable[[KCellFunc[KCellParams, KC_co]], KCellFunc[KCellParams, KC_co]]:
        """__call__ implementation."""
        ...


class ModuleDecorator(Protocol):
    """Signature of the `@module_cell` decorator."""

    def __call__(
        self, /, **kwargs: Unpack[ModuleCellKWargs]
    ) -> Callable[[KCellFunc[KCellParams, KC_co]], KCellFunc[KCellParams, KC_co]]:
        """__call__ implementation."""
        ...


def _module_cell(
    cell_decorator: KCellDecorator,
    /,
    **kwargs: Unpack[ModuleCellKWargs],
) -> Callable[[KCellFunc[KCellParams, KC_co]], KCellFunc[KCellParams, KC_co]]:
    """Constructs the actual decorator.

    Modifies the basename to the module if the module is not the main one.
    """

    def decorator_cell(
        f: KCellFunc[KCellParams, KC_co],
    ) -> KCellFunc[KCellParams, KC_co]:
        mod = f.__module__
        basename = f.__name__ if mod == "__main" else f"{mod}_{f.__name__}"
        return cell_decorator(basename=basename, **kwargs)(f)

    return decorator_cell


class Decorators:
    """Various decorators intended to be attached to a KCLayout."""

    def __init__(self, kcl: KCLayout) -> None:
        """Just set the standard `@cell` decorator."""
        self._cell = kcl.cell

    @overload
    def module_cell(
        self,
        _func: KCellFunc[KCellParams, KC_co],
        /,
    ) -> KCellFunc[KCellParams, KC_co]: ...

    @overload
    def module_cell(
        self, /, **kwargs: Unpack[ModuleCellKWargs]
    ) -> Callable[[KCellFunc[KCellParams, KC_co]], KCellFunc[KCellParams, KC_co]]: ...

    def module_cell(  # type: ignore[misc]
        self,
        _func: KCellFunc[KCellParams, KC_co] | None = None,
        /,
        **kwargs: Unpack[ModuleCellKWargs],
    ) -> (
        KCellFunc[KCellParams, KC_co]
        | Callable[[KCellFunc[KCellParams, KC_co]], KCellFunc[KCellParams, KC_co]]
    ):
        """Constructs the `@module_cell` decorator on KCLayout.decorators."""

        def mc(
            **kwargs: Unpack[ModuleCellKWargs],
        ) -> Callable[[KCellFunc[KCellParams, KC_co]], KCellFunc[KCellParams, KC_co]]:
            return _module_cell(self._cell, **kwargs)  # type: ignore[arg-type]

        return mc(**kwargs) if _func is None else mc(**kwargs)(_func)

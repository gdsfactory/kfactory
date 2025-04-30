"""Defines additional decorators than just `@cell`."""

from __future__ import annotations

import functools
import inspect
from collections import defaultdict
from pathlib import Path
from threading import RLock
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Generic,
    Protocol,
    TypedDict,
    get_origin,
    overload,
)

from cachetools import Cache, cached
from typing_extensions import Unpack

from . import kdb
from .conf import CheckInstances, logger
from .exceptions import CellNameError
from .serialization import (
    DecoratorDict,
    DecoratorList,
    get_cell_name,
    hashable_to_original,
    to_hashable,
)
from .settings import KCellSettings, KCellSettingsUnits
from .typings import KC, VK, K, KC_co, KC_contra, KCellParams, MetaData

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from .kcell import AnyKCell, ProtoTKCell, TKCell, VKCell
    from .layout import KCLayout


def _parse_params(
    sig: inspect.Signature, kcl: KCLayout, args: Any, kwargs: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    params: dict[str, Any] = {p.name: p.default for _, p in sig.parameters.items()}
    param_units: dict[str, str] = {
        p.name: p.annotation.__metadata__[0]
        for p in sig.parameters.values()
        if get_origin(p.annotation) is Annotated
    }
    arg_par = list(sig.parameters.items())[: len(args)]
    for i, (k, _) in enumerate(arg_par):
        params[k] = args[i]
    params.update(kwargs)

    del_parameters: list[str] = []

    for key, value in params.items():
        if isinstance(value, dict | list):
            params[key] = to_hashable(value)
        elif isinstance(value, kdb.LayerInfo):
            params[key] = kcl.get_info(kcl.layer(value))
        if value is inspect.Parameter.empty:
            del_parameters.append(key)

    for param in del_parameters:
        params.pop(param, None)
        param_units.pop(param, None)

    return params, param_units


def _params_to_original(params: dict[str, Any]) -> None:
    for key, value in params.items():
        if isinstance(value, DecoratorDict | DecoratorList):
            params[key] = hashable_to_original(value)


def _add_port_layers(cell: ProtoTKCell[Any], kcl: KCLayout) -> None:
    for port in cell.to_itype().ports:
        if port.layer in cell.kcl.netlist_layer_mapping:
            if port.base.trans:
                edge = kdb.Edge(
                    kdb.Point(0, -port.width // 2),
                    kdb.Point(0, port.width // 2),
                )
                cell.shapes(cell.kcl.netlist_layer_mapping[port.layer]).insert(
                    port.trans * edge
                )
                if port.name:
                    cell.shapes(cell.kcl.netlist_layer_mapping[port.layer]).insert(
                        kdb.Text(port.name, port.trans)
                    )
            else:
                dwidth = kcl.to_um(port.width)
                dedge = kdb.DEdge(
                    kdb.DPoint(0, -dwidth / 2),
                    kdb.DPoint(0, dwidth / 2),
                )
                cell.shapes(cell.kcl.netlist_layer_mapping[port.layer]).insert(
                    port.dcplx_trans * dedge
                )
                if port.name:
                    cell.shapes(cell.kcl.netlist_layer_mapping[port.layer]).insert(
                        kdb.DText(
                            port.name,
                            port.dcplx_trans.s_trans(),
                        )
                    )


def _add_port_layers_vkcell(cell: VKCell, kcl: KCLayout) -> None:
    for port in cell.ports:
        if port.layer in cell.kcl.netlist_layer_mapping:
            if port.base.trans:
                edge = kdb.Edge(
                    kdb.Point(0, int(-port.width // 2)),
                    kdb.Point(0, int(port.width // 2)),
                )
                cell.shapes(cell.kcl.netlist_layer_mapping[port.layer]).insert(
                    port.trans * edge
                )
                if port.name:
                    cell.shapes(cell.kcl.netlist_layer_mapping[port.layer]).insert(
                        kdb.Text(port.name, port.trans)
                    )
            else:
                dedge = kdb.DEdge(
                    kdb.DPoint(0, -port.width / 2),
                    kdb.DPoint(0, port.width / 2),
                )
                cell.shapes(cell.kcl.netlist_layer_mapping[port.layer]).insert(
                    port.dcplx_trans * dedge
                )
                if port.name:
                    cell.shapes(cell.kcl.netlist_layer_mapping[port.layer]).insert(
                        kdb.DText(port.name, port.dcplx_trans.s_trans())
                    )


def _check_instances(
    cell: ProtoTKCell[Any], kcl: KCLayout, check_instances: CheckInstances
) -> None:
    match check_instances:
        case CheckInstances.RAISE:
            if any(inst.is_complex() for inst in cell.each_inst()):
                raise ValueError(
                    "Found off-grid instances, which is not allowed in most "
                    "foundries.\n"
                    "Please run c.flatten() before returning "
                    "or add use @cell(check_instances=False).\n"
                    "Cellnames of instances affected by this: "
                    + "\n".join(
                        inst.cell.name for inst in cell.each_inst() if inst.is_complex()
                    )
                )
        case CheckInstances.FLATTEN:
            if any(inst.is_complex() for inst in cell.each_inst()):
                cell.flatten()
        case CheckInstances.VINSTANCES:
            if any(inst.is_complex() for inst in cell.each_inst()):
                complex_insts = [inst for inst in cell.each_inst() if inst.is_complex()]
                for inst in complex_insts:
                    vinst = cell.create_vinst(kcl[inst.cell.cell_index()])
                    vinst.trans = inst.dcplx_trans
                    inst.delete()
        case CheckInstances.IGNORE:
            pass


def _snap_ports(cell: ProtoTKCell[Any], kcl: KCLayout) -> None:
    for port in cell.to_itype().ports:
        if port.base.dcplx_trans:
            dup = port.base.dcplx_trans.dup()
            dup.disp = kcl.to_um(kcl.to_dbu(port.base.dcplx_trans.disp))
            port.dcplx_trans = dup


def _check_ports(cell: ProtoTKCell[Any]) -> None:
    port_names: dict[str | None, int] = defaultdict(int)
    for port in cell.ports:
        port_names[port.name] += 1
    duplicate_names = [(name, n) for name, n in port_names.items() if n > 1]
    if duplicate_names:
        raise ValueError(
            "Found duplicate port names: "
            + ", ".join([f"{name}: {n}" for name, n in duplicate_names])
            + " If this intentional, please pass "
            "`check_ports=False` to the @cell decorator"
        )


def _get_function_name(f: Callable[..., Any]) -> str:
    if hasattr(f, "__name__"):
        name = f.__name__
    elif hasattr(f, "func"):
        name = f.func.__name__
    else:
        raise ValueError(f"Function {f} has no name.")
    return name


def _set_settings(
    cell: K,
    f: Callable[KCellParams, K],
    drop_params: Sequence[str],
    params: dict[str, Any],
    param_units: dict[str, Any],
    basename: str | None,
) -> None:
    cell.function_name = _get_function_name(f)
    cell.basename = basename

    for param in drop_params:
        params.pop(param, None)
        param_units.pop(param, None)
    cell.settings = KCellSettings(**params)
    cell.settings_units = KCellSettingsUnits(**param_units)


def _overwrite_existing(
    name: str | None, cell: ProtoTKCell[Any], kcl: KCLayout
) -> None:
    for c in list(kcl.cells(name or cell.name)):
        if c is not cell.kdb_cell:
            kcl[c.cell_index()].delete()


def _check_cell(cell: AnyKCell, kcl: KCLayout) -> None:
    if cell.kcl != kcl:
        raise ValueError(
            f"The {cell.__class__.__name__} created must be using the same"
            " KCLayout object as the @cell decorator. "
            f"{kcl.name!r} != {cell.kcl.name!r}. Please make sure "
            "to use @kcl.cell and only use @cell for cells which "
            "are created through kfactory.kcl. To create KCells not"
            " in the standard KCLayout, use either "
            "custom_kcl.kcell() or KCell(kcl=custom_kcl)."
        )


def _post_process(
    cell: KC_contra,
    post_process_functions: Iterable[Callable[[KC_contra], None]],
) -> None:
    for pp in post_process_functions:
        pp(cell)


class WrappedKCellFunc(Generic[KCellParams, KC]):
    _f: Callable[KCellParams, KC]
    _f_orig: Callable[KCellParams, ProtoTKCell[Any]]
    cache: Cache[int, KC] | dict[int, Any]
    name: str
    kcl: KCLayout
    output_type: type[KC]

    @property
    def __name__(self) -> str:
        if self.name is None:
            raise ValueError(f"{self._f} does not have a name")
        return self.name

    @__name__.setter
    def __name__(self, value: str) -> None:
        self.name = value

    def __init__(
        self,
        *,
        kcl: KCLayout,
        f: Callable[KCellParams, ProtoTKCell[Any]],
        sig: inspect.Signature,
        output_type: type[KC],
        cache: Cache[int, KC] | dict[int, KC],
        set_settings: bool,
        set_name: bool,
        check_ports: bool,
        check_instances: CheckInstances,
        snap_ports: bool,
        add_port_layers: bool,
        basename: str | None,
        drop_params: Sequence[str],
        overwrite_existing: bool | None,
        layout_cache: bool | None,
        info: dict[str, MetaData] | None,
        post_process: Iterable[Callable[[ProtoTKCell[Any]], None]],
        debug_names: bool,
    ) -> None:
        self.kcl = kcl
        self.output_type = output_type
        self.name = _get_function_name(f)

        @functools.wraps(f)
        def wrapper_autocell(
            *args: KCellParams.args, **kwargs: KCellParams.kwargs
        ) -> KC:
            params, param_units = _parse_params(sig, kcl, args, kwargs)

            @cached(cache=cache, lock=RLock())
            @functools.wraps(f)
            def wrapped_cell(**params: Any) -> KC:
                _params_to_original(params)
                old_future_name: str | None = None
                if set_name:
                    if basename is not None:
                        name = get_cell_name(basename, **params)
                    else:
                        name = get_cell_name(self.name, **params)
                    old_future_name = kcl.future_cell_name
                    kcl.future_cell_name = name
                    if layout_cache:
                        if overwrite_existing:
                            for c in list(kcl.cells(kcl.future_cell_name)):
                                kcl[c.cell_index()].delete()
                        else:
                            layout_cell = kcl.layout_cell(kcl.future_cell_name)
                            if layout_cell is not None:
                                logger.debug(
                                    "Loading {} from layout cache",
                                    kcl.future_cell_name,
                                )
                                return kcl.get_cell(
                                    layout_cell.cell_index(), output_type
                                )
                    logger.debug(f"Constructing {kcl.future_cell_name}")
                    name_: str | None = name
                else:
                    name_ = None
                cell = f(**params)  # type: ignore[call-arg]
                if cell is None:
                    raise ValueError(
                        f"The cell function {self.name!r} in {str(self.file)!r}"
                        " returned None. Did you forget to return the cell or component"
                        " at the end of the function?"
                    )

                logger.debug("Constructed {}", name_ or cell.name)

                if cell.locked:
                    # If the cell is locked, it comes from a cache (most likely)
                    # and should be copied first
                    cell = cell.dup(new_name=kcl.future_cell_name)
                if overwrite_existing:
                    _overwrite_existing(name_, cell, kcl)
                if set_name and name_:
                    if debug_names and cell.kcl.layout_cell(name_) is not None:
                        logger.opt(depth=4).error(
                            "KCell with name {name} exists already. Duplicate "
                            "occurrence in module '{module}' at "
                            "line {lno}",
                            name=name_,
                            module=f.__module__,
                            function_name=f.__name__,
                            lno=inspect.getsourcelines(f)[1],
                        )
                        raise CellNameError(f"KCell with name {name_} exists already.")

                    cell.name = name_
                    kcl.future_cell_name = old_future_name
                if set_settings:
                    _set_settings(cell, f, drop_params, params, param_units, basename)
                if check_ports:
                    _check_ports(cell)
                _check_instances(cell, kcl, check_instances)
                cell.insert_vinsts(recursive=False)
                if snap_ports:
                    _snap_ports(cell, kcl)
                if add_port_layers:
                    _add_port_layers(cell, kcl)
                _post_process(cell, post_process)
                cell.base.lock()
                _check_cell(cell, kcl)
                return output_type(base=cell.base)

            with kcl.thread_lock:
                cell_ = wrapped_cell(**params)
                if cell_.destroyed():
                    # If any cell has been destroyed, we should clean up the cache.
                    # Delete all the KCell entrances in the cache which have
                    # `destroyed() == True`
                    deleted_cell_hashes: list[int] = [
                        _hash_item
                        for _hash_item, _cell_item in cache.items()
                        if _cell_item.destroyed()
                    ]
                    for _dch in deleted_cell_hashes:
                        del cache[_dch]
                    cell_ = wrapped_cell(**params)

                if info is not None:
                    cell_.info.update(info)

                return cell_

        self._f = wrapper_autocell
        self._f_orig = f
        self.cache = cache
        functools.update_wrapper(self, f)

    def __call__(self, *args: KCellParams.args, **kwargs: KCellParams.kwargs) -> KC:
        return self._f(*args, **kwargs)

    def __len__(self) -> int:
        del_cells = [hk for hk, kc in self.cache.items() if kc._destroyed()]
        for hk in del_cells:
            del self.cache[hk]

        return len(self.cache)

    @functools.cached_property
    def file(self) -> Path:
        if isinstance(self._f_orig, FunctionType):
            return Path(self._f_orig.__code__.co_filename).resolve()
        if isinstance(self._f_orig, functools.partial):
            return Path(self._f_orig.func.__code__.co_filename).resolve()
        return Path(self._f_orig.__code__.co_filename).resolve()

    def prune(self) -> None:
        cells = [c for c in self.cache.values() if not c._destroyed()]
        caller_cis = {
            ci for cell in cells for ci in cell.caller_cells() if not cell._destroyed()
        }
        caller_cis |= {c.cell_index() for c in cells}
        self.kcl.delete_cells(list(caller_cis))

        self.kcl.cleanup()
        self.cache.clear()


class WrappedVKCellFunc(Generic[KCellParams, VK]):
    _f: Callable[KCellParams, VK]
    cache: Cache[int, Any] | dict[int, Any]
    name: str | None

    @property
    def __name__(self) -> str:
        if self.name is None:
            raise ValueError(f"{self._f} does not have a name")
        return self.name

    @__name__.setter
    def __name__(self, value: str) -> None:
        self.name = value

    def __init__(
        self,
        *,
        kcl: KCLayout,
        f: Callable[KCellParams, VK],
        sig: inspect.Signature,
        cache: Cache[int, Any] | dict[int, Any],
        set_settings: bool,
        set_name: bool,
        add_port_layers: bool,
        basename: str | None,
        drop_params: Sequence[str],
    ) -> None:
        @functools.wraps(f)
        def wrapper_autocell(
            *args: KCellParams.args, **kwargs: KCellParams.kwargs
        ) -> VK:
            params, param_units = _parse_params(sig, kcl, args, kwargs)

            @cached(cache=cache, lock=RLock())
            @functools.wraps(f)
            def wrapped_cell(**params: Any) -> VK:
                _params_to_original(params)
                cell = f(**params)  # type: ignore[call-arg]
                if cell.locked:
                    cell = cell.dup(new_name=kcl.future_cell_name)
                if set_name:
                    if basename is not None:
                        name = get_cell_name(basename, **params)
                    else:
                        name = get_cell_name(f.__name__, **params)
                    cell.name = name
                if set_settings:
                    _set_settings(cell, f, drop_params, params, param_units, basename)
                if add_port_layers:
                    _add_port_layers_vkcell(cell, kcl)
                cell.base.lock()
                _check_cell(cell, kcl)
                return cell

            return wrapped_cell(**params)

        self._f = wrapper_autocell
        self.cache = cache
        self.name = None
        if hasattr(f, "__name__"):
            self.name = f.__name__
        elif hasattr(f, "func"):
            self.name = f.func.__name__

    def __call__(self, *args: Any, **kwargs: Any) -> VK:
        return self._f(*args, **kwargs)


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
    ) -> Callable[[Callable[KCellParams, KC_co]], Callable[KCellParams, KC_co]]:
        """__call__ implementation."""
        ...


class ModuleDecorator(Protocol):
    """Signature of the `@module_cell` decorator."""

    def __call__(
        self, /, **kwargs: Unpack[ModuleCellKWargs]
    ) -> Callable[[Callable[KCellParams, KC_co]], Callable[KCellParams, KC_co]]:
        """__call__ implementation."""
        ...


def _module_cell(
    cell_decorator: KCellDecorator,
    /,
    **kwargs: Unpack[ModuleCellKWargs],
) -> Callable[[Callable[KCellParams, KC_co]], Callable[KCellParams, KC_co]]:
    """Constructs the actual decorator.

    Modifies the basename to the module if the module is not the main one.
    """

    def decorator_cell(
        f: Callable[KCellParams, KC_co],
    ) -> Callable[KCellParams, KC_co]:
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
        _func: Callable[KCellParams, KC_co],
        /,
    ) -> Callable[KCellParams, KC_co]: ...

    @overload
    def module_cell(
        self, /, **kwargs: Unpack[ModuleCellKWargs]
    ) -> Callable[[Callable[KCellParams, KC_co]], Callable[KCellParams, KC_co]]: ...

    def module_cell(
        self,
        _func: Callable[KCellParams, KC_co] | None = None,
        /,
        **kwargs: Unpack[ModuleCellKWargs],
    ) -> (
        Callable[KCellParams, KC_co]
        | Callable[[Callable[KCellParams, KC_co]], Callable[KCellParams, KC_co]]
    ):
        """Constructs the `@module_cell` decorator on KCLayout.decorators."""

        def mc(
            **kwargs: Unpack[ModuleCellKWargs],
        ) -> Callable[[Callable[KCellParams, KC_co]], Callable[KCellParams, KC_co]]:
            return _module_cell(self._cell, **kwargs)  # type: ignore[arg-type]

        return mc(**kwargs) if _func is None else mc(**kwargs)(_func)

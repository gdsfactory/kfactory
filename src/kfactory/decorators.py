"""Defines additional decorators than just `@cell`."""

from __future__ import annotations

import functools
import inspect
import pickle
from collections import defaultdict
from pathlib import Path
from threading import RLock
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
from .typings import KC, VK, K, KCellParams, MetaData

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from .kcell import AnyKCell, ProtoTKCell, TKCell, VKCell
    from .layout import KCLayout
    from .typings import KC_co


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
                    "Most foundries will not allow off-grid "
                    "instances. Please flatten them or add "
                    "check_instances=False to the decorator.\n"
                    "Cellnames of instances affected by this:"
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


def _set_settings(
    cell: K,
    f: Callable[KCellParams, K],
    drop_params: Sequence[str],
    params: dict[str, Any],
    param_units: dict[str, Any],
    basename: str | None,
) -> None:
    if hasattr(f, "__name__"):
        cell.function_name = f.__name__
    elif hasattr(f, "func"):
        cell.function_name = f.func.__name__
    else:
        raise ValueError(f"Function {f} has no name.")
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
    cell: K, post_process_functions: Iterable[Callable[[K], None]]
) -> None:
    for pp in post_process_functions:
        pp(cell)


class WrappedKCellFunc(Generic[KC]):
    _f: Callable[..., KC]
    _f_orig: Callable[..., KC]
    cache: Cache[int, KC] | dict[int, Any]
    name: str | None
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
        f: Callable[KCellParams, KC],
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
        post_process: Iterable[Callable[[KC], None]],
        debug_names: bool,
    ) -> None:
        self.kcl = kcl
        self.output_type = output_type

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
                        name = get_cell_name(f.__name__, **params)
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
        self.name = None
        if hasattr(f, "__name__"):
            self.name = f.__name__
        elif hasattr(f, "func"):
            self.name = f.func.__name__

    def __call__(self, *args: Any, **kwargs: Any) -> KC:
        return self._f(*args, **kwargs)

    def dump(self, path: Path, save_options: kdb.SaveLayoutOptions) -> None:
        logger.debug("Saving state of function {name}", name=self.name)
        save_options.clear_cells()
        save_options.keep_instances = True
        hk_list: list[tuple[str, int]] = []

        for hk, c in self.cache.items():
            save_options.add_this_cell(c.cell_index())
            hk_list.append((c.name, hk))
        path.mkdir(parents=True, exist_ok=True)
        self.kcl.write(path / "cells.gds.gz", options=save_options)
        with (path / "keytable.pkl").open(mode="wb") as f:
            pickle.dump(tuple(hk_list), f)

    def load(self, path: Path) -> None:
        load_opts = kdb.LoadLayoutOptions()
        load_opts.cell_conflict_resolution = (
            kdb.LoadLayoutOptions.CellConflictResolution.SkipNewCell
        )
        self.kcl.read(path / "cells.gds.gz", options=load_opts, test_merge=False)
        with (path / "keytable.pkl").open(mode="rb") as f:
            hashmap = pickle.load(f)  # noqa: S301
            for cell_name, hk in hashmap:
                self.cache[hk] = self.output_type(
                    base=self.kcl.tkcells[self.kcl.layout.cell(cell_name).cell_index()]
                )

    @functools.cached_property
    def file(self) -> Path:
        return Path(self._f_orig.__code__.co_filename).resolve()


class WrappedVKCellFunc(Generic[VK]):
    _f: Callable[..., VK]
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

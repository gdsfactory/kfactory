"""Defines additional decorators than just `@cell`."""

from __future__ import annotations

import functools
import inspect
from collections import defaultdict
from enum import StrEnum
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
from .kcell import AnyKCell, ProtoTKCell, TKCell, VKCell
from .serialization import (
    DecoratorDict,
    DecoratorList,
    get_cell_name,
    hashable_to_original,
    to_hashable,
)
from .settings import KCellSettings, KCellSettingsUnits
from .typings import (
    KC,
    VK,
    K,
    K_contra,
    KC_co,
    KC_contra,
    KCellParams,
    MetaData,
    VK_contra,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

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


class PortsDefinition(TypedDict, total=False):
    right: list[str]
    top: list[str]
    left: list[str]
    bottom: list[str]


class Direction(StrEnum):
    right = "right"
    left = "left"
    top = "top"
    bottom = "bottom"


def _check_instances(
    cell: ProtoTKCell[Any], kcl: KCLayout, check_instances: CheckInstances
) -> None:
    match check_instances:
        case CheckInstances.RAISE:
            if any(inst.is_complex() for inst in cell.each_inst()):
                instance_names = [
                    inst.name for inst in cell.each_inst() if inst.is_complex()
                ]
                cell_names = [
                    inst.cell.name for inst in cell.each_inst() if inst.is_complex()
                ]
                affected = "\n".join(
                    f"Instance name: {iname}, Cell name: {cname}"
                    for iname, cname in zip(instance_names, cell_names, strict=True)
                )
                raise ValueError(
                    "Found off-grid instances, which is not allowed in most "
                    "foundries.\n"
                    "Please run c.flatten() before returning "
                    "or add use @cell(check_instances=False).\n"
                    f"Instances affected by this:\n{affected}"
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


def _check_ports(cell: ProtoTKCell[Any] | VKCell) -> None:
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


def _check_pins(cell: ProtoTKCell[Any] | VKCell) -> None:
    pin_names: dict[str | None, int] = defaultdict(int)
    for pin in cell.pins:
        pin_names[pin.name] += 1
        pin_ports = {id(port) for port in pin._base.ports}
        pin_ports_in_cell = {id(port.base) for port in cell.ports} & pin_ports
        if len(pin_ports_in_cell) != len(pin_ports):
            raise ValueError(
                f"Attempted to create a pin {pin.name} with ports not belonging "
                "to the cell. Please use ports that belong to the cell "
                "to create the pin."
            )

    duplicate_pin_names = [(name, n) for name, n in pin_names.items() if n > 1]
    if duplicate_pin_names:
        raise ValueError(
            "Found duplicate pin names: "
            + ", ".join([f"{name}: {n}" for name, n in duplicate_pin_names])
            + " If this intentional, please pass "
            "`check_pins=False` to the @cell decorator"
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


@overload
def _post_process(
    cell: KC_contra,
    post_process_functions: Iterable[Callable[[KC_contra], None]],
) -> None: ...


@overload
def _post_process(
    cell: VK_contra,
    post_process_functions: Iterable[Callable[[VK_contra], None]],
) -> None: ...


def _post_process(
    cell: K_contra,
    post_process_functions: Iterable[Callable[[K_contra], None]],
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
    lvs_equivalent_ports: list[list[str]] | None = None
    ports_definition: PortsDefinition | None = None

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
        check_pins: bool,
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
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
    ) -> None:
        self.kcl = kcl
        self.output_type = output_type
        self.name = _get_function_name(f)
        self.ports_definition = ports.copy() if ports is not None else None

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
                    raise TypeError(
                        f"The cell function {self.name!r} in {str(self.file)!r}"
                        " returned None. Did you forget to return the cell or component"
                        " at the end of the function?"
                    )
                if not isinstance(cell, ProtoTKCell):
                    raise TypeError(
                        f"The cell function {self.name!r} in {str(self.file)!r}"
                        f" returned {type(cell)=}. The `@cell` decorator only supports"
                        " KCell/DKCell or any SubClass such as Component."
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
                if check_pins:
                    _check_pins(cell)
                _check_instances(cell, kcl, check_instances)
                cell.insert_vinsts(recursive=False)
                if snap_ports:
                    _snap_ports(cell, kcl)
                if add_port_layers:
                    _add_port_layers(cell, kcl)
                _post_process(cell, post_process)
                cell.base.lock()
                _check_cell(cell, kcl)
                if self.ports_definition is not None:
                    port_lengths = 0
                    for direction in Direction:
                        port_lengths += len(self.ports_definition.get(direction, []))  # type: ignore[arg-type]
                    mapping = {0: "right", 1: "top", 2: "left", 3: "bottom"}
                    if len(cell.ports) != port_lengths:
                        received_ports = PortsDefinition()
                        for port in cell.ports:
                            mapped: Direction = Direction(mapping[port.trans.angle])
                            if mapped not in received_ports:
                                received_ports[mapped] = []  # type: ignore[literal-required]
                            received_ports[mapped].append(port.name)  # type: ignore[literal-required]
                        raise ValueError(
                            "The `@cell` decorator defines ports, but they do not match"
                            " the extracted ports. Declared ports: "
                            f"{self.ports_definition}"
                            ", Received ports: "
                            f"{received_ports}"
                        )

                    if check_ports:
                        found_errors = False
                        for port in cell.ports:
                            if (
                                port.name
                                not in self.ports_definition[mapping[port.trans.angle]]  # type: ignore[literal-required]
                            ):
                                found_errors = True
                        if found_errors:
                            received_ports = PortsDefinition()
                            for port in cell.ports:
                                mapped = Direction(mapping[port.trans.angle])
                                if mapped not in received_ports:
                                    received_ports[mapped] = []  # type: ignore[literal-required]
                                received_ports[mapped].append(port.name)  # type: ignore[literal-required]
                            raise ValueError(
                                "The `@cell` decorator defines ports, but they do not"
                                " match the extracted ports. Declared ports: "
                                f"{self.ports_definition}"
                                ", Received ports: "
                                f"{received_ports}"
                            )
                    else:
                        port_names: list[str | None] = []
                        for direction in Direction:
                            if direction in self.ports_definition:
                                port_names.extend(self.ports_definition[direction])  # type: ignore[literal-required]

                        for port in cell.ports:
                            if port.name not in port_names:
                                found_errors = True
                        if found_errors:
                            raise ValueError(
                                "The `@cell` decorator defines ports, but they do not"
                                " match the extracted ports. Declared ports: "
                                f"{port_names}"
                                ", Received ports: "
                                f"{[p.name for p in cell.ports]}"
                            )

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
        self.lvs_equivalent_ports = lvs_equivalent_ports
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
    _f_orig: Callable[KCellParams, VKCell]
    cache: Cache[int, VK] | dict[int, Any]
    name: str
    kcl: KCLayout
    output_type: type[VK]
    lvs_equivalent_ports: list[list[str]] | None = None
    ports_definition: PortsDefinition | None = None

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
        f: Callable[KCellParams, VKCell],
        sig: inspect.Signature,
        output_type: type[VK],
        cache: Cache[int, VK] | dict[int, VK],
        set_settings: bool,
        set_name: bool,
        check_ports: bool,
        check_pins: bool,
        add_port_layers: bool,
        basename: str | None,
        drop_params: Sequence[str],
        info: dict[str, MetaData] | None,
        post_process: Iterable[Callable[[VKCell], None]],
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
    ) -> None:
        self.kcl = kcl
        self.output_type = output_type
        self.name = _get_function_name(f)
        self.ports_definitions = ports.copy() if ports is not None else None

        @functools.wraps(f)
        def wrapper_autocell(
            *args: KCellParams.args, **kwargs: KCellParams.kwargs
        ) -> VK:
            params, param_units = _parse_params(sig, kcl, args, kwargs)

            @cached(cache=cache, lock=RLock())
            @functools.wraps(f)
            def wrapped_cell(**params: Any) -> VK:
                _params_to_original(params)
                old_future_name: str | None = None
                if set_name:
                    if basename is not None:
                        name = get_cell_name(basename, **params)
                    else:
                        name = get_cell_name(self.name, **params)
                    old_future_name = kcl.future_cell_name
                    kcl.future_cell_name = name
                    logger.debug(f"Constructing {kcl.future_cell_name}")
                    name_: str | None = name
                else:
                    name_ = None
                cell = f(**params)  # type: ignore[call-arg]
                if cell is None:
                    raise TypeError(
                        f"The cell function {self.name!r} in {str(self.file)!r}"
                        " returned None. Did you forget to return the cell or component"
                        " at the end of the function?"
                    )
                if not isinstance(cell, VKCell):
                    raise TypeError(
                        f"The cell function {self.name!r} in {str(self.file)!r}"
                        f" returned {type(cell)=}. The `@vcell` decorator only supports"
                        " VKCell or any SubClass such as ComponentAllAngle."
                    )

                logger.debug("Constructed {}", name_ or cell.name)

                if cell.locked:
                    # If the cell is locked, it comes from a cache (most likely)
                    # and should be copied first
                    cell = cell.dup(new_name=kcl.future_cell_name)
                if set_name and name_:
                    cell.name = name_
                    kcl.future_cell_name = old_future_name
                if set_settings:
                    _set_settings(cell, f, drop_params, params, param_units, basename)
                if check_ports:
                    _check_ports(cell)
                if check_pins:
                    _check_pins(cell)
                if add_port_layers:
                    _add_port_layers_vkcell(cell, kcl)
                _post_process(cell, post_process)
                cell.base.lock()
                _check_cell(cell, kcl)
                if self.ports_definition is not None:
                    port_lengths = 0
                    for direction in Direction:
                        port_lengths += len(self.ports_definition.get(direction, []))  # type: ignore[arg-type]
                    mapping = {0: "right", 1: "top", 2: "left", 3: "bottom"}
                    if len(cell.ports) != port_lengths:
                        received_ports = PortsDefinition()
                        for port in cell.ports:
                            mapped: Direction = Direction(mapping[port.trans.angle])
                            if mapped not in received_ports:
                                received_ports[mapped] = []  # type: ignore[literal-required]
                            received_ports[mapped].append(port.name)  # type: ignore[literal-required]
                        raise ValueError(
                            "The `@cell` decorator defines ports, but they do not match"
                            " the extracted ports. Declared ports: "
                            f"{self.ports_definition}"
                            ", Received ports: "
                            f"{received_ports}"
                        )

                    port_names: list[str | None] = []
                    for direction in Direction:
                        if direction in self.ports_definition:
                            port_names.extend(self.ports_definition[direction])  # type: ignore[literal-required]

                    for port in cell.ports:
                        if port.name not in port_names:
                            found_errors = True
                    if found_errors:
                        raise ValueError(
                            "The `@cell` decorator defines ports, but they do not"
                            " match the extracted ports. Declared ports: "
                            f"{port_names}"
                            ", Received ports: "
                            f"{[p.name for p in cell.ports]}"
                        )

                return output_type(base=cell.base)

            with kcl.thread_lock:
                cell_ = wrapped_cell(**params)

                if info is not None:
                    cell_.info.update(info)

                return cell_

        self._f = wrapper_autocell
        self._f_orig = f
        self.cache = cache
        self.lvs_equivalent_ports = lvs_equivalent_ports
        functools.update_wrapper(self, f)

    def __call__(self, *args: Any, **kwargs: Any) -> VK:
        return self._f(*args, **kwargs)

    def __len__(self) -> int:
        return len(self.cache)

    @functools.cached_property
    def file(self) -> Path:
        if isinstance(self._f_orig, FunctionType):
            return Path(self._f_orig.__code__.co_filename).resolve()
        if isinstance(self._f_orig, functools.partial):
            return Path(self._f_orig.func.__code__.co_filename).resolve()
        return Path(self._f_orig.__code__.co_filename).resolve()


class ModuleCellKWargs(TypedDict, total=False):
    """KWargs for `@module_cell`."""

    set_settings: bool
    set_name: bool
    check_ports: bool
    check_pins: bool
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
    check_pins: bool
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

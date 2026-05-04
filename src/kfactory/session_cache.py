from __future__ import annotations

import copyreg
import functools
import hashlib
import importlib
import json
import operator
import pickle
import types
from collections import defaultdict
from shutil import rmtree
from typing import TYPE_CHECKING

from kfactory.cross_section import SymmetricalCrossSection
from kfactory.kcell import ProtoKCell, VKCell

from . import kdb
from .conf import logger
from .layout import KCLayout, kcls
from .typings import DShapeLike, IShapeLike
from .utilities import get_session_directory, save_layout_options

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable
    from io import BufferedReader, BufferedWriter
    from pathlib import Path
    from typing import Any

    from .kcell import KCell, ProtoTKCell


def _reconstruct_function(module_name: str, qualname: str) -> Any:
    """Reconstruct a function from its module and qualified name."""
    module = importlib.import_module(module_name)
    obj: Any = module
    for attr in qualname.split("."):
        obj = getattr(obj, attr)
    return obj


def _reconstruct_partial(
    func: Any, args: tuple[Any, ...], keywords: dict[str, Any]
) -> functools.partial[Any]:
    """Reconstruct a functools.partial from its components."""
    return functools.partial(func, *args, **keywords)


class FunctionPickler(pickle.Pickler):
    """Custom pickler that can serialize non-lambda functions by reference."""

    def reducer_override(self, obj: Any) -> Any:
        if isinstance(obj, types.FunctionType):
            if obj is _reconstruct_function or obj is _reconstruct_partial:
                return NotImplemented
            if obj.__name__ == "<lambda>":
                raise pickle.PicklingError(
                    "Cannot pickle lambda functions. Use a named function instead."
                )
            if "<locals>" in obj.__qualname__:
                raise pickle.PicklingError(
                    f"Cannot pickle nested function {obj.__qualname__!r}. "
                    "Use a module-level function instead."
                )
            return _reconstruct_function, (obj.__module__, obj.__qualname__)
        if isinstance(obj, functools.partial):
            return _reconstruct_partial, (obj.func, obj.args, obj.keywords)
        return NotImplemented


class FunctionUnpickler(pickle.Unpickler):
    """Custom unpickler paired with FunctionPickler."""


def _dump(obj: Any, f: BufferedWriter) -> None:
    """Pickle an object using FunctionPickler."""
    FunctionPickler(f).dump(obj)


def _load(f: BufferedReader) -> Any:
    """Unpickle an object using FunctionUnpickler."""
    return FunctionUnpickler(f).load()


def _factory_key(name: str, file_path: str) -> str:
    """Create a unique key for a factory based on name and file path."""
    return f"{name}@{file_path}"


def save_session(
    c: ProtoTKCell[Any] | None = None,
    session_dir: Path | None = None,
) -> None:
    kcls_dir = get_session_directory(session_dir)
    if kcls_dir.exists():
        rmtree(kcls_dir)
    skip_cells: set[int] = set()
    kcl_dependencies: defaultdict[str, set[str]] = defaultdict(set)
    kcls_ = (
        list(kcls.values()) if c is None else [kcls[kcl_] for kcl_ in get_cell_kcls(c)]
    )

    for kcl in kcls_:
        kcl.start_changes()
        save_options = save_layout_options()
        save_options.clear_cells()
        kcl_dir = kcls_dir / kcl.name
        kcl_dir.mkdir(parents=True)

        cis = kcl.each_cell_bottom_up()
        factory_dependency: defaultdict[str, set[str]] = defaultdict(set)
        factory_cells: defaultdict[str, list[tuple[Hashable, Any]]] = defaultdict(list)
        take_cell_indexes: set[int] = set()
        for ci in cis:
            if ci in skip_cells:
                continue
            kc = kcl[ci]
            if kc.is_library_cell():
                logger.debug(f"Adding {kc.name!r} to session cache")
                take_cell_indexes.add(ci)
                kcl_dependencies[kcl.name].add(kc.library().name())
                continue
            if not kc.has_factory_name():
                skip_cells.add(ci)
                skip_cells |= set(kc.caller_cells())
                logger.warning(
                    f"Skipping to save cell {kc.name!r} (cell_index {ci})"
                    " as it does not have a creator "
                    "function. This will affect all parent cells as well: "
                    f"{[kcl[ci_].name for ci_ in kc.caller_cells()]!r}"
                )
            else:
                fd = factory_dependency[kc.factory_name]
                for pi in kc.caller_cells():
                    pc = kcl[pi]
                    if pc.factory_name is not None:
                        fd.add(pc.factory_name)
                logger.debug(f"Adding {kc.name!r} to session cache")
                take_cell_indexes.add(ci)
        for factory in kcl.factories._all:
            assert factory.name is not None
            for hk, cell in factory.cache.items():
                if cell.cell_index() in take_cell_indexes:
                    factory_cells[factory.name].append((hk, cell.name))
        for ci in take_cell_indexes - skip_cells:
            save_options.add_this_cell(ci)
        kcl.end_changes()
        kcl.write(kcl_dir / "cells.gds.gz", options=save_options)
        factory_infos = {
            _factory_key(k, _file_path(kcl.factories[k].file)): [
                v,
                factory_cells[k],
                _file_path(kcl.factories[k].file),
                _file_hash(kcl.factories[k].file),
            ]
            for k, v in factory_dependency.items()
        }
        with (kcl_dir / "factories.pkl").open("wb") as f:
            _dump(factory_infos, f)
        with (kcl_dir / "cross_sections.pkl").open("wb") as f:
            pickle.dump(kcl.cross_sections.cross_sections, f)

    with (kcls_dir / "../kcl_dependencies.json").resolve().open("wt") as f:
        json.dump({k: list(v) for k, v in kcl_dependencies.items()}, f)


def load_session(
    session_dir: Path | None = None, warn_missing_dir: bool = True
) -> None:
    kcls_dir = get_session_directory(session_dir)
    logger.debug("Loading session from {}", kcls_dir)

    if not kcls_dir.exists():
        if warn_missing_dir:
            logger.warning(
                "Session folder {} does not exist, cannot load session.", kcls_dir
            )
        return

    dependency_file = (kcls_dir / "../kcl_dependencies.json").resolve()

    if not dependency_file.exists():
        logger.error(
            "Found session folder {}, but it's missing `kcl_dependencies.json`, "
            "aborting session load."
        )
        return
    with dependency_file.open("rt") as f:
        kcl_dependencies = json.load(f)

    kcl_paths = set(kcls_dir.glob("*"))

    loaded_kcls: set[Path] = set()

    changed = True
    while changed:
        changed = False
        if len(loaded_kcls) == len(kcl_paths):
            break
        loadable_kcls = kcl_paths - loaded_kcls
        for p in loadable_kcls:
            if not (
                {kcls_dir / p_ for p_ in kcl_dependencies.get(p.name, [])} - loaded_kcls
            ):
                logger.debug(f"Loading KCLayout {p.stem!r}")
                load_kcl(kcl_path=p)
                loaded_kcls.add(p)
                changed = True
                logger.debug("Loaded {}", p.name)
    else:
        logger.warning("Cannot load session due to circular dependencies. ")
    logger.debug("Loaded session. Loaded kcls: {}", [p.name for p in kcl_paths])


def load_kcl(kcl_path: Path) -> None:
    kcl_name = kcl_path.name
    if kcl_name not in kcls:
        raise ValueError(f"Unknown KCL {kcl_name}")
    kcl = kcls[kcl_name]
    loaded_kcl = KCLayout("SESSION_LOAD")
    xs_path = kcl_path / "cross_sections.pkl"
    if xs_path.is_file():
        with xs_path.open("rb") as f:
            kcl.cross_sections.cross_sections = pickle.load(f)  # noqa: S301

    loaded_kcl.read(kcl_path / "cells.gds.gz")
    invalid_factories: set[str] = set()
    with (kcl_path / "factories.pkl").open("rb") as f:
        factory_infos = _load(f)
    for factory in sorted(kcl.factories._all, key=operator.attrgetter("name")):
        logger.debug(f"Loading factory {factory.name!r}")
        p = _file_path(factory.file)
        fh = _file_hash(factory.file)
        factory_key = _factory_key(factory.name, p)
        factory_info = factory_infos.get(factory_key)
        assert factory.name is not None
        logger.debug(f"{factory_info=}")
        if factory_info is not None:
            factory_dependencies, _, p_loaded, fh_loaded = factory_info
            logger.debug(
                "Checking factory path compatibility of definition "
                f"{p!r} vs loaded {p_loaded!r} ({p == p_loaded}) and file hashes "
                f"defintio {fh!r} vs loaded {fh_loaded!r} ({fh == fh_loaded})"
            )
            if p_loaded != p or fh_loaded != fh:
                invalid_factories |= factory_dependencies
                invalid_factories.add(factory_key)
    cells_to_add: defaultdict[int, list[tuple[int, KCell, str]]] = defaultdict(list)
    logger.debug(f"{sorted(invalid_factories)=}")
    for factory in kcl.factories._all:
        if factory.name is None:
            continue
        p = _file_path(factory.file)
        factory_key = _factory_key(factory.name, p)
        if factory_key in invalid_factories:
            continue
        logger.debug(f"Filling {factory.name!r}")
        if factory_info := factory_infos.get(factory_key):
            cache_ = factory_info[1]
            logger.debug(cache_)
            for hk, cn in cache_:
                kc = loaded_kcl[cn]
                logger.debug(f"Adding {cn!r} to cache of {factory.name!r}")
                cells_to_add[kc.kdb_cell.hierarchy_levels()].append(
                    (hk, kc, factory.name)
                )
    for _, factory_cell_list in sorted(
        cells_to_add.items(), key=operator.itemgetter(0)
    ):
        for hk, kc, factory_name in factory_cell_list:
            factory = kcl.factories[factory_name]
            # Check if cell already exists in the layout
            existing_kdb_cell = kcl.layout.cell(kc.name)
            if existing_kdb_cell is not None:
                # Cell already exists, use it and add to cache
                existing_cell_index = existing_kdb_cell.cell_index()
                kc_ = kcl[existing_cell_index]
                logger.debug(
                    f"Cell {kc.name!r} already exists (index {existing_cell_index}), "
                    "reusing and adding to cache"
                )
                tkc_ = kc_._base
                factory.cache[hk] = factory.output_type(base=tkc_)
            else:
                # Create new cell
                kc_ = kcl.kcell(name=kc.name)
                for inst in kc.insts:
                    if inst.cell.is_library_cell():
                        lib_c = inst.cell.library().layout().cell(inst.cell.name)
                        if lib_c is not None:
                            inst_ = kc_.icreate_inst(
                                kcls[inst.cell.library().name()][lib_c.cell_index()],
                                na=inst.na,
                                nb=inst.nb,
                                a=inst.a,
                                b=inst.b,
                            )

                    else:
                        inst_ = kc_.icreate_inst(
                            kc_.kcl[inst.cell.name],
                            na=inst.na,
                            nb=inst.nb,
                            a=inst.a,
                            b=inst.b,
                        )
                    inst_.cplx_trans = inst.cplx_trans
                kc_.copy_shapes(kc.kdb_cell)
                kc_.copy_meta_info(kc.kdb_cell)
                kc_.get_meta_data()

                tkc_ = kc_._base
                factory.cache[hk] = factory.output_type(base=tkc_)
    loaded_kcl.delete()


def get_cell_kcls(c: ProtoTKCell[Any]) -> set[str]:
    kcls_ = {c.kcl.name}
    for ci in c.called_cells():
        c_ = c.kcl.layout.cell(ci)
        if c_.is_library_cell():
            kcls_ |= get_cell_kcls(kcls[c_.library().name()][c_.library_cell_index()])
    return kcls_


@functools.cache
def _file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


@functools.cache
def _file_path(path: Path) -> str:
    return str(path)


def _reduce_region(
    obj: kdb.Region,
) -> tuple[Callable[..., Any], tuple[tuple[str, ...]]]:
    return (_read_region, (tuple([p.to_s() for p in obj.each()]),))


def _read_region(polygons: tuple[str]) -> kdb.Region:
    return kdb.Region([kdb.PolygonWithProperties.from_s(p) for p in polygons])


def _reduce_klayout_shapes(
    obj: IShapeLike | DShapeLike,
) -> tuple[Callable[..., Any], tuple[str, ...] | tuple[tuple[str, ...]]]:
    if isinstance(obj, kdb.Region):
        return _reduce_region(obj)
    return (obj.__class__.from_s, (obj.to_s(),))


def _reduce_layer_info(obj: kdb.LayerInfo) -> tuple[Callable[..., Any], tuple[str]]:
    return (kdb.LayerInfo.from_string, (obj.to_s(),))


def _get_cell(kcl_name: str, virtual: bool, factory_name: str, settings: Any) -> Any:
    if virtual:
        return kcls[kcl_name].virtual_factories[factory_name](**settings)
    return kcls[kcl_name].factories[factory_name](**settings)


def _reduce_protocells(
    obj: ProtoTKCell[Any] | VKCell,
) -> tuple[Callable[..., Any], tuple[str, bool, str, Any]]:
    if obj.has_factory_name():
        if isinstance(obj, ProtoKCell):
            return (
                _get_cell,
                (
                    obj.kcl.name,
                    False,
                    obj.kcl.factories[obj.factory_name].name,
                    obj.settings.model_dump(),
                ),
            )
        return (
            _get_cell,
            (
                obj.kcl.name,
                True,
                obj.factory_name.name,
                obj.settings.model_dump(),
            ),
        )
    raise NotImplementedError


def _get_symmetrical_cross_section(
    model_dump: dict[str, Any],
) -> SymmetricalCrossSection:
    return SymmetricalCrossSection.model_validate(model_dump)


def _reduce_symmetrical_cross_section(
    obj: SymmetricalCrossSection,
) -> tuple[Callable[..., SymmetricalCrossSection], tuple[dict[str, Any]]]:
    return (_get_symmetrical_cross_section, (obj.model_dump(),))


for cls in IShapeLike.__value__.__args__:
    copyreg.pickle(cls, _reduce_klayout_shapes)
copyreg.pickle(kdb.LayerInfo, _reduce_layer_info)
copyreg.pickle(SymmetricalCrossSection, _reduce_symmetrical_cross_section)

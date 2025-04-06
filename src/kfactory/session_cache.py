from __future__ import annotations

import functools
import hashlib
import json
import operator
import pickle
from collections import defaultdict
from hashlib import sha256
from shutil import rmtree
from typing import TYPE_CHECKING

from .conf import config, logger
from .layout import KCLayout, kcls
from .utilities import save_layout_options

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from .kcell import KCell, ProtoTKCell


def save_session(
    c: ProtoTKCell[Any] | None = None, session_dir: Path | None = None
) -> None:
    kcls_dir = session_dir or (config.project_dir / "build/session/kcls")
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
        cis = set(kcl.each_cell_bottom_up())
        factory_dependency: defaultdict[str, set[str]] = defaultdict(set)
        factory_cells: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
        take_cell_indexes: set[int] = set()
        for ci in cis:
            if ci in skip_cells:
                continue
            kc = kcl[ci]
            if kc.is_library_cell():
                take_cell_indexes.add(ci)
                kcl_dependencies[kcl.name].add(kc.library().name())
                continue
            if kc.factory_name is None:
                skip_cells |= set(ci)
            else:
                fd = factory_dependency[kc.factory_name]
                for pi in kc.caller_cells():
                    pc = kcl[pi]
                    if pc.factory_name is not None:
                        fd.add(pc.factory_name)
                take_cell_indexes.add(ci)

        for factory in kcl.factories.values():
            assert factory.name is not None
            for hk, cell in factory.cache.items():
                if cell.cell_index() in take_cell_indexes:
                    factory_cells[factory.name].append((hk, cell.name))

        for ci in cis - skip_cells:
            save_options.add_this_cell(ci)
        kcl.end_changes()
        kcl.write(kcl_dir / "cells.gds.gz", options=save_options)
        factory_infos = {
            k: [
                v,
                factory_cells[k],
                _file_path_hash(kcl.factories[k].file),
                _file_hash(kcl.factories[k].file),
            ]
            for k, v in factory_dependency.items()
        }
        with (kcl_dir / "facories.pkl").open("wb") as f:
            pickle.dump(factory_infos, f)
    with (kcls_dir / "../kcl_dependencies.json").resolve().open("wt") as f:
        json.dump({k: list(v) for k, v in kcl_dependencies.items()}, f)


def load_session(
    session_dir: Path | None = None, warn_missing_dir: bool = True
) -> None:
    kcls_dir = session_dir or (config.project_dir / "build/session/kcls")
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
    loaded_kcl.read(kcl_path / "cells.gds.gz")
    invalid_factories: set[str] = set()
    with (kcl_path / "facories.pkl").open("rb") as f:
        factory_infos = pickle.load(f)  # noqa: S301
    for factory in kcl.factories.values():
        ph = _file_path_hash(factory.file)
        fh = _file_hash(factory.file)
        factory_info = factory_infos.get(factory.name)
        assert factory.name is not None
        if factory_info is not None:
            factory_dependencies, _, ph_loaded, fh_loaded = factory_info
            if ph_loaded != ph or fh_loaded != fh:
                invalid_factories |= factory_dependencies
                invalid_factories.add(factory.name)
    cells_to_add: defaultdict[int, list[tuple[int, KCell, str]]] = defaultdict(list)
    for factory_name in set(kcl.factories.keys()) - invalid_factories:
        if factory_info := factory_infos.get(factory_name):
            cache_ = factory_info[1]
            for hk, cn in cache_:
                kc = loaded_kcl[cn]
                cells_to_add[kc.kdb_cell.hierarchy_levels()].append(
                    (hk, kc, factory_name)
                )
    for _, factory_cell_list in sorted(
        cells_to_add.items(), key=operator.itemgetter(0)
    ):
        for hk, kc, factory_name in factory_cell_list:
            factory = kcl.factories[factory_name]
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
def _file_path_hash(path: Path) -> str:
    return sha256(str(path).encode()).hexdigest()

from __future__ import annotations

import functools
import hashlib
import pickle
from collections import defaultdict
from hashlib import sha256
from shutil import rmtree
from typing import TYPE_CHECKING

from .conf import config
from .layout import KCLayout, kcls
from .utilities import save_layout_options

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from .decorators import WrappedKCellFunc
    from .kcell import ProtoTKCell


def save_session(
    c: ProtoTKCell[Any] | None = None, session_dir: Path | None = None
) -> None:
    build_dir = session_dir or (config.project_dir / "build/session")
    if build_dir.exists():
        rmtree(build_dir)
    skip_cells: set[int] = set()
    for kcl in kcls.values():
        kcl.start_changes()
        save_options = save_layout_options()
        save_options.clear_cells()
        kcl_dir = build_dir / kcl.name
        kcl_dir.mkdir(parents=True)
        cis = set(kcl.each_cell_bottom_up())
        factory_dependency: defaultdict[str, set[str]] = defaultdict(set)
        factory_cells: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
        take_cell_indexes: set[int] = set()
        for ci in cis:
            if ci in skip_cells:
                continue
            kc = kcl[ci]
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


def load_session(session_dir: Path | None = None) -> None:
    build_dir = session_dir or (config.project_dir / "build/session")

    for kcl_path in build_dir.glob("*"):
        kcl_name = kcl_path.name
        if kcl_name not in kcls:
            raise ValueError(f"Unknown KCL {kcl_name}")
        kcl = kcls[kcl_name]
        kcl_dir = build_dir / kcl.name
        loaded_kcl = KCLayout("SESSION_LOAD")
        loaded_kcl.read(kcl_dir / "cells.gds.gz")
        if not kcl_dir.exists():
            continue
        invalid_factories: set[WrappedKCellFunc[Any]] = set()
        with (kcl_dir / "facories.pkl").open("rb") as f:
            factory_infos = pickle.load(f)
        for factory in kcl.factories.values():
            ph = _file_path_hash(factory.file)
            fh = _file_hash(factory.file)
            factory_info = factory_infos.get(factory.name)
            if factory_info is not None:
                factory_dependencies, _, ph_loaded, fh_loaded = factory_info

                if ph_loaded != ph or fh_loaded != fh:
                    invalid_factories |= factory_dependencies
        for factory in set(kcl.factories.values()) - invalid_factories:
            factory_info = factory_infos.get(factory.name)
            if factory_info:
                cache_ = factory_info[1]
                for hk, cn in cache_:
                    # TODO: fix
                    factory.cache[hk] = loaded_kcl[cn]


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

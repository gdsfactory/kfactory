from __future__ import annotations

import functools
import hashlib
from hashlib import sha256
from shutil import rmtree
from typing import TYPE_CHECKING

from .conf import config
from .layout import kcls
from .utilities import save_layout_options

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from .decorators import WrappedKCellFunc


def load_session(session_dir: Path | None = None) -> None:
    build_dir = session_dir or (config.project_dir / "session")
    loaded_factories: set[WrappedKCellFunc[Any]] = set()  # noqa: F841
    for kcl in kcls.values():
        kcl_dir = build_dir / kcl.name
        for factory in kcl.factories.values():
            if factory.name is None:
                continue
            factory_dir = kcl_dir / "_".join(
                (
                    _file_path_hash(factory.file)[-16:],
                    _file_hash(factory.file)[-16:],
                )
            )
            if factory_dir.is_dir():
                factory.load(factory_dir / factory.name / "cells.gds.gz")


def save_session(session_dir: Path | None = None) -> None:
    build_dir = session_dir or (config.project_dir / "session")
    rmtree(build_dir)
    for kcl in kcls.values():
        kcl_dir = build_dir / kcl.name
        for factory in kcl.factories.values():
            if factory.cache:
                factory_dir = kcl_dir / "_".join(
                    (
                        sha256(str(factory.file).encode()).hexdigest()[-16:],
                        _file_hash(factory.file)[-16:],
                    )
                )
                factory_dir.mkdir(parents=True, exist_ok=True)
                factory.dump(factory_dir, save_options=save_layout_options())


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

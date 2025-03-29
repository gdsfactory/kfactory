from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from pydantic import BaseModel

from . import kdb
from .conf import config

if TYPE_CHECKING:
    from pathlib import Path


def _file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class FileCache(BaseModel):
    path: Path
    parents: list[Path]
    factories: list[str]

    @property
    def location_hash(self) -> str:
        """Hash of the file's path (location)."""
        return hashlib.sha256(str(self.path).encode("utf-8")).hexdigest()

    @property
    def content_hash(self) -> str:
        """Hash of the file's content."""
        return _file_hash(self.path)


class SessionManger:
    def load_session(self) -> None:
        build_dir = config.root_dir / "build"
        self.session_dir = build_dir / "session"

    def get_factory_cache(self, path_hash: str, file_hash: str) -> kdb.Layout:
        ly = kdb.Layout()
        ly.read(str(config.root_dir / "build" / path_hash / file_hash / "layout.oas"))
        return ly

    # @property
    # def

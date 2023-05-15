"""KFactory types."""

from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

from kfactory.kcell import KCell

CellFactory = Callable[..., KCell]
CellSpec: TypeAlias = str | CellFactory | KCell | dict[str, CellFactory | KCell]
PathType: TypeAlias = str | Path

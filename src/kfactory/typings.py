from collections.abc import Callable
from pathlib import Path

from kfactory.kcell import KCell

CellFactory = Callable[..., KCell]
CellSpec = str | CellFactory | KCell | dict[str, CellFactory | KCell]
PathType = str | Path

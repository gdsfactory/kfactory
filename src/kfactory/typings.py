from pathlib import Path
from typing import Any, Callable, Type, Union

from kfactory.kcell import KCell

CellFactory = Callable[..., KCell]
CellSpec = str | CellFactory | KCell | dict[str, CellFactory | KCell]
PathType = str | Path

from pathlib import Path
from typing import Any, Callable, Dict, Type, Union

from kfactory.kcell import KCell

CellSpec = Union[Type[str], KCell | Type[Dict[str, Any]]]
ComponentFactory = Callable[..., KCell]
ComponentSpec = Union[str, ComponentFactory, KCell, Dict[str, Any]]
PathType = Union[str, Path]

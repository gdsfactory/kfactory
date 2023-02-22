from typing import Any, Dict, Type, Union, Callable

from .kcell import KCell

CellSpec = Union[Type[str], KCell | Type[Dict[str, Any]]]
ComponentFactory = Callable[..., KCell]
ComponentSpec = Union[
    str, ComponentFactory, KCell, Dict[str, Any]
]
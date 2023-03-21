from typing import Callable, Dict
from .DCs import coupler, straight_coupler
from .mzi import mzi

import kfactory as kf

__all__ = [
    "coupler",
    "mzi",
    "straight_coupler",
]

components: Dict[str, Callable[..., kf.kcell.KCell]] = {
    "coupler": coupler,
    "mzi": mzi,
    "straight_coupler": straight_coupler,
}

# flake8: noqa
from typing import Callable

import kfactory as kf

from .bezier import bend_s
from .circular import bend_circular
from .DCs import coupler, straight_coupler
from .euler import bend_euler, bend_s_euler
from .mzi import mzi
from .taper import taper
from .waveguide import waveguide

__all__ = [
    "bend_s",
    "bend_circular",
    "bend_euler",
    "bend_s_euler",
    "taper",
    "waveguide",
]

pcells: dict[str, Callable[..., kf.kcell.KCell]] = {
    "bend_s": bend_s,
    "bend_circular": bend_circular,
    "bend_euler": bend_euler,
    "bend_s_euler": bend_s_euler,
    "coupler": coupler,
    "straight_coupler": straight_coupler,
    "mzi": mzi,
    "taper": taper,
    "waveguide": waveguide,
}

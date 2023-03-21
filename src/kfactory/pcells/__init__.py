# flake8: noqa
from .bezier import bend_s
from .circular import bend_circular
from .euler import bend_euler, bend_s_euler
from .taper import taper as taper_function
from .waveguide import waveguide as wg

import kfactory as kf

from typing import Callable

__all__ = [
    "bend_s",
    "bend_circular",
    "bend_euler",
    "bend_s_euler",
    "taper",
    "waveguide",
]

pcells: dict[str, Callable[..., kf.kcell.KCell]] = {  # type: ignore
    "bend_s": bend_s,
    "bend_circular": bend_circular,
    "bend_euler": bend_euler,
    "bend_s_euler": bend_s_euler,
    "taper": taper_function,
    "waveguide": wg,
}

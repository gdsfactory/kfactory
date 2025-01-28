"""Euler bends.

Euler bends are bends with a constantly changing radius
from zero to a maximum radius and back to 0 at the other
end.

There are two kinds of euler bends. One that snaps the ports and one that doesn't.
All the default bends use snapping. To use no snapping make an instance of
BendEulerCustom(KCell.kcl) and use that one.
"""

from ..factories.euler import bend_euler_factory, bend_s_euler_factory
from ..layout import kcl

__all__ = [
    "bend_euler",
    "bend_s_euler",
]


bend_euler = bend_euler_factory(kcl)
bend_s_euler = bend_s_euler_factory(kcl)

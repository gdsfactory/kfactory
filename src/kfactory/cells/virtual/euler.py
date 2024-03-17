"""Virtual euler cells."""

from ...factories.virtual.euler import virtual_bend_euler_factory
from ...kcell import kcl

__all__ = ["virtual_bend_euler"]

virtual_bend_euler = virtual_bend_euler_factory(kcl)

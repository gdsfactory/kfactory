"""Virtual euler cells."""

from ...factories.virtual.euler import virtual_bend_euler_factory
from .. import demo

__all__ = ["virtual_bend_euler"]

virtual_bend_euler = virtual_bend_euler_factory(kcl=demo)
"""Virtual euler bend on the default KCLayout.

Created by [`virtual_bend_euler_factory`][kfactory.factories.virtual.euler.virtual_bend_euler_factory].
"""  # noqa: E501

"""Virtual circular cells."""

from kfactory.factories.virtual.circular import virtual_bend_circular_factory
from kfactory.layout import kcl

__all__ = ["virtual_bend_circular"]

virtual_bend_circular = virtual_bend_circular_factory(kcl)

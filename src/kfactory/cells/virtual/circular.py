"""Virtual circular cells."""

from ...factories.virtual.circular import virtual_bend_circular_factory
from .. import demo

__all__ = ["virtual_bend_circular"]

virtual_bend_circular = virtual_bend_circular_factory(kcl=demo)
"""Virtual circular bend on the default KCLayout.

Created by [`virtual_bend_circular_factory`][kfactory.factories.virtual.circular.virtual_bend_circular_factory].
"""  # noqa: E501

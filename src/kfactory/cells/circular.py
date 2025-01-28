"""Circular bends.

A circular bend has a constant radius.
"""

from ..factories.circular import bend_circular_factory
from ..layout import kcl

__all__ = ["bend_circular"]


bend_circular = bend_circular_factory(kcl)
"""Circular bend on the default KCLayout."""

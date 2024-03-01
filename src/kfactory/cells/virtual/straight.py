"""Straight virtual waveguide cells."""

from ...factories.virtual.straight import virtual_straight_factory
from ...kcell import kcl

virtual_straight = virtual_straight_factory(kcl)
"""Default straight on the "default" kcl."""

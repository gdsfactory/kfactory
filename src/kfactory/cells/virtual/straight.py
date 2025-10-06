"""Straight virtual waveguide cells."""

from ...factories.virtual.straight import virtual_straight_factory
from .. import demo

virtual_straight = virtual_straight_factory(kcl=demo)
"""Default straight on the "default" kcl."""

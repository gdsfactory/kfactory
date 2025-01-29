"""Straight virtual waveguide cells."""

from kfactory.factories.virtual.straight import virtual_straight_factory
from kfactory.layout import kcl

virtual_straight = virtual_straight_factory(kcl)
"""Default straight on the "default" kcl."""

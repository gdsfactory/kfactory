"""Bezier curve based bends and functions."""

from kfactory.factories.bezier import bend_s_bezier_factory
from kfactory.layout import kcl

__all__ = ["bend_s"]


bend_s = bend_s_bezier_factory(kcl)

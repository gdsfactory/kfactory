"""Bezier curve based bends and functions."""

from ..factories.bezier import bend_s_bezier_factory
from ..layout import kcl

__all__ = ["bend_s"]


bend_s = bend_s_bezier_factory(kcl)

"""Utilities to provide geometrical, fill and DRC violation help.

[fill_tiled][kfactory.utils.fill_tiled] provides a filling algorithm that can use
the `klayout.db.TilingProcessor` to calculate the regions to fill.

[fix_spacing][kfactory.utils.violations.fix_spacing_tiled] uses a region space check to
calculate areas that violate min space violations.
"""

from .fill import fill_tiled
from .simplify import dsimplify, simplify
from .violations import fix_spacing_minkowski_tiled, fix_spacing_tiled
from .difftest import difftest, diff, xor

__all__ = [
    "dsimplify",
    "fill_tiled",
    "fix_spacing_minkowski_tiled",
    "fix_spacing_tiled",
    "simplify",
    "difftest",
    "diff",
    "xor",
]

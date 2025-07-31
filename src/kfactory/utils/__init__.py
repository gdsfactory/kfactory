"""Utilities to provide geometrical, fill and DRC violation help.

[fill_tiled][kfactory.utils.fill_tiled] provides a filling algorithm that can use
the `klayout.db.TilingProcessor` to calculate the regions to fill.

[fix_spacing][kfactory.utils.violations.fix_spacing_tiled] uses a region space check to
calculate areas that violate min space violations.
"""

from .difftest import diff, difftest, xor
from .fill import fill_tiled
from .simplify import dsimplify, simplify
from .violations import fix_spacing_minkowski_tiled, fix_spacing_tiled

__all__ = [
    "diff",
    "difftest",
    "dsimplify",
    "fill_tiled",
    "fix_spacing_minkowski_tiled",
    "fix_spacing_tiled",
    "simplify",
    "xor",
]

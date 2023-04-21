"""Utilities to provide geometrical, fill and DRC violation help.

:py:class:~`Enclosures can automatically generate slab and excludes based on minkowski
sums instead of only vector based sizing.

:py:func:~`fill_tiled` provides a filling algorithm that can use the
:py:class:~`klayout.db.TilingProcessor` to calculate the regions to fill.

:py:func:~`fix_spacing` uses a region space check to calculate areas that violate
min space violations. :py:func:~`fix_spacing_tiled` to fix it using a TilingProcessor.
"""

from .enclosure import (
    Direction,
    Enclosure,
    clean_points,
    extrude_path,
    extrude_path_dynamic,
)
from .fill import fill_tiled
from .violations import fix_spacing_minkowski_tiled, fix_spacing_tiled

__all__ = [
    "Enclosure",
    "violations",
    "Direction",
    "geo",
    "extrude_path",
    "extrude_path_dynamic",
    "fill_tiled",
    "fix_spacing_tiled",
    "fix_spacing_minkowski_tiled",
    "clean_points",
]

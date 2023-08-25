"""Utilities to provide geometrical, fill and DRC violation help.

[Enclosures][kfactory.utils.enclosure.LayerEnclosure] can automatically generate slab
and excludes based on minkowski sums instead of only vector based sizing.

[fill_tiled][kfactory.utils.fill_tiled] provides a filling algorithm that can use
the `klayout.db.TilingProcessor` to calculate the regions to fill.

[fix_spacing][kfactory.utils.violations.fix_spacing_tiled] uses a region space check to
calculate areas that violate min space violations.
"""

# from .enclosure import (
#     Direction,
#     KCellEnclosure,
#     LayerEnclosure,
#     clean_points,
#     extrude_path,
#     extrude_path_dynamic,
# )

from .fill import fill_tiled
from .violations import fix_spacing_minkowski_tiled, fix_spacing_tiled

__all__ = [
    "fill_tiled",
    "fix_spacing_tiled",
    "fix_spacing_minkowski_tiled",
]

from __future__ import annotations

from typing import List, Optional, Tuple

import kfactory as kf
from .kcell import cell
from .kcell import KCell    
from .types import ComponentSpec


def get_padding_points(
    component: KCell,
    default: float = 50.0,
    top: Optional[float] = None,
    bottom: Optional[float] = None,
    right: Optional[float] = None,
    left: Optional[float] = None,
) -> List[float]:
    """Returns padding points for a component outline.

    Args:
        component: to add padding.
        default: default padding in um.
        top: north padding in um.
        bottom: south padding in um.
        right: east padding in um.
        left: west padding in um.
    """
    c = component
    top = top if top is not None else default
    bottom = bottom if bottom is not None else default
    right = right if right is not None else default
    left = left if left is not None else default
    xmin = c.bbox().left
    ymin = c.bbox().bottom
    xmax = c.bbox().right
    ymax = c.bbox().top
    return [
        [xmin - left, ymin - bottom],
        [xmax + right, ymin - bottom],
        [xmax + right, ymax + top],
        [xmin - left, ymax + top],
    ]
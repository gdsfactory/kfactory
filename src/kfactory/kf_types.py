"""KFactory types.

Mainly units for annotating types.
"""

from typing import Annotated

from . import kdb
from .kcell import (
    LayerEnum,
)

um = Annotated[float, "um"]
"""Float in micrometer."""
dbu = Annotated[int, "dbu"]
"""Integer in database units."""
deg = Annotated[float, "deg"]
"""Float in degrees."""
rad = Annotated[float, "rad"]
"""Float in radians."""
layer = Annotated[int | LayerEnum, "layer"]
"""Integer or enum index of a Layer."""
layer_info = Annotated[kdb.LayerInfo, "layer info"]

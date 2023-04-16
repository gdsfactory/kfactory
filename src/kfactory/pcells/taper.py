r"""Tapers, linear only.

TODO: Non-linear tapers.

"""


from .. import KCell, LayerEnum, klib
from ..utils import Enclosure
from .dbu.taper import taper as taper_dbu

__all__ = ["taper", "taper_dbu"]


def taper(
    width1: float,
    width2: float,
    length: float,
    layer: int | LayerEnum,
    enclosure: Enclosure | None = None,
) -> KCell:
    r"""Linear Taper [um].

    Visualization::

               __
             _/  │ Slab/Exclude
           _/  __│
         _/  _/  │
        │  _/    │
        │_/      │
        │_       │ Core
        │ \_     │
        │_  \_   │
          \_  \__│
            \_   │
              \__│ Slab/Exclude

    Args:
        width1: Width of the core on the left side. [um]
        width2: Width of the core on the right side. [um]
        length: Length of the taper. [um]
        layer: Layer index / :py:class:~`LayerEnum` of the core.
        enclosure: Definition of the slab/exclude.
    """
    return taper_dbu(
        width1=int(width1 / klib.dbu),
        width2=int(width2 / klib.dbu),
        length=int(length / klib.dbu),
        layer=layer,
        enclosure=enclosure,
    )

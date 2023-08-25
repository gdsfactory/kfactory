r"""Tapers, linear only.

TODO: Non-linear tapers.

"""


from .. import KCell, LayerEnum, kcl
from ..enclosure import LayerEnclosure
from .dbu.taper import taper as taper_dbu

__all__ = ["taper", "taper_dbu"]


def taper(
    width1: float,
    width2: float,
    length: float,
    layer: int | LayerEnum,
    enclosure: LayerEnclosure | None = None,
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
        layer: Main layer of the taper.
        enclosure: Definition of the slab/exclude.
    """
    return taper_dbu(
        width1=int(width1 / kcl.dbu),
        width2=int(width2 / kcl.dbu),
        length=int(length / kcl.dbu),
        layer=layer,
        enclosure=enclosure,
    )

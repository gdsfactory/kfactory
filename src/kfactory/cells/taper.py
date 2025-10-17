r"""Tapers, linear only.

TODO: Non-linear tapers.

"""

from .. import KCell, kdb
from ..enclosure import LayerEnclosure
from ..factories.taper import taper_factory
from ..typings import um
from . import demo

__all__ = ["taper", "taper_dbu"]

taper_dbu = taper_factory(kcl=demo)


def taper(
    width1: um,
    width2: um,
    length: um,
    layer: kdb.LayerInfo,
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
        width1=demo.to_dbu(width1),
        width2=demo.to_dbu(width2),
        length=demo.to_dbu(length),
        layer=layer,
        enclosure=enclosure,
    )

r"""Tapers, linear only.

TODO: Non-linear tapers.

"""

from .. import KCell, kcl, kf_types
from ..enclosure import LayerEnclosure
from ..factories.taper import taper_factory

__all__ = ["taper", "taper_dbu"]

taper_dbu = taper_factory(kcl)


def taper(
    width1: kf_types.um,
    width2: kf_types.um,
    length: kf_types.um,
    layer: kf_types.layer,
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

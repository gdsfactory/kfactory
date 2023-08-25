r"""Tapers, linear only.

TODO: Non-linear tapers.

"""


from collections.abc import Callable

from .. import KCell, KCLayout, LayerEnum
from ..enclosure import LayerEnclosure
from .dbu.taper import custom_taper as custom_taper_dbu

__all__ = ["custom_taper", "custom_taper_dbu"]


def custom_taper(kcl: KCLayout) -> Callable[..., KCell]:
    """Taper with a custom KCLayout."""

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
        return custom_taper_dbu(kcl)(
            width1=int(width1 / kcl.dbu),
            width2=int(width2 / kcl.dbu),
            length=int(length / kcl.dbu),
            layer=layer,
            enclosure=enclosure,
        )

    return taper

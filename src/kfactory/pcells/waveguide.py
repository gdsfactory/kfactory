"""Provides straight waveguides in dbu and um versions.

A waveguide is a rectangle of material with excludes and/or slab around it::

    ┌─────────────────────────────┐
    │        Slab/Exclude         │
    ├─────────────────────────────┤
    │                             │
    │            Core             │
    │                             │
    ├─────────────────────────────┤
    │        Slab/Exclude         │
    └─────────────────────────────┘

The slabs and excludes can be given in the form of an :py:class:~`Enclosure`.
"""


from .. import KCell, LayerEnum, klib
from ..utils import Enclosure
from .dbu.waveguide import waveguide as waveguide_dbu

__all__ = ["waveguide", "waveguide_dbu"]


def waveguide(
    width: float,
    length: float,
    layer: int | LayerEnum,
    enclosure: Enclosure | None = None,
) -> KCell:
    """Straight waveguide in um.

    Visualization::

        ┌─────────────────────────────┐
        │        Slab/Exclude         │
        ├─────────────────────────────┤
        │                             │
        │            Core             │
        │                             │
        ├─────────────────────────────┤
        │        Slab/Exclude         │
        └─────────────────────────────┘

    Args:
        width: Width of the waveguide. [um]
        length: Length of the waveguide. [um]
        layer: Layer index / :py:class:~`LayerEnum`
        enclosure: Definition of slabs/excludes. [um]
    """
    return waveguide_dbu(
        int(width / klib.dbu), int(length / klib.dbu), layer, enclosure=enclosure
    )

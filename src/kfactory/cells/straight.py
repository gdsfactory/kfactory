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

The slabs and excludes can be given in the form of an
[Enclosure][kfactory.enclosure.LayerEnclosure].
"""

from .. import KCell, kdb
from ..enclosure import LayerEnclosure
from ..factories.straight import straight_dbu_factory
from ..typings import um
from . import demo

__all__ = ["straight", "straight_dbu"]

straight_dbu = straight_dbu_factory(kcl=demo)


def straight(
    width: um,
    length: um,
    layer: kdb.LayerInfo,
    enclosure: LayerEnclosure | None = None,
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
        width: Width of the straight. [um]
        length: Length of the straight. [um]
        layer: Main layer of the straight.
        enclosure: Definition of slabs/excludes. [um]
    """
    return straight_dbu(
        width=demo.to_dbu(width),
        length=demo.to_dbu(length),
        layer=layer,
        enclosure=enclosure,
    )

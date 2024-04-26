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
[Enclosure][kfactory.enclosure.LayerEncolosure].
"""

from .. import KCell, kcl, kf_types
from ..enclosure import LayerEnclosure
from ..factories.straight import straight_dbu_factory

__all__ = ["straight", "straight_dbu"]

straight_dbu = straight_dbu_factory(kcl)


def straight(
    width: kf_types.um,
    length: kf_types.um,
    layer: kf_types.layer,
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
        width=round(width / kcl.dbu),
        length=round(length / kcl.dbu),
        layer=layer,
        enclosure=enclosure,
    )

"""Straight waveguide in dbu.

A waveguide is a rectangle of material with excludes and/or slab around it::

    ┌──────────────────────────────┐
    │         Slab/Exclude         │
    ├──────────────────────────────┤
    │                              │
    │             Core             │
    │                              │
    ├──────────────────────────────┤
    │         Slab/Exclude         │
    └──────────────────────────────┘

The slabs and excludes can be given in the form of an
[Enclosure][kfactory.utils.LayerEnclosure].
"""

from ... import KCell, LayerEnum, cell, kdb
from ...utils import LayerEnclosure

__all__ = ["waveguide"]


@cell
def waveguide(
    width: int,
    length: int,
    layer: int | LayerEnum,
    enclosure: LayerEnclosure | None = None,
) -> KCell:
    """Waveguide defined in dbu.

        ┌──────────────────────────────┐
        │         Slab/Exclude         │
        ├──────────────────────────────┤
        │                              │
        │             Core             │
        │                              │
        ├──────────────────────────────┤
        │         Slab/Exclude         │
        └──────────────────────────────┘
    Args:
        width: Waveguide width. [dbu]
        length: Waveguide length. [dbu]
        layer: Main layer of the waveguide.
        enclosure: Definition of slab/excludes. [dbu]
    """
    c = KCell()

    if width // 2 * 2 != width:
        raise ValueError("The width (w) must be a multiple of 2 database units")

    c.shapes(layer).insert(kdb.Box(0, -width // 2, length, width // 2))
    c.create_port(trans=kdb.Trans(2, False, 0, 0), layer=layer, width=width)
    c.create_port(trans=kdb.Trans(0, False, length, 0), layer=layer, width=width)

    if enclosure is not None:
        enclosure.apply_minkowski_y(c, layer)
    c.settings = {
        "width_um": width * c.kcl.dbu,
        "length_um": length * c.kcl.dbu,
        "layer": layer,
    }
    c.autorename_ports()
    return c

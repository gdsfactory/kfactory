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

The slabs and excludes are part of the cross section, or can be given for the legacy
``(width, layer, enclosure)`` call via a
[`LayerEnclosure`][kfactory.enclosure.LayerEnclosure].
"""

from typing import overload

from .. import KCell, kdb
from ..cross_section import (
    CrossSection,
    CrossSectionSpec,
    DCrossSection,
    DCrossSectionSpec,
)
from ..enclosure import LayerEnclosure
from ..factories.straight import straight_dbu_factory
from ..typings import um
from . import demo

__all__ = ["straight", "straight_dbu"]

straight_dbu = straight_dbu_factory(kcl=demo)
"""Cross-section-first straight factory on the default KCLayout (length in dbu)."""


@overload
def straight(
    *,
    width: um,
    length: um,
    layer: kdb.LayerInfo,
    enclosure: LayerEnclosure | None = None,
) -> KCell: ...
@overload
def straight(
    *,
    cross_section: str
    | CrossSection
    | DCrossSection
    | CrossSectionSpec
    | DCrossSectionSpec,
    length: um,
) -> KCell: ...
def straight(
    *,
    length: um,
    cross_section: str
    | CrossSection
    | DCrossSection
    | CrossSectionSpec
    | DCrossSectionSpec
    | None = None,
    width: um | None = None,
    layer: kdb.LayerInfo | None = None,
    enclosure: LayerEnclosure | None = None,
) -> KCell:
    """Straight waveguide in um.

    Either pass a ``cross_section`` (name, spec, or instance) or the legacy
    ``width``/``layer``/``enclosure``.

    Args:
        length: Length of the straight. [um]
        cross_section: Cross section of the straight.
        width: Width of the core. [um] (legacy; requires ``layer``)
        layer: Main layer of the straight. (legacy)
        enclosure: Definition of slabs/excludes. (legacy)
    """
    if cross_section is not None:
        return straight_dbu(cross_section=cross_section, length=demo.to_dbu(length))
    if width is None or layer is None:
        raise ValueError("Provide a cross_section, or width and layer (legacy call).")
    return straight_dbu(
        width=demo.to_dbu(width),
        length=demo.to_dbu(length),
        layer=layer,
        enclosure=enclosure,
    )

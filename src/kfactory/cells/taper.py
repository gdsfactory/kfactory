r"""Tapers, linear only.

A linear taper transitions between two cross sections (two core widths). The slabs
and excludes are part of the cross sections, or can be given for the legacy
``(width1, width2, layer, enclosure)`` call via a
[`LayerEnclosure`][kfactory.enclosure.LayerEnclosure].

TODO: Non-linear tapers.

"""

from typing import overload

from .. import KCell, kdb
from ..cross_section import (
    CrossSection,
    CrossSectionSpecDict,
    DCrossSection,
    DCrossSectionSpecDict,
)
from ..enclosure import LayerEnclosure
from ..factories.taper import taper_factory
from ..typings import um
from . import demo

__all__ = ["taper", "taper_dbu"]

taper_dbu = taper_factory(kcl=demo)
"""Cross-section-first taper factory on the default KCLayout (length in dbu)."""


@overload
def taper(
    *,
    width1: um,
    width2: um,
    length: um,
    layer: kdb.LayerInfo,
    enclosure: LayerEnclosure | None = None,
) -> KCell: ...
@overload
def taper(
    *,
    cross_section1: str
    | CrossSection
    | DCrossSection
    | CrossSectionSpecDict
    | DCrossSectionSpecDict,
    cross_section2: str
    | CrossSection
    | DCrossSection
    | CrossSectionSpecDict
    | DCrossSectionSpecDict,
    length: um,
) -> KCell: ...
def taper(
    *,
    length: um,
    cross_section1: str
    | CrossSection
    | DCrossSection
    | CrossSectionSpecDict
    | DCrossSectionSpecDict
    | None = None,
    cross_section2: str
    | CrossSection
    | DCrossSection
    | CrossSectionSpecDict
    | DCrossSectionSpecDict
    | None = None,
    width1: um | None = None,
    width2: um | None = None,
    layer: kdb.LayerInfo | None = None,
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

    Either pass two cross sections (``cross_section1``/``cross_section2``) or the
    legacy ``width1``/``width2``/``layer``/``enclosure``.

    Args:
        length: Length of the taper. [um]
        cross_section1: Cross section of the left side.
        cross_section2: Cross section of the right side.
        width1: Width of the core on the left side. [um] (legacy; requires ``layer``)
        width2: Width of the core on the right side. [um] (legacy; requires ``layer``)
        layer: Main layer of the taper. (legacy)
        enclosure: Definition of the slab/exclude. (legacy)
    """
    if cross_section1 is not None and cross_section2 is not None:
        return taper_dbu(
            cross_section1=cross_section1,
            cross_section2=cross_section2,
            length=demo.to_dbu(length),
        )
    if width1 is None or width2 is None or layer is None:
        raise ValueError(
            "Provide cross_section1 and cross_section2, or width1, width2 and layer"
            " (legacy call)."
        )
    return taper_dbu(
        width1=demo.to_dbu(width1),
        width2=demo.to_dbu(width2),
        length=demo.to_dbu(length),
        layer=layer,
        enclosure=enclosure,
    )

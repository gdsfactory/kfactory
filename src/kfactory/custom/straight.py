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


from collections.abc import Callable

from .. import KCell, KCLayout, LayerEnum
from ..enclosure import LayerEnclosure
from .dbu.straight import custom_straight as custom_straight_dbu

__all__ = ["custom_straight"]


def custom_straight(kcl: KCLayout) -> Callable[..., KCell]:
    """Straight with a custom KCLayout."""

    def straight(
        width: float,
        length: float,
        layer: int | LayerEnum,
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
        return custom_straight_dbu(kcl)(
            int(width / kcl.dbu), int(length / kcl.dbu), layer, enclosure=enclosure
        )

    return straight

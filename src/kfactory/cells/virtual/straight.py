"""Straight virtual waveguide cells."""

from ... import kdb
from ...conf import config
from ...enclosure import LayerEnclosure
from ...kcell import KCLayout, LayerEnum, VKCell, kcl, vcell
from .utils import extrude_backbone

__all__ = ["Straight", "straight"]


class Straight:
    """Virtual waveguide defined in um.

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
        width: Waveguide width. [um]
        length: Waveguide length. [um]
        layer: Main layer of the waveguide.
        enclosure: Definition of slab/excludes. [dbu]
    """

    kcl: KCLayout

    def __init__(self, kcl: KCLayout):
        """Initialize A straight class on a defined KCLayout."""
        self.kcl = kcl

    @vcell
    def __call__(
        self,
        width: float,
        length: float,
        layer: int | LayerEnum,
        enclosure: LayerEnclosure | None = None,
    ) -> VKCell:
        """Virtual waveguide defined in um.

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
            width: Waveguide width. [um]
            length: Waveguide length. [um]
            layer: Main layer of the waveguide.
            enclosure: Definition of slab/excludes. [dbu]
        """
        c = VKCell(kcl=self.kcl)
        if length < 0:
            config.logger.critical(
                f"Negative lengths are not allowed {length} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length = -length
        if width < 0:
            config.logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width

        extrude_backbone(
            c,
            backbone=[kdb.DPoint(0, 0), kdb.DPoint(length, 0)],
            width=width,
            layer=layer,
            enclosure=enclosure,
            start_angle=0,
            end_angle=0,
            dbu=c.kcl.dbu,
        )

        c.create_port(
            name="o1",
            dcplx_trans=kdb.DCplxTrans(1, 180, False, 0, 0),
            layer=layer,
            dwidth=width,
        )
        c.create_port(
            name="o2",
            dcplx_trans=kdb.DCplxTrans(1, 0, False, length, 0),
            layer=layer,
            dwidth=width,
        )
        return c


straight = Straight(kcl)
"""Default straight on the "default" kcl."""

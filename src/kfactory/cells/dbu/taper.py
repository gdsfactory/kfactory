"""Taper definitions [dbu].

TODO: Non-linear tapers
"""

from ... import KCell, KCLayout, cell, kcl, kdb
from ...conf import config
from ...enclosure import LayerEnclosure
from ...kcell import Info

__all__ = ["taper"]


class Taper:
    kcl: KCLayout

    def __init__(self, kcl: KCLayout) -> None:
        self.kcl = kcl

    @cell
    def __call__(
        self,
        width1: int,
        width2: int,
        length: int,
        layer: int,
        enclosure: LayerEnclosure | None = None,
    ) -> KCell:
        r"""Linear Taper [um].

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
            width1: Width of the core on the left side. [dbu]
            width2: Width of the core on the right side. [dbu]
            length: Length of the taper. [dbu]
            layer: Main layer of the taper.
            enclosure: Definition of the slab/exclude.
        """
        return self._kcell(
            width1=width1,
            width2=width2,
            length=length,
            layer=layer,
            enclosure=enclosure,
        )

    def _kcell(
        self,
        width1: int,
        width2: int,
        length: int,
        layer: int,
        enclosure: LayerEnclosure | None = None,
    ) -> KCell:
        r"""Linear Taper [um].

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
            width1: Width of the core on the left side. [dbu]
            width2: Width of the core on the right side. [dbu]
            length: Length of the taper. [dbu]
            layer: Main layer of the taper.
            enclosure: Definition of the slab/exclude.
        """
        c = self.kcl.kcell()
        if length < 0:
            config.logger.critical(
                f"Negative lengths are not allowed {length} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length = -length
        if width1 < 0:
            config.logger.critical(
                f"Negative widths are not allowed {width1} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width1 = -width1

        if width2 < 0:
            config.logger.critical(
                f"Negative widths are not allowed {width2} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width2 = -width2

        taper = c.shapes(layer).insert(
            kdb.Polygon(
                [
                    kdb.Point(0, int(-width1 / 2)),
                    kdb.Point(0, width1 // 2),
                    kdb.Point(length, width2 // 2),
                    kdb.Point(length, int(-width2 / 2)),
                ]
            )
        )

        c.create_port(trans=kdb.Trans(2, False, 0, 0), width=width1, layer=layer)
        c.create_port(trans=kdb.Trans(0, False, length, 0), width=width2, layer=layer)

        if enclosure is not None:
            enclosure.apply_minkowski_y(c, layer)
        c.info = Info(
            **{
                "width1_um": width1 * c.kcl.dbu,
                "width2_um": width2 * c.kcl.dbu,
                "length_um": length * c.kcl.dbu,
                "width1_dbu": width1,
                "width2_dbu": width2,
                "length_dbu": length,
            }
        )
        c.auto_rename_ports()
        c.boundary = taper.dpolygon

        return c


taper = Taper(kcl)

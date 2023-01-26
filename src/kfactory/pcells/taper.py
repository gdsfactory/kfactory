from typing import Optional

from .. import KCell, LayerEnum, autocell, kdb, library
from ..utils import Enclosure

__all__ = ["taper", "taper_dbu"]


@autocell(set_settings=False)
def taper(
    width1: float,
    width2: float,
    length: float,
    layer: int | LayerEnum,
    enclosure: Optional[Enclosure] = None,
) -> KCell:
    return taper_dbu(
        width1=width1 * library.dbu,
        width2=width2 * library.dbu,
        length=length * library.dbu,
        layer=layer,
        enclosure=enclosure,
    )


@autocell
def taper_dbu(
    width1: int,
    width2: int,
    length: int,
    layer: int,
    enclosure: Optional[Enclosure] = None,
) -> KCell:
    c = KCell()

    c.shapes(layer).insert(
        kdb.Polygon(
            [
                kdb.Point(0, int(-width1 / 2)),
                kdb.Point(0, width1 // 2),
                kdb.Point(length, width2 // 2),
                kdb.Point(length, int(-width2 / 2)),
            ]
        )
    )

    c.create_port(name="o1", trans=kdb.Trans(2, False, 0, 0), width=width1, layer=layer)
    c.create_port(
        name="o2", trans=kdb.Trans(0, False, length, 0), width=width2, layer=layer
    )

    if enclosure is not None:
        enclosure.apply_minkowski_y(c, kdb.Region(c.bbox()))
    c.settings["width1_um"] = width1 / c.library.dbu
    c.settings["width2_um"] = width2 / c.library.dbu
    c.settings["length_um"] = length / c.library.dbu

    return c

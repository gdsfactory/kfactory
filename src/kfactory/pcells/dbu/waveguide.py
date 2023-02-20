from typing import Optional

from ... import KCell, LayerEnum, autocell, kdb, klib
from ...utils import Enclosure

__all__ = ["waveguide"]


@autocell
def waveguide(
    width: int,
    length: int,
    layer: int | LayerEnum,
    enclosure: Optional[Enclosure] = None,
) -> KCell:
    c = KCell()

    if width // 2 * 2 != width:
        raise ValueError("The width (w) must be a multiple of 2 database units")

    c.shapes(layer).insert(kdb.Box(0, -width // 2, length, width // 2))
    c.create_port(name="o1", trans=kdb.Trans(2, False, 0, 0), layer=layer, width=width)
    c.create_port(
        name="o2", trans=kdb.Trans(0, False, length, 0), layer=layer, width=width
    )

    if enclosure is not None:
        enclosure.apply_minkowski_y(c, layer)
    c.settings = {
        "width_dbu": width,
        "length_dbu": length,
        "width_um": width / c.klib.dbu,
        "length_um": length / c.klib.dbu,
        "layer": layer,
    }
    c.autorename_ports()
    return c

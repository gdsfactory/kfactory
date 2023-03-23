from typing import Optional

from ... import KCell, LayerEnum, autocell, kdb, klib
from ...pdk import _ACTIVE_PDK
from ...utils import Enclosure

__all__ = ["waveguide"]


@autocell
def waveguide(
    width: int,
    length: int,
    layer: int | LayerEnum | str,
    enclosure: Optional[Enclosure] = None,
) -> KCell:
    c = KCell()

    layer_: LayerEnum = (
        _ACTIVE_PDK.get_layer(layer)[0] if isinstance(layer, str) else layer
    )
    if width // 2 * 2 != width:
        raise ValueError("The width (w) must be a multiple of 2 database units")

    c.shapes(layer_).insert(kdb.Box(0, -width // 2, length, width // 2))
    c.create_port(name="o1", trans=kdb.Trans(2, False, 0, 0), layer=layer_, width=width)
    c.create_port(
        name="o2", trans=kdb.Trans(0, False, length, 0), layer=layer_, width=width
    )

    if enclosure is not None:
        enclosure.apply_minkowski_y(c, layer_)
    c.settings = {
        "width_um": width * c.klib.dbu,
        "length_um": length * c.klib.dbu,
        "layer": layer,
    }
    c.autorename_ports()

    return c

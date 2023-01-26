from ... import KCell, LayerEnum, autocell, kdb, library
from ...utils import Enclosure

__all__ = ["waveguide_dbu"]


@autocell
def waveguide(width: int, length: int, layer: int | LayerEnum) -> KCell:
    c = KCell()

    if width // 2 * 2 != width:
        raise ValueError(f"The width (w) must be a multiple of 2 database units")

    c.shapes(layer).insert(kdb.Box(0, -width // 2, length, width // 2))
    c.create_port(name="o1", trans=kdb.Trans(2, False, 0, 0), layer=layer, width=width)

    c.settings = {
        "width_dbu": width,
        "length_dbu": length,
        "width_um": width / c.library.dbu,
        "length_um": length / c.library.dbu,
        "layer": layer,
    }

    return c

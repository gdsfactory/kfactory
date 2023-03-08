from .. import kdb
from ..pcells.bezier import bend_s
from ..pcells.waveguide import waveguide
from ..pdk import _ACTIVE_PDK
from ..generic_tech import LAYER, LayerEnum
from ..utils import Enclosure

from .. import autocell, KCell

from typing import Union

@autocell
def coupler(
    gap: float = 0.2,
    length: float = 10.0,
    dy: float = 5.0,
    dx: float = 5.0,
    width: float = 0.5,
    layer: Union[int, LayerEnum, str] = LAYER.WG,
    enclosure: Enclosure = Enclosure(),
):
    r"""Symmetric coupler.
    Args:
        gap: between straights in um.
        length: of coupling region in um.
        dy: port to port vertical spacing in um.
        dx: length of bend in x direction in um.
        layer: layer number or name.
        enclosure: waveguide enclosure.
    .. code::
               dx                                 dx
            |------|                           |------|
         o2 ________                           ______o3
                    \                         /           |
                     \        length         /            |
                      ======================= gap         | dy
                     /                       \            |
            ________/                         \_______    |
         o1                                          o4
    """
    c = KCell()

    layer = _ACTIVE_PDK.get_layer(layer) if isinstance(layer, str) else layer
    enclosure = enclosure if enclosure is not None else Enclosure()
    sbend = c << bend_s(width=width, height=((dy) / 2 - gap / 2 - width / 2), length=dx, layer=layer, enclosure=enclosure)
    sbend_2 = c << bend_s(width=width, height=((dy) / 2 - gap / 2 - width / 2), length=dx, layer=layer, enclosure=enclosure)

    sbend.transform(kdb.DTrans(0, True, 0, (gap - width + dy)))
    sbend_2.transform(kdb.DTrans(2, False, 0, -(gap + width + dy)))

    wg_top = c << waveguide(width, length, layer, enclosure)
    wg_top.trans = kdb.DTrans(0, True, dx, (gap + width) / 2)

    wg_bottom = c << waveguide(width, length, layer, enclosure)
    wg_bottom.trans = kdb.DTrans(0, False, dx, -(gap + width) / 2)

    sbend.connect("E0", wg_top.ports["o1"])
    sbend_2.connect("E0", wg_bottom.ports["o1"])
    sbend_r_top = c << bend_s(width=width, height=(dy / 2 - width / 2 - gap / 2), length=dx, layer=layer, enclosure=enclosure)
    sbend_r_bottom = c << bend_s(width=width, height=(dy / 2 - width / 2 - gap / 2), length=dx, layer=layer, enclosure=enclosure)

    sbend_r_top.connect("E0", wg_top.ports["o2"])
    sbend_r_bottom.connect("E0", wg_bottom.ports["o2"])

    sbend_r_top.transform(kdb.DTrans(0, False, 0, -(gap + width)))
    sbend_r_bottom.transform(kdb.DTrans(0, False, 0, (gap + width)))

    # sbend_r_top.transform(kdb.DTrans(0, False, 0, 0))
    # sbend_r_bottom.transform(kdb.DTrans(0, False, 0, 0))

    c.add_port(name="o1", port=sbend_2.ports["W0"])
    c.add_port(name="o2", port=sbend.ports["W0"])
    c.add_port(name="o3", port=sbend_r_bottom.ports["W0"])
    c.add_port(name="o4", port=sbend_r_top.ports["W0"])

    return c

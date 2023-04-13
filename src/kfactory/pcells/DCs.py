from typing import Union

from .. import KCell, autocell, kdb
from ..generic_tech import LAYER
from ..kcell import LayerEnum
from ..pcells.bezier import bend_s
from ..pcells.waveguide import waveguide
from ..pdk import _ACTIVE_PDK
from ..utils import Enclosure


@autocell
def coupler(
    gap: float = 0.2,
    length: float = 10.0,
    dy: float = 5.0,
    dx: float = 5.0,
    width: float = 0.5,
    layer: Union[int, LayerEnum] = LAYER.WG,
    enclosure: Enclosure = Enclosure(),
) -> KCell:
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
    enclosure = enclosure if enclosure is not None else Enclosure()
    sbend_ = symmetric_coupler(
        gap=gap, length=length, width=width, layer=layer, enclosure=enclosure, height=dy / 2 - width / 2 - gap / 2,
    )
    sbend_ = c << sbend_

    stright_coupl = straight_coupler(gap, length, width, layer, enclosure)
    stright_coupl.ports["o1"].name = "port 1"
    stright_coupl.ports["o2"].name = "port 2"
    stright_coupl.ports["o3"].name = "port 3"
    stright_coupl.ports["o4"].name = "port 4"
    wg = c << stright_coupl

    sbend_.connect("port2", wg.ports["port 4"])
    sbend_.connect("port3", wg.ports["port 1"])
    sbend_3 = symmetric_coupler(
        gap=gap, length=length, width=width, layer=layer, enclosure=enclosure, height=dy / 2 - width / 2 - gap / 2,
    )
    sbend_3 = c << sbend_3

    sbend_3.connect("port4", wg.ports["port 3"])
    sbend_3.connect("port3", wg.ports["port 2"])

    # sbend_r_top.transform(kdb.DTrans(0, False, 0, 0))
    # sbend_r_bottom.transform(kdb.DTrans(0, False, 0, 0))

    c.add_port(name="port1", port=sbend_.ports["port1"])
    c.add_port(name="port2", port=sbend_.ports["port2"])
    c.add_port(name="port3", port=sbend_3.ports["port2"])
    c.add_port(name="port4", port=sbend_3.ports["port1"])
    c.begin_instances_rec()

    return c


@autocell
def symmetric_coupler(
    width: float = 0.5,
    height: float = 0.5,
    gap: float = 0.5,
    length: float = 10.0,
    layer: Union[int, LayerEnum] = LAYER.WG,
    enclosure: Enclosure = Enclosure(),
) -> KCell:
    c = KCell()
    sbend_r_top = c << bend_s(
        width=width,
        height=height,
        length=length,
        layer=layer,
        enclosure=enclosure,
    )
    sbend_r_top.transform(kdb.Trans(0, True, 0, 0))
    sbend_r_bottom = c << bend_s(
        width=width,
        height=height,
        length=length,
        layer=layer,
        enclosure=enclosure,
    )
    sbend_r_bottom.transform(kdb.Trans(0, False, 0, gap / c.klib.dbu + width / c.klib.dbu))

    c.add_port(sbend_r_top.ports["E0"], "port1")
    c.add_port(sbend_r_bottom.ports["E0"], "port2")
    c.add_port(sbend_r_top.ports["W0"], "port3")
    c.add_port(sbend_r_bottom.ports["W0"], "port4")

    return c


@autocell
def straight_coupler(
    gap: float = 0.2,
    length: float = 10.0,
    width: float = 0.5,
    layer: Union[int, LayerEnum] = LAYER.WG,
    enclosure: Enclosure = Enclosure(),
) -> KCell:
    """Straight coupler.

    Args:
        gap: between straights in um.
        length: of coupling region in um.
        layer: layer number or name.
        enclosure: waveguide enclosure.
    """
    c = KCell()

    wg_top = c << waveguide(width, length, layer, enclosure)
    wg_top.trans = kdb.Trans(0, True, 0, int((gap + width) / 2 / c.klib.dbu))

    wg_bottom = c << waveguide(width, length, layer, enclosure)
    wg_bottom.trans = kdb.Trans(0, False, 0, -int((gap + width) / 2 / c.klib.dbu))

    c.add_port(name="o1", port=wg_top.ports["port 1"])
    c.add_port(name="o2", port=wg_top.ports["port 2"])
    c.add_port(name="o3", port=wg_bottom.ports["port 2"])
    c.add_port(name="o4", port=wg_bottom.ports["port 1"])

    c.info["sim"] = "MODE"
    return c

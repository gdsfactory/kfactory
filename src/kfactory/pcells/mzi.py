from functools import partial
from typing import Any, Callable, Optional, Sequence, Tuple, Union

import kfactory as kf
from kfactory import autocell

### To do:
from kfactory.pcells.DCs import coupler
from kfactory.generic_tech import LayerEnum
from kfactory.pcells.dbu.waveguide import waveguide as waveguide_dbu
from kfactory.pcells.euler import bend_euler
from kfactory.pcells.taper import taper
from kfactory.pcells.waveguide import waveguide as straight_function
from kfactory.routing.optical import connect
from kfactory.typs import ComponentSpec
from kfactory.utils import Enclosure

# from kfactory.pcells.heater import wg_heater_connected
# from kfactory.tech.layers import LAYER (create some default layer for users)
# from kfactory.utils.enclosures import LAYER_ENC, WG_STANDARD
# from kfactory.utils.connection import connect_sequence


@autocell
def mzi(
    delta_length: float = 10.0,
    length_y: float = 2.0,
    length_x: Optional[float] = 0.1,
    bend: Callable[..., kf.KCell] = bend_euler,
    straight: ComponentSpec = straight_function,
    straight_y: Optional[ComponentSpec] = None,
    straight_x_top: Optional[ComponentSpec] = None,
    straight_x_bot: Optional[ComponentSpec] = None,
    splitter: ComponentSpec = coupler,
    combiner: Optional[ComponentSpec] = None,
    with_splitter: bool = True,
    port_e1_splitter: str = "o3",
    port_e0_splitter: str = "o4",
    port_e1_combiner: str = "o2",
    port_e0_combiner: str = "o1",
    nbends: int = 2,
    width: float = 1.0,
    layer: int | LayerEnum = 0,
    radius: float = 5.0,
    enclosure: Optional[Enclosure] = None,
    **kwargs: Any,
) -> kf.KCell:
    """Mzi.
    Args:
        delta_length: bottom arm vertical extra length.
        length_y: vertical length for both and top arms.
        length_x: horizontal length. None uses to the straight_x_bot/top defaults.
        bend: 90 degrees bend library.
        straight: straight function.
        straight_y: straight for length_y and delta_length.
        straight_x_top: top straight for length_x.
        straight_x_bot: bottom straight for length_x.
        splitter: splitter function.
        combiner: combiner function.
        with_splitter: if False removes splitter.
        port_e1_splitter: east top splitter port.
        port_e0_splitter: east bot splitter port.
        port_e1_combiner: east top combiner port.
        port_e0_combiner: east bot combiner port.
        nbends: from straight top/bot to combiner (at least 2).
        width: waveguide width.
        layer: waveguide layer.
        radius: bend radius.
        enclosure: waveguide enclosure.
        kwargs: combiner/splitter kwargs.
    .. code::
                       b2______b3
                      |  sxtop  |
              straight_y        |
                      |         |
                      b1        b4
            splitter==|         |==combiner
                      b5        b8
                      |         |
              straight_y        |
                      |         |
        delta_length/2          |
                      |         |
                     b6__sxbot__b7
                          Lx
    """
    combiner = combiner or splitter

    straight_x_top = (
        partial(straight_x_top, layer=layer)
        if straight_x_top and callable(straight_x_top)
        else None
    )
    straight_x_bot = (
        partial(straight_x_bot, layer=layer)
        if straight_x_bot and callable(straight_x_bot)
        else None
    )
    straight_x_top = straight_x_top or straight
    straight_x_bot = straight_x_bot or straight
    straight_y = straight_y or straight

    bend_settings = {
        "width": width,
        "layer": layer,
        "radius": radius,
        "enclosure": enclosure,
    }
    bend = kf.get_component(bend, **bend_settings)
    c = kf.KCell()
    straight_connect = partial(
        waveguide_dbu, layer=layer, width=width / c.klib.dbu, enclosure=enclosure
    )
    combiner_settings = {
        "width": width,
        "layer": layer,
        "enclosure": enclosure,
    }
    kwargs.pop("kwargs", "")
    kwargs |= combiner_settings
    cp1_ = kf.get_component(splitter, **kwargs)
    cp1_copy = cp1_
    cp2_ = kf.get_component(combiner, **kwargs) if combiner else cp1_

    if with_splitter:
        cp1 = c << cp1_

    cp2 = c << cp1_copy
    b5 = c << bend
    # b5.transform(kf.kdb.Trans.M90)
    b5.connect("W0", cp1.ports[port_e0_splitter], mirror=True)
    # b5.instance.transform(kf.kdb.Trans(1, False, 0, 0))
    # b5.transform(kf.kdb.Trans.M90.R180)

    syl = c << kf.get_component(
        straight_y,
        length=delta_length / 2 + length_y,
        width=width,
        layer=layer,
        enclosure=enclosure,
    )
    syl.connect("o1", b5.ports["N0"])
    b6 = c << bend
    b6.connect("W0", syl.ports["o2"], mirror=True)
    # b6.transform(kf.kdb.Trans.M90.R270)

    straight_x_bot = (
        kf.get_component(
            straight_x_bot,
            width=width,
            length=length_x,
            layer=layer,
            enclosure=enclosure,
        )
        if length_x
        else kf.get_component(
            straight_x_bot, length=10.0, width=width, layer=layer, enclosure=enclosure
        )
    )

    sxb = c << straight_x_bot
    sxb.connect("o1", b6.ports["N0"], mirror=True)

    b1 = c << bend
    b1.connect("W0", cp1.ports[port_e1_splitter], mirror=True)

    sytl = c << kf.get_component(
        straight_y, length=length_y, width=width, layer=layer, enclosure=enclosure
    )
    sytl.connect("o1", b1.ports["N0"])

    b2 = c << bend
    b2.connect("N0", sytl.ports["o2"])
    straight_x_top = (
        kf.get_component(
            straight_x_top,
            length=length_x,
            width=width,
            layer=layer,
            enclosure=enclosure,
        )
        if length_x
        else kf.get_component(
            straight_x_top, length=10.0, width=width, layer=layer, enclosure=enclosure
        )
    )
    sxt = c << straight_x_top
    sxt.connect("o1", b2.ports["W0"])

    # cp2.transform(kf.kdb.Trans.M90)
    cp2.transform(
        kf.kdb.Trans(
            2
            * (
                sxt.ports["o2"].x
                + radius * nbends
                + cp2.instance.dbbox().width()
                + cp2.ports["o2"].x
            ),
            0,
        )
    )

    connect(
        c,
        cp2.ports["o2"],
        sxt.ports["o2"],
        straight_connect,
        bend,
    )
    connect(
        c,
        cp2.ports["o1"],
        sxb.ports["o2"],
        straight_connect,
        bend,
    )

    if with_splitter:
        c.add_ports([port for port in cp1.ports if port.orientation == 180])
    else:
        c.add_port(name="o1", port=b1.ports["W0"])
        c.add_port(name="o2", port=b5.ports["W0"])
    c.add_ports([port for port in cp2.ports if port.orientation == 0])
    c.autorename_ports()

    c.info["components"] = {
        "straight1": {
            "component": straight,
            "params": {
                "width": width,
                "layer": layer,
                "enclosure": enclosure,
                "length": length_y,
            },
        },
        "straight2": {
            "component": straight,
            "params": {
                "width": width,
                "layer": layer,
                "enclosure": enclosure,
                "length": length_x,
            },
        },
        "straight3": {
            "component": straight,
            "params": {
                "width": width,
                "layer": layer,
                "enclosure": enclosure,
                "length": delta_length / 2 + length_y,
            },
        },
        "bend": {
            "component": bend,
            "params": bend_settings,
            "sim": "FDTD",
        },
        "splitter": {
            "component": splitter,
            "params": kwargs,
            **cp1_copy.info["components"],
        },
    }
    return c

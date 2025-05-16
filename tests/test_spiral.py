import warnings

import numpy as np

import kfactory as kf
from tests.conftest import Layers


def bend_circular(
    width: int,
    radius: int,
    layer: kf.kdb.LayerInfo,
    enclosure: kf.enclosure.LayerEnclosure | None = None,
    angle: int = 90,
    angle_step: float = 1,
) -> kf.KCell:
    """Circular radius bend.

    Args:
        width: Width in database units
        radius: Radius in database units
        layer: Layer index of the target layer
        enclosure: :py:class:`kfactory.Enclosure` object to describe the claddings
    Returns:
        cell (KCell): Circular Bend KCell
    """
    c = kf.KCell()
    r = radius * c.kcl.dbu
    backbone = [
        kf.kdb.DPoint(x, y)
        for x, y in [
            [np.sin(_angle / 180 * np.pi) * r, (-np.cos(_angle / 180 * np.pi) + 1) * r]
            for _angle in np.linspace(
                0, angle, int(angle // angle_step + 0.5), endpoint=True
            )
        ]
    ]

    kf.enclosure.extrude_path(c, layer, backbone, width, enclosure, 0, angle)

    c.create_port(
        name="W0",
        trans=kf.kdb.Trans(2, False, 0, 0),
        width=width,
        layer=c.kcl.find_layer(layer),
    )

    match angle:
        case 90:
            c.create_port(
                name="N0",
                trans=kf.kdb.Trans(1, False, radius, radius),
                width=width,
                layer=c.kcl.find_layer(layer),
            )
        case 180:
            c.create_port(
                name="W1",
                trans=kf.kdb.Trans(0, False, 0, 2 * radius),
                width=width,
                layer=c.kcl.find_layer(layer),
            )

    return c


def dbend_circular(
    width: float,
    radius: float,
    layer: kf.kdb.LayerInfo,
    enclosure: kf.LayerEnclosure | None = None,
    angle: float = 90,
    angle_step: float = 1,
) -> kf.KCell:
    """Circular radius bend.

    Args:
        width: Width in database units
        radius: Radius in database units
        layer: Layer index of the target layer
        enclosure: :py:class:`kfactory.Enclosure` object to describe the claddings
    Returns:
        cell (KCell): Circular Bend KCell
    """
    c = kf.KCell()
    r = radius
    backbone = [
        kf.kdb.DPoint(x, y)
        for x, y in [
            [np.sin(_angle / 180 * np.pi) * r, (-np.cos(_angle / 180 * np.pi) + 1) * r]
            for _angle in np.linspace(
                0, angle, int(angle // angle_step + 0.5), endpoint=True
            )
        ]
    ]
    kf.enclosure.extrude_path(c, layer, backbone, width, enclosure, 0, angle)
    dp1 = kf.port.Port(
        width=c.kcl.to_dbu(width),
        layer=c.kcl.find_layer(layer),
        name="W0",
        dcplx_trans=kf.kdb.DCplxTrans.R180,
    )
    warnings.filterwarnings("ignore")
    c.add_port(port=dp1)

    match angle:
        case 90:
            dp2 = kf.Port(
                name="N0",
                layer=c.kcl.find_layer(layer),
                width=c.kcl.to_dbu(width),
                dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, radius, radius),
            )
        case 180:
            dp2 = kf.Port(
                name="N0",
                layer=c.kcl.find_layer(layer),
                width=c.kcl.to_dbu(width),
                dcplx_trans=kf.kdb.DCplxTrans(1, 0, False, 0, 2 * radius),
            )
        case _:
            raise ValueError("only support 90/180° bends")
    c.add_port(port=dp2)
    warnings.filterwarnings("default")
    return c


def test_spiral(layers: Layers) -> None:
    c = kf.KCell()

    r1 = 1000
    r2 = 0

    p: kf.port.ProtoPort[int] = kf.Port(
        name="start",
        trans=kf.kdb.Trans.R0,
        width=1000,
        layer=c.kcl.find_layer(layers.WG),
    )

    for _ in range(10):
        r = r1 + r2
        r2 = r1
        r1 = r
        b = c << bend_circular(width=1000, radius=r2, layer=layers.WG)
        b.connect("W0", p)
        p = b.ports["N0"]


def test_dspiral(layers: Layers) -> None:
    c = kf.KCell()

    r1 = 1
    r2 = 0

    p: kf.port.ProtoPort[int] = kf.Port(
        name="start",
        dcplx_trans=kf.kdb.DCplxTrans.R0,
        width=c.kcl.to_dbu(1),
        layer=c.kcl.find_layer(layers.WG),
    )

    kf.config.logfilter.level = kf.conf.LogLevel.ERROR

    for _ in range(10):
        r = r1 + r2
        r2 = r1
        r1 = r
        b = c << dbend_circular(width=1, radius=r2, layer=layers.WG)
        b.connect("W0", p)
        p = b.ports["N0"]

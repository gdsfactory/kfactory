import kfactory as kf
import numpy as np
import warnings


def bend_circular(
    width: int,
    radius: int,
    layer: int,
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
        name="W0", trans=kf.kdb.Trans(2, False, 0, 0), width=width, layer=layer
    )

    match angle:
        case 90:
            c.create_port(
                name="N0",
                trans=kf.kdb.Trans(1, False, radius, radius),
                width=width,
                layer=layer,
            )
        case 180:
            c.create_port(
                name="W1",
                trans=kf.kdb.Trans(0, False, 0, 2 * radius),
                width=width,
                layer=layer,
            )

    return c


def dbend_circular(
    width: float,
    radius: float,
    layer: kf.kcell.LayerEnum,
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
    dp1 = kf.kcell.Port(
        dwidth=width, layer=layer, name="W0", dcplx_trans=kf.kdb.DCplxTrans.R180
    )
    warnings.filterwarnings("ignore")
    c.add_port(dp1)

    match angle:
        case 90:
            dp2 = kf.Port(
                name="N0",
                layer=layer,
                dwidth=width,
                dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, radius, radius),
            )
        case 180:
            dp2 = kf.Port(
                name="N0",
                layer=layer,
                dwidth=width,
                dcplx_trans=kf.kdb.DTrans(1, 0, False, 0, 2 * radius),
            )
        case _:
            raise ValueError("only support 90/180° bends")
    c.add_port(dp2)
    warnings.filterwarnings("default")
    return c


def test_spiral(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()

    r1 = 1000
    r2 = 0

    p = kf.Port(name="start", trans=kf.kdb.Trans.R0, width=1000, layer=LAYER.WG)

    for _ in range(10):
        r = r1 + r2
        r2 = r1
        r1 = r
        b = c << bend_circular(width=1000, radius=r2, layer=LAYER.WG)
        b.connect("W0", p)
        p = b.ports["N0"]


def test_dspiral(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()

    r1 = 1
    r2 = 0

    p = kf.Port(
        name="start", dcplx_trans=kf.kdb.DCplxTrans.R0, dwidth=1, layer=LAYER.WG
    )

    kf.config.logfilter.level = kf.conf.LogLevel.ERROR

    for _ in range(10):
        r = r1 + r2
        r2 = r1
        r1 = r
        b = c << dbend_circular(width=1, radius=r2, layer=LAYER.WG)
        b.connect("W0", p)
        p = b.ports["N0"]

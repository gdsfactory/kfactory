import kfactory as kf
import pytest
import numpy as np
from typing import Optional


def bend_circular(
    width: int,
    radius: int,
    layer: int,
    enclosure: Optional[kf.utils.Enclosure] = None,
    theta: int = 90,
    theta_step: float = 1,
) -> kf.KCell:
    """Circular radius bend

    Args:
        width: Width in database units
        radius: Radius in database units
        layer: Layer index of the target layer
        enclosure: :py:class:`kfactory.utils.Enclosure` object to describe the claddings
    Returns:
        cell (KCell): Circular Bend KCell
    """

    c = kf.KCell()
    r = radius * c.library.dbu
    backbone = [
        kf.kdb.DPoint(x, y)
        for x, y in [
            [np.sin(_theta / 180 * np.pi) * r, (-np.cos(_theta / 180 * np.pi) + 1) * r]
            for _theta in np.linspace(
                0, theta, int(theta // theta_step + 0.5), endpoint=True
            )
        ]
    ]
    pts = kf.utils.geo.extrude_path(backbone, width * c.library.dbu, snap_to_90=True)

    c.shapes(layer).insert(kf.kdb.DPolygon(pts))

    for p1, p2 in zip(pts[:-1], pts[1:]):
        e = kf.kdb.DEdge(p1, p2)
        c.shapes(layer).insert(e)

    if enclosure is not None:
        enclosure.apply_custom(
            c,
            lambda d: kf.kdb.Polygon(
                [
                    p.to_itype(c.library.dbu)
                    for p in kf.utils.geo.extrude_path(
                        backbone, (d * 2 + width) * c.library.dbu
                    )
                ]
            ),
        )

    c.create_port(
        name="W0", trans=kf.kdb.Trans(2, False, 0, 0), width=width, layer=layer
    )

    match theta:
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
    layer: kf.tech.LayerEnum,
    enclosure: Optional[kf.utils.Enclosure] = None,
    theta: float = 90,
    theta_step: float = 1,
) -> kf.KCell:
    """Circular radius bend

    Args:
        width: Width in database units
        radius: Radius in database units
        layer: Layer index of the target layer
        enclosure: :py:class:`kfactory.utils.Enclosure` object to describe the claddings
    Returns:
        cell (KCell): Circular Bend KCell
    """

    c = kf.KCell()
    # r = radius * c.library.dbu
    r = radius
    backbone = [
        kf.kdb.DPoint(x, y)
        for x, y in [
            [np.sin(_theta / 180 * np.pi) * r, (-np.cos(_theta / 180 * np.pi) + 1) * r]
            for _theta in np.linspace(
                0, theta, int(theta // theta_step + 0.5), endpoint=True
            )
        ]
    ]
    pts = kf.utils.geo.extrude_path(backbone, width, snap_to_90=True)

    c.shapes(layer).insert(kf.kdb.DPolygon(pts))

    for p1, p2 in zip(pts[:-1], pts[1:]):
        e = kf.kdb.DEdge(p1, p2)
        c.shapes(layer).insert(e)

    if enclosure is not None:
        enclosure.apply_custom(
            c,
            lambda d: kf.kdb.Polygon(
                [
                    p.to_itype(c.library.dbu)
                    for p in kf.utils.geo.extrude_path(backbone, (d * 2 + width))
                ]
            ),
        )

    dp1 = kf.kcell.DPort(width=width, layer=layer, name="W0", trans=kf.kdb.DTrans.R180)

    c.add_port(dp1)

    # c.create_port(
    #     name="W0", trans=kf.kdb.Trans(2, False, 0, 0), width=width, layer=int(layer)
    # )

    match theta:
        case 90:

            dp2 = kf.DPort(
                name="N0",
                layer=layer,
                width=width,
                trans=kf.kdb.DTrans(1, False, radius, radius),
            )
        case 180:
            dp2 = kf.DPort(
                name="N0",
                layer=layer,
                width=width,
                trans=kf.kdb.DTrans(0, False, 0, 2 * radius),
            )
        case _:
            raise ValueError("only support 90/180° bends")
    c.add_port(dp2)
    return c


def test_spiral(LAYER):
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

    # kf.show(c)


def test_dspiral(LAYER):
    c = kf.KCell()

    r1 = 1
    r2 = 0

    p = kf.DPort(name="start", trans=kf.kdb.DTrans.R0, width=1, layer=LAYER.WG)

    for _ in range(10):
        r = r1 + r2
        r2 = r1
        r1 = r
        b = c << dbend_circular(width=1, radius=r2, layer=LAYER.WG)
        b.connect_cplx("W0", p)
        p = b.ports["N0"]


# if __name__ == "__main__":
#     test_waveguide()

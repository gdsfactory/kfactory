"""Circular bends.

A circular bend has a constant radius.
"""

import numpy as np

from kfactory import kdb
from kfactory.kcell import Cell, LayerEnum, cell
from kfactory.utils import Enclosure, extrude_path

__all__ = ["bend_circular"]


@cell
def bend_circular(
    width: float,
    radius: float,
    layer: int | LayerEnum,
    enclosure: Enclosure | None = None,
    theta: float = 90,
    theta_step: float = 1,
) -> Cell:
    """Circular radius bend [um].

    Args:
        width: Width of the core. [um]
        radius: Radius of the backbone. [um]
        layer: Layer index of the target layer.
        enclosure: :py:class:`kfactory.utils.Enclosure` object to describe the
            claddings.
        theta: Angle amount of the bend.
        theta_step: Angle amount per backbone point of the bend.
    """
    c = Cell()
    r = radius
    backbone = [
        kdb.DPoint(x, y)
        for x, y in [
            [np.sin(_theta / 180 * np.pi) * r, (-np.cos(_theta / 180 * np.pi) + 1) * r]
            for _theta in np.linspace(
                0, theta, int(theta // theta_step + 0.5), endpoint=True
            )
        ]
    ]

    extrude_path(
        target=c,
        layer=layer,
        path=backbone,
        width=width,
        enclosure=enclosure,
        start_angle=0,
        end_angle=theta,
    )

    c.create_port(
        name="o1",
        trans=kdb.Trans(2, False, 0, 0),
        width=int(width / c.klib.dbu),
        layer=layer,
    )

    match theta:
        case 90:
            c.create_port(
                name="o2",
                trans=kdb.DTrans(1, False, radius, radius).to_itype(c.klib.dbu),
                width=int(width / c.klib.dbu),
                layer=layer,
            )
        case 180:
            c.create_port(
                name="o2",
                trans=kdb.DTrans(0, False, 0, 2 * radius).to_itype(c.klib.dbu),
                width=int(width / c.klib.dbu),
                layer=layer,
            )

    return c

if __name__ == "__main__": 
    from kfactory.generic_tech import LAYER
    import kfactory as kf
    um=1e3

    enc = kf.utils.Enclosure(
    [
        (LAYER.DEEPTRENCH, 2*um, 3*um),
        (LAYER.SLAB90, 2*um),
    ],
    name="WGSLAB",
    main_layer=LAYER.WG,
)

    c = bend_circular(width=0.5, layer=LAYER.WG, radius=10, enclosure=enc)
    c.draw_ports()
    c.show()

"""Circular bends.

A circular bend has a constant radius.
"""

import numpy as np

from .. import kdb
from ..kcell import KCell, LayerEnum, cell
from ..utils import LayerEnclosure, extrude_path

__all__ = ["bend_circular"]


@cell
def bend_circular(
    width: float,
    radius: float,
    layer: int | LayerEnum,
    enclosure: LayerEnclosure | None = None,
    angle: float = 90,
    angle_step: float = 1,
    snap_ports: bool = True,
) -> KCell:
    """Circular radius bend [um].

    If the ports are not snapped to the grid in the 90° case, it can lead to poor
    performance and snapping issues.

    Args:
        width: Width of the core. [um]
        radius: Radius of the backbone. [um]
        layer: Layer index of the target layer.
        enclosure: Optional enclosure.
        angle: Angle amount of the bend.
        angle_step: Angle amount per backbone point of the bend.
        snap_ports: Useful if the resulting center of the port should be on-grid.
    """
    c = KCell()
    dbu = c.kcl.dbu
    r = radius
    backbone = [
        kdb.DPoint(x, y)
        for x, y in [
            [np.sin(_angle / 180 * np.pi) * r, (-np.cos(_angle / 180 * np.pi) + 1) * r]
            for _angle in np.linspace(
                0, angle, int(angle // angle_step + 0.5), endpoint=True
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
        end_angle=angle,
    )

    c.create_port(
        trans=kdb.Trans(2, False, 0, 0),
        width=int(width / dbu),
        layer=layer,
    )

    if snap_ports:
        dcplxtrans = kdb.DCplxTrans(
            1, angle, False, backbone[-1].to_itype(dbu).to_dtype(dbu).to_v()
        )
    else:
        dcplxtrans = kdb.DCplxTrans(1, angle, False, backbone[-1].to_v())

    c.create_port(
        dcplx_trans=dcplxtrans,
        dwidth=width,
        layer=layer,
    )
    c.autorename_ports()
    return c

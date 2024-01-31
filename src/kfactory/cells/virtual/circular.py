"""Virtual circular cells."""
import numpy as np

from ... import kdb
from ...conf import config
from ...enclosure import LayerEnclosure
from ...kcell import KCLayout, VKCell, kcl, vcell
from .utils import extrude_backbone


class VirtualBendCircular:
    """Virtual circular bend."""

    kcl: KCLayout

    def __init__(self, kcl: KCLayout) -> None:
        """Create a virtual circular bend function on a custom KCLayout."""
        self.kcl = kcl

    @vcell
    def __call__(
        self,
        width: float,
        radius: float,
        layer: int,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        angle_step: float = 1,
    ) -> VKCell:
        """Create a virtual circular bend.

        Args:
            width: Width of the core. [um]
            radius: Radius of the backbone. [um]
            layer: Layer index of the target layer.
            enclosure: Optional enclosure.
            angle: Angle amount of the bend.
            angle_step: Angle amount per backbone point of the bend.
        """
        c = VKCell()
        if angle < 0:
            config.logger.critical(
                f"Negative lengths are not allowed {angle} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            angle = -angle
        if width < 0:
            config.logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width
        dbu = c.kcl.dbu
        backbone = [
            kdb.DPoint(x, y)
            for x, y in [
                [
                    np.sin(_angle / 180 * np.pi) * radius,
                    (-np.cos(_angle / 180 * np.pi) + 1) * radius,
                ]
                for _angle in np.linspace(
                    0, angle, int(angle // angle_step + 0.5), endpoint=True
                )
            ]
        ]

        extrude_backbone(
            c=c,
            backbone=backbone,
            width=width,
            layer=layer,
            enclosure=enclosure,
            start_angle=0,
            end_angle=angle,
            dbu=dbu,
        )

        c.create_port(
            name="o1",
            layer=layer,
            dwidth=round(width / c.kcl.dbu),
            dcplx_trans=kdb.DCplxTrans(1, 180, False, backbone[0].to_v()),
        )
        c.create_port(
            name="o2",
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            dwidth=width,
            layer=layer,
        )
        return c


virtual_bend_circular = VirtualBendCircular(kcl)

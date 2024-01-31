"""Virtual euler cells."""
from ... import kdb
from ...conf import config
from ...enclosure import LayerEnclosure
from ...kcell import KCLayout, VKCell, kcl, vcell
from ..euler import euler_bend_points
from .utils import extrude_backbone


class VirtualBendEuler:
    """Virtual euler bend on a custom KCLayout."""

    kcl: KCLayout

    def __init__(self, kcl: KCLayout) -> None:
        """Create a euler_bend function on a custom KCLayout."""
        self.kcl = kcl

    @vcell
    def __call__(
        self,
        width: float,
        radius: float,
        layer: int,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        resolution: float = 150,
    ) -> VKCell:
        """Create a virtual euler bend.

        Args:
            width: Width of the core. [um]
            radius: Radius off the backbone. [um]
            layer: Layer index / LayerEnum of the core.
            enclosure: Slab/exclude definition. [dbu]
            angle: Angle of the bend.
            resolution: Angle resolution for the backbone.
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
        backbone = euler_bend_points(angle, radius=radius, resolution=resolution)

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
            dwidth=width,
            dcplx_trans=kdb.DCplxTrans(1, 180, False, backbone[0].to_v()),
        )
        c.create_port(
            name="o2",
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            dwidth=width,
            layer=layer,
        )
        return c


virtual_bend_euler = VirtualBendEuler(kcl)

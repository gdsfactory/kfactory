"""Euler bends.

Euler bends are bends with a constantly changing radius
from zero to a maximum radius and back to 0 at the other
end.
"""


from collections.abc import Callable

from .. import kdb
from ..cells.euler import euler_bend_points, euler_sbend_points
from ..enclosure import LayerEnclosure, extrude_path
from ..kcell import KCell, KCLayout, LayerEnum, cell

__all__ = [
    "euler_bend_points",
    "euler_sbend_points",
    "custom_bend_euler",
    "custom_bend_s_euler",
]


def custom_bend_euler(
    kcl: KCLayout,
) -> Callable[
    [float, float, int | LayerEnum, LayerEnclosure | None, float, float], KCell
]:
    """Euler bend with a custom KCLayout."""

    @cell
    def bend_euler(
        width: float,
        radius: float,
        layer: int | LayerEnum,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        resolution: float = 150,
    ) -> KCell:
        """Create a euler bend.

        Args:
            width: Width of the core. [um]
            radius: Radius off the backbone. [um]
            layer: Layer index / LayerEnum of the core.
            enclosure: Slab/exclude definition. [dbu]
            angle: Angle of the bend.
            resolution: Angle resolution for the backbone.
        """
        c = kcl.kcell()
        dbu = c.kcl.dbu
        backbone = euler_bend_points(angle, radius=radius, resolution=resolution)

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
            layer=layer,
            width=int(width / c.kcl.dbu),
            trans=kdb.Trans(2, False, backbone[0].to_itype(dbu).to_v()),
        )

        c.create_port(
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            dwidth=width,
            layer=layer,
        )

        c.autorename_ports()
        return c

    return bend_euler


def custom_bend_s_euler(kcl: KCLayout) -> Callable[..., KCell]:
    """Euler s-bend with a custom KCLayout."""

    @cell
    def bend_s_euler(
        offset: float,
        width: float,
        radius: float,
        layer: LayerEnum | int,
        enclosure: LayerEnclosure | None = None,
        resolution: float = 150,
    ) -> KCell:
        """Create a euler s-bend.

        Args:
            offset: Offset between left/right. [um]
            width: Width of the core. [um]
            radius: Radius off the backbone. [um]
            layer: Layer index / LayerEnum of the core.
            enclosure: Slab/exclude definition. [dbu]
            resolution: Angle resolution for the backbone.
        """
        c = kcl.kcell()
        dbu = c.kcl.dbu
        backbone = euler_sbend_points(
            offset=offset,
            radius=radius,
            resolution=resolution,
        )
        extrude_path(
            target=c,
            layer=layer,
            path=backbone,
            width=width,
            enclosure=enclosure,
            start_angle=0,
            end_angle=0,
        )

        v = backbone[-1] - backbone[0]
        if v.x < 0:
            p1 = backbone[-1].to_itype(dbu)
            p2 = backbone[0].to_itype(dbu)
        else:
            p1 = backbone[0].to_itype(dbu)
            p2 = backbone[-1].to_itype(dbu)
        c.create_port(
            trans=kdb.Trans(2, False, p1.to_v()),
            width=int(width / c.kcl.dbu),
            port_type="optical",
            layer=layer,
        )
        c.create_port(
            trans=kdb.Trans(0, False, p2.to_v()),
            width=int(width / c.kcl.dbu),
            port_type="optical",
            layer=layer,
        )

        c.autorename_ports()
        return c

    return bend_s_euler

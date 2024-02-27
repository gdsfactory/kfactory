"""Circular bends.

A circular bend has a constant radius.
"""
from typing import Any

import numpy as np

from .. import kdb
from ..conf import config
from ..enclosure import LayerEnclosure, extrude_path
from ..kcell import KCell, KCLayout, LayerEnum, kcl

__all__ = ["bend_circular", "BendCircular"]


class BendCircular:
    """Circular radius bend [um].

    Args:
        width: Width of the core. [um]
        radius: Radius of the backbone. [um]
        layer: Layer index of the target layer.
        enclosure: Optional enclosure.
        angle: Angle amount of the bend.
        angle_step: Angle amount per backbone point of the bend.
    """

    def __init__(
        self,
        kcl: KCLayout,
        basename: str | None = None,
        snap_ports: bool = False,
        **cell_kwargs: Any,
    ):
        """Set kcl."""
        self.kcl = kcl
        self._cell = self.kcl.cell(
            basename=basename or self.__class__.__name__,
            snap_ports=snap_ports,
            **cell_kwargs,
        )(self._kcell)

    def __call__(
        self,
        width: float,
        radius: float,
        layer: int | LayerEnum,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        angle_step: float = 1,
    ) -> KCell:
        """Circular radius bend [um].

        Args:
            width: Width of the core. [um]
            radius: Radius of the backbone. [um]
            layer: Layer index of the target layer.
            enclosure: Optional enclosure.
            angle: Angle amount of the bend.
            angle_step: Angle amount per backbone point of the bend.
        """
        return self._cell(
            width=width,
            radius=radius,
            layer=layer,
            enclosure=enclosure,
            angle=angle,
            angle_step=angle_step,
        )

    def _kcell(
        self,
        width: float,
        radius: float,
        layer: int | LayerEnum,
        enclosure: LayerEnclosure | None = None,
        angle: float = 90,
        angle_step: float = 1,
    ) -> KCell:
        """Circular radius bend [um].

        Args:
            width: Width of the core. [um]
            radius: Radius of the backbone. [um]
            layer: Layer index of the target layer.
            enclosure: Optional enclosure.
            angle: Angle amount of the bend.
            angle_step: Angle amount per backbone point of the bend.
        """
        c = self.kcl.kcell()
        r = radius

        if angle < 0:
            config.logger.critical(
                f"Negative angles are not allowed {angle} as ports"
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

        backbone = [
            kdb.DPoint(x, y)
            for x, y in [
                [
                    np.sin(_angle / 180 * np.pi) * r,
                    (-np.cos(_angle / 180 * np.pi) + 1) * r,
                ]
                for _angle in np.linspace(
                    0, angle, int(angle // angle_step + 0.5), endpoint=True
                )
            ]
        ]

        center_path = extrude_path(
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
            width=int(width / c.kcl.dbu),
            layer=layer,
        )
        c.create_port(
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            dwidth=width,
            layer=layer,
        )
        c.auto_rename_ports()
        c.boundary = center_path
        return c


bend_circular = BendCircular(kcl)
"""Circular bend on the default KCLayout."""

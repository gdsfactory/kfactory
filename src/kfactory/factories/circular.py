"""Circular bends.

A circular bend has a constant radius.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, Unpack, cast, overload

import numpy as np

from .. import kdb
from ..conf import logger
from ..enclosure import LayerEnclosure, extrude_path
from ..kcell import KCell
from ..layout import CellKWargs, KCLayout
from ..settings import Info
from ..typings import KC, KC_co, MetaData, deg, um

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..enclosure import LayerEnclosure
    from ..kcell import KCell

__all__ = ["bend_circular_factory"]


class BendCircularFactory(Protocol[KC_co]):
    def __call__(
        self,
        width: um,
        radius: um,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
        angle: deg = 90,
        angle_step: deg = 1,
    ) -> KC_co:
        """Circular radius bend [um].

        Args:
            width: Width of the core. [um]
            radius: Radius of the backbone. [um]
            layer: Layer index of the target layer.
            enclosure: Optional enclosure.
            angle: Angle amount of the bend.
            angle_step: Angle amount per backbone point of the bend.
        """
        ...


@overload
def bend_circular_factory(
    kcl: KCLayout,
    *,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BendCircularFactory[KCell]: ...
@overload
def bend_circular_factory(
    kcl: KCLayout,
    *,
    output_type: type[KC],
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BendCircularFactory[KC]: ...


def bend_circular_factory(
    kcl: KCLayout,
    *,
    output_type: type[KC] | None = None,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> BendCircularFactory[KC]:
    """Returns a function generating circular bends.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.settings.Info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting KCell's name. By default
            the KCell will be named 'straight_dbu[...]'.
        snap_ports: Whether to snap ports to grid.
        cell_kwargs: Additional arguments passed as `@kcl.cell(**cell_kwargs)`.
    """
    if callable(additional_info):
        _additional_info_func: Callable[
            ...,
            dict[str, MetaData],
        ] = additional_info
        _additional_info: dict[str, MetaData] = {}
    else:

        def additional_info_func(
            **kwargs: Any,
        ) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}

    if cell_kwargs.get("snap_ports") is None:
        cell_kwargs["snap_ports"] = False

    if output_type is not None:
        cell = kcl.cell(output_type=output_type, **cell_kwargs)
    else:
        cell = kcl.cell(output_type=cast("type[KC]", KCell), **cell_kwargs)

    @cell
    def bend_circular(
        width: um,
        radius: um,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
        angle: deg = 90,
        angle_step: deg = 1,
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
        c = kcl.kcell()
        r = radius

        if angle < 0:
            logger.critical(
                f"Negative angles are not allowed {angle} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            angle = -angle
        if width < 0:
            logger.critical(
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
            layer=c.kcl.layer(layer),
            port_type=port_type,
        )
        c.create_port(
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            width=c.kcl.to_dbu(width),
            layer=c.kcl.layer(layer),
            port_type=port_type,
        )
        c.auto_rename_ports()
        c.boundary = center_path
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                width=width,
                radius=radius,
                layer=layer,
                enclosure=enclosure,
                angle=angle,
                angle_step=angle_step,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)
        return c

    return bend_circular

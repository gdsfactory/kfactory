"""Virtual euler cell factories."""

from collections.abc import Callable
from typing import Any, Protocol

from ... import kdb
from ...conf import logger
from ...enclosure import LayerEnclosure
from ...factories.euler import euler_bend_points
from ...kcell import VKCell
from ...layout import KCLayout
from ...settings import Info
from ...typings import MetaData
from .utils import extrude_backbone


class BendEulerVKCell(Protocol):
    """Factory for virtual euler bends."""

    def __call__(
        self,
        width: float,
        radius: float,
        layer: kdb.LayerInfo,
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
        ...


def virtual_bend_euler_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    basename: str | None = None,
    **cell_kwargs: Any,
) -> BendEulerVKCell:
    """Returns a function generating virtual euler bends.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`VKCell.info`][kfactory.kcell.VKCell.info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting VKCell's name. By default
            the VKCell will be named 'virtual_bend_euler[...]'.
        cell_kwargs: Additional arguments passed as `@kcl.vcell(**cell_kwargs)`.
    """
    if callable(additional_info) and additional_info is not None:
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

    @kcl.vcell(
        basename=basename,
        output_type=VKCell,
        **cell_kwargs,
    )
    def bend_euler(
        width: float,
        radius: float,
        layer: kdb.LayerInfo,
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
            logger.critical(
                f"Negative lengths are not allowed {angle} as ports"
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
        _info: dict[str, MetaData] = {}
        _info.update(
            _additional_info_func(
                width=width,
                radius=radius,
                layer=layer,
                enclosure=enclosure,
                angle=angle,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)

        c.create_port(
            name="o1",
            layer=c.kcl.layer(layer),
            width=width,
            dcplx_trans=kdb.DCplxTrans(1, 180, False, backbone[0].to_v()),
        )
        c.create_port(
            name="o2",
            dcplx_trans=kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
            width=width,
            layer=c.kcl.layer(layer),
        )
        return c

    return bend_euler

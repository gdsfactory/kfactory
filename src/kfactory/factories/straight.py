"""Straight waveguide in dbu.

A waveguide is a rectangle of material with excludes and/or slab around it::

    ┌──────────────────────────────┐
    │         Slab/Exclude         │
    ├──────────────────────────────┤
    │                              │
    │             Core             │
    │                              │
    ├──────────────────────────────┤
    │         Slab/Exclude         │
    └──────────────────────────────┘

The slabs and excludes can be given in the form of an
[Enclosure][kfactory.enclosure.LayerEnclosure].
"""

from collections.abc import Callable
from typing import Any, Protocol

from .. import kdb
from ..conf import logger
from ..decorators import PortsDefinition
from ..enclosure import LayerEnclosure
from ..kcell import KCell
from ..layout import KCLayout
from ..settings import Info
from ..typings import MetaData, dbu

__all__ = ["straight_dbu_factory"]


class StraightKCellFactory(Protocol):
    __name__: str

    def __call__(
        self,
        width: dbu,
        length: dbu,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
    ) -> KCell:
        """Waveguide defined in dbu.

            ┌──────────────────────────────┐
            │         Slab/Exclude         │
            ├──────────────────────────────┤
            │                              │
            │             Core             │
            │                              │
            ├──────────────────────────────┤
            │         Slab/Exclude         │
            └──────────────────────────────┘
        Args:
            width: Waveguide width. [dbu]
            length: Waveguide length. [dbu]
            layer: Main layer of the waveguide.
            enclosure: Definition of slab/excludes. [dbu]
        """
        ...


_straight_default_ports = PortsDefinition(left=["o1"], right=["o2"])


def straight_dbu_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    basename: str | None = None,
    ports: PortsDefinition = _straight_default_ports,
    **cell_kwargs: Any,
) -> StraightKCellFactory:
    """Returns a function generating straights [dbu].

        ┌──────────────────────────────┐
        │         Slab/Exclude         │
        ├──────────────────────────────┤
        │                              │
        │             Core             │
        │                              │
        ├──────────────────────────────┤
        │         Slab/Exclude         │
        └──────────────────────────────┘
    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.kcell.KCell.info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
        basename: Overwrite the prefix of the resulting KCell's name. By default
            the KCell will be named 'straight_dbu[...]'.
        cell_kwargs: Additional arguments passed as `@kcl.cell(**cell_kwargs)`.
    """
    if callable(additional_info):
        _additional_info_func: Callable[..., dict[str, MetaData]] = additional_info
        _additional_info: dict[str, MetaData] = {}
    else:

        def additional_info_func(**kwargs: Any) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}

    @kcl.cell(
        basename=basename,
        output_type=KCell,
        ports=ports,
        **cell_kwargs,
    )
    def straight(
        width: dbu,
        length: dbu,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
    ) -> KCell:
        """Waveguide defined in dbu.

            ┌──────────────────────────────┐
            │         Slab/Exclude         │
            ├──────────────────────────────┤
            │                              │
            │             Core             │
            │                              │
            ├──────────────────────────────┤
            │         Slab/Exclude         │
            └──────────────────────────────┘
        Args:
            width: Waveguide width. [dbu]
            length: Waveguide length. [dbu]
            layer: Main layer of the waveguide.
            enclosure: Definition of slab/excludes. [dbu]
        """
        c = kcl.kcell()

        if length < 0:
            logger.critical(
                f"Negative lengths are not allowed {length} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length = -length
        if width < 0:
            logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width

        if width // 2 * 2 != width:
            raise ValueError("The width (w) must be a multiple of 2 database units")

        li = c.kcl.layer(layer)
        c.shapes(li).insert(kdb.Box(0, -width // 2, length, width // 2))
        c.create_port(trans=kdb.Trans(2, False, 0, 0), layer=li, width=width)
        c.create_port(trans=kdb.Trans(0, False, length, 0), layer=li, width=width)

        if enclosure is not None:
            enclosure.apply_minkowski_y(c, layer)
        _info: dict[str, MetaData] = {
            "width_um": width * c.kcl.dbu,
            "length_um": length * c.kcl.dbu,
            "width_dbu": width,
            "length_dbu": length,
        }
        _info.update(
            _additional_info_func(
                width=width, length=length, layer=layer, enclosure=enclosure
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)

        c.boundary = c.dbbox()  # type: ignore[assignment]
        c.auto_rename_ports()
        return c

    return straight

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

from .. import kdb, kf_types
from ..conf import config
from ..enclosure import LayerEnclosure
from ..kcell import Info, KCell, KCLayout, MetaData

__all__ = ["straight_dbu_factory"]


class StraightKCellFactory(Protocol):
    def __call__(
        self,
        width: kf_types.dbu,
        length: kf_types.dbu,
        layer: kf_types.dbu,
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


def straight_dbu_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    basename: str | None = None,
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

    @kcl.cell(basename=basename, **cell_kwargs)
    def straight(
        width: kf_types.dbu,
        length: kf_types.dbu,
        layer: kf_types.layer,
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
            config.logger.critical(
                f"Negative lengths are not allowed {length} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length = -length
        if width < 0:
            config.logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width

        if width // 2 * 2 != width:
            raise ValueError("The width (w) must be a multiple of 2 database units")

        c.shapes(layer).insert(kdb.Box(0, -width // 2, length, width // 2))
        c.create_port(trans=kdb.Trans(2, False, 0, 0), layer=layer, width=width)
        c.create_port(trans=kdb.Trans(0, False, length, 0), layer=layer, width=width)

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

        c.boundary = c.dbbox()
        c.auto_rename_ports()
        return c

    return straight

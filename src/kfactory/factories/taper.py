"""Taper definitions [dbu].

TODO: Non-linear tapers
"""

from collections.abc import Callable
from typing import Any, Protocol

from .. import kdb
from ..conf import logger
from ..enclosure import LayerEnclosure
from ..kcell import KCell
from ..layout import KCLayout, kcl
from ..settings import Info
from ..typings import MetaData, dbu

__all__ = ["taper"]


class TaperFactory(Protocol):
    def __call__(
        self,
        width1: dbu,
        width2: dbu,
        length: dbu,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
    ) -> KCell:
        r"""Linear Taper [dbu].

                   __
                 _/  │ Slab/Exclude
               _/  __│
             _/  _/  │
            │  _/    │
            │_/      │
            │_       │ Core
            │ \_     │
            │_  \_   │
              \_  \__│
                \_   │
                  \__│ Slab/Exclude

        Args:
            width1: Width of the core on the left side. [dbu]
            width2: Width of the core on the right side. [dbu]
            length: Length of the taper. [dbu]
            layer: Main layer of the taper.
            enclosure: Definition of the slab/exclude.
        """
        ...


def taper_factory(
    kcl: KCLayout,
    basename: str | None = None,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    **cell_kwargs: Any,
) -> TaperFactory:
    r"""Returns a function generating linear tapers [dbu].

               __
             _/  │ Slab/Exclude
           _/  __│
         _/  _/  │
        │  _/    │
        │_/      │
        │_       │ Core
        │ \_     │
        │_  \_   │
          \_  \__│
            \_   │
              \__│ Slab/Exclude

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

    @kcl.cell(
        basename=basename,
        output_type=KCell,
        ports={"left": ["o1"], "right": ["o2"]},
        **cell_kwargs,
    )
    def taper(
        width1: dbu,
        width2: dbu,
        length: dbu,
        layer: kdb.LayerInfo,
        enclosure: LayerEnclosure | None = None,
    ) -> KCell:
        r"""Linear Taper [um].

                   __
                 _/  │ Slab/Exclude
               _/  __│
             _/  _/  │
            │  _/    │
            │_/      │
            │_       │ Core
            │ \_     │
            │_  \_   │
              \_  \__│
                \_   │
                  \__│ Slab/Exclude

        Args:
            width1: Width of the core on the left side. [dbu]
            width2: Width of the core on the right side. [dbu]
            length: Length of the taper. [dbu]
            layer: Main layer of the taper.
            enclosure: Definition of the slab/exclude.
        """
        c = kcl.kcell()
        if length < 0:
            logger.critical(
                f"Negative lengths are not allowed {length} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length = -length
        if width1 < 0:
            logger.critical(
                f"Negative widths are not allowed {width1} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width1 = -width1

        if width2 < 0:
            logger.critical(
                f"Negative widths are not allowed {width2} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width2 = -width2

        li = c.kcl.layer(layer)
        taper = c.shapes(li).insert(
            kdb.Polygon(
                [
                    kdb.Point(0, int(-width1 / 2)),
                    kdb.Point(0, width1 // 2),
                    kdb.Point(length, width2 // 2),
                    kdb.Point(length, int(-width2 / 2)),
                ]
            )
        )

        c.create_port(trans=kdb.Trans(2, False, 0, 0), width=width1, layer=li)
        c.create_port(trans=kdb.Trans(0, False, length, 0), width=width2, layer=li)

        if enclosure is not None:
            enclosure.apply_minkowski_y(c, layer)
        _info: dict[str, MetaData] = {
            "width1_um": width1 * c.kcl.dbu,
            "width2_um": width2 * c.kcl.dbu,
            "length_um": length * c.kcl.dbu,
            "width1_dbu": width1,
            "width2_dbu": width2,
            "length_dbu": length,
        }
        _info.update(
            _additional_info_func(
                width1=width1,
                width2=width2,
                length=length,
                layer=layer,
                enclosure=enclosure,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)
        c.auto_rename_ports()
        c.boundary = taper.dpolygon

        return c

    return taper


taper = taper_factory(kcl)

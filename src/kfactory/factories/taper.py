"""Taper definitions [dbu].

A linear taper transitions between two cross sections (two core widths) over a
given length::

           __
         _/  │ Slab/Exclude
       _/  __│
     _/  _/  │
    │  _/    │
    │_/      │
    │_       │ Core
    │ \\_     │
    │_  \\_   │
      \\_  \\__│
        \\_   │
          \\__│ Slab/Exclude

The slabs and excludes are part of the cross sections the taper is built from, or
can be given for the legacy ``(width1, width2, layer, enclosure)`` call.

TODO: Non-linear tapers
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Unpack, cast, overload

from .. import kdb
from ..conf import logger
from ..cross_section import (
    AnyCrossSectionInput,
    AsymmetricalCrossSection,
    CrossSectionSpecDict,
    DCrossSectionSpecDict,
)
from ..kcell import KCell
from ..layout import CellKWargs, KCLayout  # noqa: TC001
from ..port import rename_by_direction, rename_clockwise
from ..settings import Info
from ..typings import KC, KC_co, MetaData, dbu
from .utils import _is_additional_info_func, cross_section_from_width

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..enclosure import LayerEnclosure

__all__ = ["taper_factory"]


class TaperFactory(Protocol[KC_co]):
    __name__: str

    def __call__(
        self,
        *,
        length: dbu,
        cross_section1: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        cross_section2: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width1: dbu | None = None,
        width2: dbu | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC_co:
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

        Either pass two cross sections (``cross_section1``/``cross_section2``) or the
        legacy ``width1``/``width2``/``layer``/``enclosure`` (all dbu) which is
        normalized into a pair of symmetric cross sections.

        Args:
            length: Length of the taper. [dbu]
            cross_section1: Cross section of the left side.
            cross_section2: Cross section of the right side.
            width1: Width of the core on the left side. [dbu] (legacy; requires
                ``layer``)
            width2: Width of the core on the right side. [dbu] (legacy; requires
                ``layer``)
            layer: Main layer of the taper. (legacy)
            enclosure: Definition of the slab/exclude. (legacy)
        """
        ...


@overload
def taper_factory(
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
) -> TaperFactory[KCell]: ...
@overload
def taper_factory(
    kcl: KCLayout,
    *,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    output_type: type[KC],
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> TaperFactory[KC]: ...


def taper_factory(
    kcl: KCLayout,
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None = None,
    output_type: type[KC] | None = None,
    port_type: str = "optical",
    **cell_kwargs: Unpack[CellKWargs],
) -> TaperFactory[KC]:
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

    The returned function is the generic interface: it accepts either two cross
    sections (``cross_section1``/``cross_section2``) or the legacy
    ``width1``/``width2``/``layer``/``enclosure`` (all dbu), normalized into a pair
    of symmetric cross sections.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.settings.Info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the taper
            functions' parameters as kwargs and returns a dict with the mapping.
        output_type: The type of the returned cell.
        port_type: Type of the ports the taper gets.
        cell_kwargs: Additional arguments passed as `@kcl.cell(**cell_kwargs)`.
    """
    _additional_info: dict[str, MetaData] = {}
    if _is_additional_info_func(additional_info):
        _additional_info_func: Callable[
            ...,
            dict[str, MetaData],
        ] = additional_info
    else:

        def additional_info_func(
            **kwargs: Any,
        ) -> dict[str, MetaData]:
            return {}

        _additional_info_func = additional_info_func
        _additional_info = additional_info or {}  # ty:ignore[invalid-assignment]

    ports = cell_kwargs.get("ports")
    if ports is None:
        if kcl.rename_function == rename_clockwise:
            cell_kwargs["ports"] = {"left": ["o1"], "right": ["o2"]}
        elif kcl.rename_function == rename_by_direction:
            cell_kwargs["ports"] = {"left": ["W0"], "right": ["E0"]}
    cell_kwargs.setdefault("basename", "taper")
    basename = cell_kwargs["basename"]

    if output_type is not None:
        cell = kcl.cell(output_type=output_type, **cell_kwargs)
    else:
        cell = kcl.cell(output_type=cast("type[KC]", KCell), **cell_kwargs)

    @cell
    def _taper(
        cross_section1: str | AnyCrossSectionInput,
        cross_section2: str | AnyCrossSectionInput,
        length: dbu,
    ) -> KCell:
        """Linear taper defined by two cross sections."""
        c = kcl.kcell()
        if length < 0:
            logger.critical(
                f"Negative lengths are not allowed {length} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length = -length

        xs1 = kcl.get_base_cross_section(cross_section1)
        xs2 = kcl.get_base_cross_section(cross_section2)
        if isinstance(xs1, AsymmetricalCrossSection) or isinstance(
            xs2, AsymmetricalCrossSection
        ):
            raise NotImplementedError(
                "Tapers do not support asymmetric cross sections yet (the straight"
                " edge of the taper is ambiguous for an off-center profile). Got"
                f" {xs1.name!r} -> {xs2.name!r}."
            )
        # The taper applies a single, constant enclosure (and core layer) along its
        # length via minkowski; a differing enclosure between the two cross sections
        # (slab/exclude sections, bbox sections, or main layer) cannot be represented
        # and would be silently taken from cross_section1 only. ``LayerEnclosure``
        # equality is structural (its name normalizes to a geometry hash) and includes
        # the main layer, so this also catches a core-layer mismatch.
        if xs1.enclosure != xs2.enclosure:
            raise ValueError(
                "Taper requires both cross sections to share the same enclosure "
                "(slab/exclude sections and main layer); got "
                f"{xs1.name!r} ({xs1.enclosure.name!r}) and "
                f"{xs2.name!r} ({xs2.enclosure.name!r}). Only the core width may "
                "differ between the two cross sections."
            )
        width1 = xs1.width
        width2 = xs2.width
        layer = xs1.main_layer
        enclosure = xs1.enclosure

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

        c.create_port(
            name="o1",
            trans=kdb.Trans(2, False, 0, 0),
            cross_section=xs1,
            port_type=port_type,
        )
        c.create_port(
            name="o2",
            trans=kdb.Trans(0, False, length, 0),
            cross_section=xs2,
            port_type=port_type,
        )

        enclosure.apply_minkowski_y(c, layer)

        _info: dict[str, MetaData] = {
            "width1_um": c.kcl.to_um(width1),
            "width2_um": c.kcl.to_um(width2),
            "length_um": c.kcl.to_um(length),
            "width1_dbu": width1,
            "width2_dbu": width2,
            "length_dbu": length,
        }
        _info.update(
            _additional_info_func(
                cross_section1=xs1,
                cross_section2=xs2,
                length=length,
            )
        )
        _info.update(_additional_info)
        c.info = Info(**_info)
        c.auto_rename_ports()
        c.boundary = taper.dpolygon

        return c

    @kcl.generic_factory(name=basename)
    def taper(
        *,
        length: dbu,
        cross_section1: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        cross_section2: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width1: dbu | None = None,
        width2: dbu | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC:
        if cross_section1 is None or cross_section2 is None:
            if width1 is None or width2 is None or layer is None:
                raise ValueError(
                    "Provide cross_section1 and cross_section2, or width1, width2 and"
                    " layer (legacy call)."
                )
            xs1 = cross_section_from_width(kcl, width1, layer, enclosure)
            xs2 = cross_section_from_width(kcl, width2, layer, enclosure)
        else:
            xs1 = kcl.get_icross_section(cross_section1)
            xs2 = kcl.get_icross_section(cross_section2)
        return _taper(cross_section1=xs1, cross_section2=xs2, length=length)

    return taper

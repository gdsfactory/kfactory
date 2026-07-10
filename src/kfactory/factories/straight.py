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

The slabs and excludes are part of the cross section the waveguide is built from.
"""

from collections.abc import Callable
from typing import Any, Protocol, Unpack, cast, overload

from .. import kdb
from ..conf import logger
from ..cross_section import (
    AnyCrossSectionInput,
    CrossSectionSpecDict,
    DCrossSectionSpecDict,
)
from ..enclosure import LayerEnclosure, extrude_path_cross_section
from ..kcell import KCell, ProtoTKCell
from ..layout import CellKWargs, KCLayout
from ..port import BasePort, rename_by_direction, rename_clockwise
from ..settings import Info
from ..typings import KC, KC_co, MetaData, dbu
from .utils import (
    _is_additional_info_func,
    cross_section_from_width,
)

__all__ = ["straight_dbu_factory"]


class StraightFactory(Protocol[KC_co]):
    __name__: str

    def __call__(
        self,
        *,
        length: dbu,
        routing_fast: bool = False,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: dbu | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC_co:
        """Waveguide defined by a cross section, length in dbu.

        Either pass a ``cross_section`` (name, spec, or instance) or the legacy
        ``width``/``layer``/``enclosure`` (all dbu) which is normalized into a
        cross section.

        Args:
            length: Waveguide length. [dbu]
            cross_section: Cross section of the waveguide.
            width: Waveguide width. [dbu] (legacy; requires ``layer``)
            layer: Main layer of the waveguide. (legacy)
            enclosure: Definition of slab/excludes. [dbu] (legacy)
        """
        ...


class _StraightFactoryWithRoutingFast[TKC: ProtoTKCell[Any]]:
    __name__: str
    __doc__: str | None
    __module__: str

    def __init__(
        self,
        factory: StraightFactory[TKC],
        routing_fast_factory: StraightFactory[KCell],
    ) -> None:
        self._factory = factory
        self.routing_fast_factory = routing_fast_factory
        self.__name__ = factory.__name__
        self.__doc__ = getattr(factory, "__doc__", None)
        self.__module__ = getattr(factory, "__module__", __name__)

    def __call__(
        self,
        *,
        length: dbu,
        routing_fast: bool = False,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: dbu | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> TKC:
        return self._factory(
            length=length,
            routing_fast=routing_fast,
            cross_section=cross_section,
            width=width,
            layer=layer,
            enclosure=enclosure,
        )


@overload
def straight_dbu_factory(
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
) -> StraightFactory[KCell]: ...
@overload
def straight_dbu_factory(
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
) -> StraightFactory[KC]: ...


def straight_dbu_factory(
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
) -> StraightFactory[KC]:
    """Returns a function generating straights [dbu length].

    The returned function is the generic interface: it accepts either a
    ``cross_section`` or the legacy ``width``/``layer``/``enclosure`` (all dbu),
    normalized into a symmetric cross section.

    Args:
        kcl: The KCLayout which will be owned
        additional_info: Add additional key/values to the
            [`KCell.info`][kfactory.settings.Info]. Can be a static dict
            mapping info name to info value. Or can a callable which takes the straight
            functions' parameters as kwargs and returns a dict with the mapping.
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
    cell_kwargs.setdefault("basename", "straight")
    cast("dict[str, Any]", cell_kwargs).setdefault(
        "drop_params", ("self", "cls", "routing_fast")
    )
    basename = cell_kwargs["basename"]

    if output_type is not None:
        cell = kcl.cell(output_type=output_type, **cell_kwargs)
    else:
        cell = kcl.cell(output_type=cast("type[KC]", KCell), **cell_kwargs)

    def _straight_impl(
        xs: Any,
        length: dbu,
        routing_fast: bool = False,
    ) -> KCell:
        """Waveguide defined by a cross section."""
        c = kcl.kcell()

        if length < 0:
            logger.critical(
                f"Negative lengths are not allowed {length} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length = -length

        extrude_path_cross_section(
            c, [kdb.DPoint(0.0, 0.0), kdb.DPoint(kcl.to_um(length), 0.0)], xs
        )

        if not routing_fast:
            c.create_port(
                name="o1",
                trans=kdb.Trans(2, False, 0, 0),
                cross_section=xs,
                port_type=port_type,
            )
            c.create_port(
                name="o2",
                trans=kdb.Trans(0, False, length, 0),
                cross_section=xs,
                port_type=port_type,
            )

            _info: dict[str, MetaData] = {
                "width_um": kcl.to_um(xs.width),
                "length_um": kcl.to_um(length),
                "width_dbu": xs.width,
                "length_dbu": length,
            }
            _info.update(_additional_info_func(cross_section=xs, length=length))
            _info.update(_additional_info)
            c.info = Info(**_info)

            c.boundary = kdb.DPolygon(c.dbbox())
            c.auto_rename_ports()
        else:
            c._base.ports.extend(
                [
                    BasePort(
                        name="o1",
                        kcl=kcl,
                        cross_section=xs,
                        trans=kdb.Trans(2, False, 0, 0),
                        port_type=port_type,
                    ),
                    BasePort(
                        name="o2",
                        kcl=kcl,
                        cross_section=xs,
                        trans=kdb.Trans(0, False, length, 0),
                        port_type=port_type,
                    ),
                ]
            )
        return c

    @cell
    def _straight(
        cross_section: str | AnyCrossSectionInput,
        length: dbu,
        routing_fast: bool = False,
    ) -> KCell:
        """Waveguide defined by a cross section."""
        return _straight_impl(
            kcl.get_base_cross_section(cross_section),
            length,
            routing_fast=routing_fast,
        )

    @kcl.generic_factory(name=basename)
    def straight(
        *,
        length: dbu,
        routing_fast: bool = False,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: dbu | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KC:
        if cross_section is None:
            if width is None or layer is None:
                raise ValueError(
                    "Provide a cross_section, or width and layer (legacy call)."
                )
            xs = cross_section_from_width(kcl, width, layer, enclosure)
        else:
            xs = kcl.get_icross_section(cross_section)
        return _straight(cross_section=xs, length=length, routing_fast=routing_fast)

    def routing_fast_straight(
        *,
        length: dbu,
        routing_fast: bool = False,
        cross_section: str
        | AnyCrossSectionInput
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | None = None,
        width: dbu | None = None,
        layer: kdb.LayerInfo | None = None,
        enclosure: LayerEnclosure | None = None,
    ) -> KCell:
        if cross_section is None:
            if width is None or layer is None:
                raise ValueError(
                    "Provide a cross_section, or width and layer (legacy call)."
                )
            xs = cross_section_from_width(kcl, width, layer, enclosure)
        else:
            xs = kcl.get_icross_section(cross_section)
        return _straight_impl(xs.base, length, routing_fast=True)

    return _StraightFactoryWithRoutingFast[KC](straight, routing_fast_straight)

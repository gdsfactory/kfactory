"""Utility functions for cell factories."""

from collections.abc import Callable, Sequence
from functools import partial
from typing import TYPE_CHECKING, TypeGuard

from .. import kdb
from ..cross_section import CrossSection, CrossSectionSpecDict
from ..enclosure import (
    LayerEnclosure,
    extrude_path_dynamic_points,
    extrude_path_points,
)
from ..kcell import KCell, VKCell
from ..typings import MetaData

if TYPE_CHECKING:
    from ..layout import KCLayout

__all__ = [
    "boundary_from_shapes",
    "cross_section_from_width",
    "extrude_backbone",
    "extrude_backbone_dynamic",
    "layer_enclosure_to_sections",
]


def boundary_from_shapes(c: KCell) -> kdb.DPolygon | None:
    """Build a cell boundary from its drawn shapes.

    Collects every shape on every layer, merges them, and returns the first polygon
    (in um) of the merged region — i.e. the outline of the cell's footprint. Returns
    `None` if the cell has no shapes.
    """
    region = kdb.Region()
    for layer_index in c.kcl.layer_indexes():
        region.insert(c.shapes(layer_index))
    region.merge()
    if region.is_empty():
        return None
    return region[0].to_dtype(c.kcl.dbu)


def layer_enclosure_to_sections(
    enclosure: LayerEnclosure | None,
) -> list[tuple[kdb.LayerInfo, int] | tuple[kdb.LayerInfo, int, int]]:
    """Flatten a `LayerEnclosure` into `CrossSectionSpec` ``sections`` (dbu)."""
    if enclosure is None:
        return []
    sections: list[tuple[kdb.LayerInfo, int] | tuple[kdb.LayerInfo, int, int]] = []
    for layer, layer_section in enclosure.layer_sections.items():
        for section in layer_section.sections:
            if section.d_min is None:
                sections.append((layer, section.d_max))
            else:
                sections.append((layer, section.d_min, section.d_max))
    return sections


def cross_section_from_width(
    kcl: "KCLayout",
    width: int,
    layer: kdb.LayerInfo,
    enclosure: LayerEnclosure | None = None,
) -> CrossSection:
    """Build a (dbu) symmetric cross section from legacy width/layer/enclosure args."""
    return kcl.get_icross_section(
        CrossSectionSpecDict(
            layer=layer,
            width=width,
            unit="dbu",
            sections=layer_enclosure_to_sections(enclosure),
        ),
        symmetrical=True,
    )


def extrude_backbone(
    c: VKCell,
    backbone: Sequence[kdb.DPoint],
    width: float,
    layer: kdb.LayerInfo,
    start_angle: float,
    end_angle: float,
    dbu: float,
    enclosure: LayerEnclosure | None = None,
) -> None:
    """Extrude a backbone into a virtual cell.

    Args:
        c: target cell
        backbone: backbone to extrude
        width: width to extrude (main layer)
        layer: main layer & reference for enclosure
        enclosure: enclosure to apply
        start_angle: force a certain start angle
        end_angle: force a acertain end angle
        dbu: database unit to use as a reference
    """
    center_path_l, center_path_r = extrude_path_points(
        backbone, width=width, start_angle=start_angle, end_angle=end_angle
    )
    center_path_r.reverse()
    c.shapes(c.kcl.layer(layer)).insert(kdb.DPolygon(center_path_l + center_path_r))

    if enclosure:
        for _layer, sections in enclosure.layer_sections.items():
            _li = c.kcl.layer(_layer)
            for section in sections.sections:
                if section.d_min is not None:
                    inner_l, inner_r = extrude_path_points(
                        backbone,
                        width=width + 2 * section.d_min * dbu,
                        start_angle=start_angle,
                        end_angle=end_angle,
                    )
                    outer_l, outer_r = extrude_path_points(
                        backbone,
                        width=width + 2 * section.d_max * dbu,
                        start_angle=start_angle,
                        end_angle=end_angle,
                    )
                    inner_l.reverse()
                    outer_r.reverse()
                    c.shapes(_li).insert(kdb.DPolygon(outer_l + inner_l))
                    c.shapes(_li).insert(kdb.DPolygon(inner_r + outer_r))
                else:
                    outer_l, outer_r = extrude_path_points(
                        backbone,
                        width=width + 2 * section.d_max * dbu,
                        start_angle=start_angle,
                        end_angle=end_angle,
                    )
                    outer_r.reverse()
                    c.shapes(_li).insert(kdb.DPolygon(outer_l + outer_r))


def extrude_backbone_dynamic(
    c: VKCell,
    backbone: list[kdb.DPoint],
    width1: float,
    width2: float,
    layer: kdb.LayerInfo,
    start_angle: float,
    end_angle: float,
    dbu: float,
    enclosure: LayerEnclosure | None = None,
) -> None:
    """Extrude a backbone into a virtual cell.

    Args:
        c: target cell
        backbone: backbone to extrude
        width1: start width to extrude (main layer)
        width2: end width to extrude (main layer)
        layer: main layer & reference for enclosure
        enclosure: enclosure to apply
        start_angle: force a certain start angle
        end_angle: force a acertain end angle
        dbu: database unit to use as a reference
    """

    def width_f(x: float, a: float) -> float:
        return (width1 - width2) * (1 - x) + width2 + a

    center_path_l, center_path_r = extrude_path_dynamic_points(
        backbone,
        widths=partial(width_f, a=0),
        start_angle=start_angle,
        end_angle=end_angle,
    )
    center_path_r.reverse()
    c.shapes(c.kcl.layer(layer)).insert(kdb.DPolygon(center_path_l + center_path_r))

    if enclosure:
        for _layer, sections in enclosure.layer_sections.items():
            _li = c.kcl.layer(_layer)
            for section in sections.sections:
                if section.d_min is not None:
                    inner_l, inner_r = extrude_path_dynamic_points(
                        backbone,
                        widths=partial(width_f, a=2 * section.d_min * dbu),
                        start_angle=start_angle,
                        end_angle=end_angle,
                    )
                    outer_l, outer_r = extrude_path_dynamic_points(
                        backbone,
                        widths=partial(width_f, a=2 * section.d_max * dbu),
                        start_angle=start_angle,
                        end_angle=end_angle,
                    )
                    inner_l.reverse()
                    outer_r.reverse()
                    c.shapes(_li).insert(kdb.DPolygon(outer_l + inner_l))
                    c.shapes(_li).insert(kdb.DPolygon(inner_r + outer_r))
                else:
                    outer_l, outer_r = extrude_path_dynamic_points(
                        backbone,
                        widths=partial(width_f, a=2 * section.d_max * dbu),
                        start_angle=start_angle,
                        end_angle=end_angle,
                    )
                    outer_r.reverse()
                    c.shapes(_li).insert(kdb.DPolygon(outer_l + outer_r))


def _is_additional_info_func(
    additional_info: Callable[
        ...,
        dict[str, MetaData],
    ]
    | dict[str, MetaData]
    | None,
) -> TypeGuard[Callable[..., dict[str, MetaData]]]:
    return callable(additional_info)

"""Utility functions for cell factories."""

from collections import defaultdict
from collections.abc import Callable, Sequence
from functools import partial
from typing import TYPE_CHECKING, TypeGuard

from .. import kdb
from ..cross_section import CrossSection
from ..enclosure import (
    LayerEnclosure,
    _extrude_path_band_points,
    extrude_path_dynamic_points,
    extrude_path_points,
    path_pts_to_polygon,
)
from ..kcell import KCell, VKCell
from ..typings import MetaData

if TYPE_CHECKING:
    from ..cross_section import AnyCrossSection
    from ..layout import KCLayout

__all__ = [
    "boundary_from_shapes",
    "cross_section_from_width",
    "extrude_backbone",
    "extrude_backbone_cross_section",
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
    return kcl.get_icross_section_from_width(
        width=width,
        layer=layer,
        enclosure=enclosure,
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


def extrude_backbone_cross_section(
    c: VKCell,
    backbone: Sequence[kdb.DPoint],
    cross_section: "AnyCrossSection",
    start_angle: float,
    end_angle: float,
) -> None:
    """Extrude a (symmetric or asymmetric) cross section along a backbone (um).

    The virtual-cell counterpart of
    [`extrude_path_cross_section`][kfactory.enclosure.extrude_path_cross_section]:
    symmetric cross sections reproduce `extrude_backbone` exactly (byte-identical,
    centered width + enclosure annuli); asymmetric ones are extruded as one signed
    band ``[section_min, section_max]`` per strip (main strip + each aux section),
    with strips sharing a layer merged.

    Args:
        c: target virtual cell
        backbone: backbone to extrude (in um)
        cross_section: the cross section to extrude
        start_angle: force a certain start angle
        end_angle: force a certain end angle
    """
    from ..cross_section import AsymmetricalCrossSection

    if not isinstance(cross_section, AsymmetricalCrossSection):
        extrude_backbone(
            c,
            backbone=list(backbone),
            width=c.kcl.to_um(cross_section.width),
            layer=cross_section.main_layer,
            start_angle=start_angle,
            end_angle=end_angle,
            dbu=c.kcl.dbu,
            enclosure=cross_section.enclosure,
        )
        return

    to_um = c.kcl.to_um
    strips: dict[kdb.LayerInfo, list[tuple[float, float]]] = defaultdict(list)
    strips[cross_section.layer].append(
        (to_um(cross_section.section_min), to_um(cross_section.section_max))
    )
    for sec in cross_section.sections:
        strips[sec.layer].append((to_um(sec.section_min), to_um(sec.section_max)))

    for layer, bands in strips.items():
        region = kdb.Region()
        for lo, hi in bands:
            polygon = path_pts_to_polygon(
                *_extrude_path_band_points(
                    list(backbone), lo, hi, start_angle, end_angle
                )
            )
            region.insert(c.kcl.to_dbu(polygon))
        region.merge()
        li = c.kcl.layer(layer)
        for poly in region.each():
            c.shapes(li).insert(poly.to_dtype(c.kcl.dbu))


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

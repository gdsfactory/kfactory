"""Utility functions for virtual cells."""
from collections.abc import Sequence

from ... import kdb
from ...enclosure import LayerEnclosure, extrude_path_points
from ...kcell import VKCell


def extrude_backbone(
    c: VKCell,
    backbone: Sequence[kdb.DPoint],
    width: float,
    layer: int,
    enclosure: LayerEnclosure | None,
    start_angle: float,
    end_angle: float,
    dbu: float,
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
    c.shapes(layer).insert(kdb.DPolygon(center_path_l + center_path_r))

    if enclosure:
        for _layer, sections in enclosure.layer_sections.items():
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
                    c.shapes(_layer).insert(kdb.DPolygon(outer_l + inner_l))
                    c.shapes(_layer).insert(kdb.DPolygon(inner_r + outer_r))
                else:
                    outer_l, outer_r = extrude_path_points(
                        backbone,
                        width=width + 2 * section.d_max * dbu,
                        start_angle=start_angle,
                        end_angle=end_angle,
                    )
                    outer_r.reverse()
                    c.shapes(_layer).insert(kdb.DPolygon(outer_l + outer_r))

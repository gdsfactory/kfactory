"""Extra tests for kfactory.utils.fill module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import kfactory as kf
from kfactory.utils.fill import (
    SparseFillOperator,
    _get_coverage,
    _get_placed_fc,
    fill_tiled,
)

if TYPE_CHECKING:
    from tests.conftest import Layers


def _make_target(kcl: kf.KCLayout, layers: Layers, name: str) -> kf.KCell:
    c = kcl.kcell(name)
    c.shapes(layers.WG).insert(kf.kdb.DPolygon.ellipse(kf.kdb.DBox(5000, 3000), 64))
    c.shapes(layers.WGCLAD).insert(
        kf.kdb.DPolygon(
            [
                kf.kdb.DPoint(0, 0),
                kf.kdb.DPoint(5000, 0),
                kf.kdb.DPoint(5000, 3000),
            ]
        )
    )
    return c


def test_fill_tiled_multi(
    fill_cell: kf.KCell, layers: Layers, kcl: kf.KCLayout
) -> None:
    """Exercise fill_tiled with the multi=True codepath."""
    c = _make_target(kcl, layers, "fill_tiled_multi")
    fill_tiled(
        c,
        fill_cell,
        [(layers.WG, 0)],
        exclude_layers=[(layers.WGCLAD, 0)],
        x_space=5,
        y_space=5,
        multi=True,
    )


def test_fill_tiled_with_fill_regions(
    fill_cell: kf.KCell, layers: Layers, kcl: kf.KCLayout
) -> None:
    """Provide an explicit fill_regions input."""
    c = _make_target(kcl, layers, "fill_tiled_fill_regions")
    region = kf.kdb.Region(kf.kdb.Box(0, 0, 4_000, 2_000))
    fill_tiled(
        c,
        fill_cell,
        fill_regions=[(region, 0.0)],
        exclude_layers=[(layers.WGCLAD, 0)],
        x_space=5,
        y_space=5,
    )


def test_fill_tiled_with_exclude_regions(
    fill_cell: kf.KCell, layers: Layers, kcl: kf.KCLayout
) -> None:
    """Provide an explicit exclude_regions input alongside layers."""
    c = _make_target(kcl, layers, "fill_tiled_exclude_regions")
    exclude = kf.kdb.Region(kf.kdb.Box(0, 0, 1_000, 1_000))
    fill_tiled(
        c,
        fill_cell,
        [(layers.WG, 0)],
        exclude_layers=[(layers.WGCLAD, 0)],
        exclude_regions=[(exclude, 0.0)],
        x_space=5,
        y_space=5,
    )


def test_fill_tiled_no_excludes(
    fill_cell: kf.KCell, layers: Layers, kcl: kf.KCLayout
) -> None:
    """Exercise the queue_str branch where there are no excludes."""
    c = _make_target(kcl, layers, "fill_tiled_no_excludes")
    fill_tiled(c, fill_cell, [(layers.WG, 0)], x_space=5, y_space=5)


def test_fill_tiled_with_fill_regions_and_layers(
    fill_cell: kf.KCell, layers: Layers, kcl: kf.KCLayout
) -> None:
    """Both fill_layers and fill_regions cover the `layers + regions` branch."""
    c = _make_target(kcl, layers, "fill_tiled_layers_and_regions")
    region = kf.kdb.Region(kf.kdb.Box(0, 0, 2_000, 1_000))
    fill_tiled(
        c,
        fill_cell,
        [(layers.WG, 0)],
        fill_regions=[(region, 0.0)],
        exclude_layers=[(layers.WGCLAD, 0)],
        x_space=5,
        y_space=5,
    )


def test_sparse_fill_operator_put() -> None:
    op = SparseFillOperator()
    region = kf.kdb.Region(kf.kdb.Box(0, 0, 100, 100))
    op.put(0, 0, kf.kdb.Box(0, 0, 200, 200), region, dbu=0.001, clip=False)
    assert not op.f_region.is_empty()


def test_get_placed_fc_empty(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell("gpf_empty")
    fill_cell = kcl.kcell("fc_for_gpf_empty")
    fill_cell.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 100, 100))
    pts = _get_placed_fc(parent, fill_cell.cell_index())
    assert pts == set()


def test_get_placed_fc_with_instances(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell("gpf_with_inst")
    fill_cell = kcl.kcell("fc_for_gpf_with_inst")
    fill_cell.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 100, 100))
    parent.create_inst(fill_cell, trans=kf.kdb.Trans(1_000, 2_000))
    parent.create_inst(fill_cell, trans=kf.kdb.Trans(3_000, 4_000))
    pts = _get_placed_fc(parent, fill_cell.cell_index())
    assert kf.kdb.Point(1_000, 2_000) in pts
    assert kf.kdb.Point(3_000, 4_000) in pts


def test_get_coverage(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell("gc_with_inst")
    fill_cell = kcl.kcell("fc_for_gc_with_inst")
    fill_cell.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 100, 100))
    parent.create_inst(fill_cell, trans=kf.kdb.Trans(1_000, 2_000))
    coverage = _get_coverage(parent, fill_cell.cell_index(), margin=200)
    assert not coverage.is_empty()


def test_cover_basic(layers: Layers, kcl: kf.KCLayout) -> None:
    """Call cover() directly with bounded inputs to exercise its body."""
    from kfactory.utils.fill import cover

    top = kcl.kcell("cover_basic")
    fill = kcl.kcell("cover_basic_fill")
    fill.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 100, 100))

    # placement_region is small enough that the while loop terminates fast
    placement = kf.kdb.Region(kf.kdb.Box(0, 0, 600, 600))
    cover_r = kf.kdb.Region(kf.kdb.Box(0, 0, 600, 600))

    cover(
        top_cell=top,
        fill_cell=fill,
        margin=200,
        placement_region=placement,
        cover_region=cover_r,
        fc_bbox_sizing=(50, 25),
    )
    # The while loop should have terminated and the cell has placed at least one inst
    # (or none — both acceptable). What matters is that cover() returned.


def test_cover_warns_when_sizing_inverted(layers: Layers, kcl: kf.KCLayout) -> None:
    """Exercise the warning branch where sizing[1] > sizing[0]."""
    from kfactory.utils.fill import cover

    top = kcl.kcell("cover_inv_sizing")
    fill = kcl.kcell("cover_inv_sizing_fill")
    fill.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 100, 100))

    placement = kf.kdb.Region(kf.kdb.Box(0, 0, 600, 600))
    cover_r = kf.kdb.Region(kf.kdb.Box(0, 0, 600, 600))

    cover(
        top_cell=top,
        fill_cell=fill,
        margin=200,
        placement_region=placement,
        cover_region=cover_r,
        fc_bbox_sizing=(25, 50),  # inverted: 2nd > 1st triggers warning
    )

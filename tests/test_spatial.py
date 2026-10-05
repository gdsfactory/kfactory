"""Tests for kfactory.spatial."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import kfactory as kf
from kfactory.spatial import collect_instance_region

if TYPE_CHECKING:
    from tests.conftest import Layers

_BOX = kf.kdb.Box(0, 0, 1000, 1000)

# Every shape kind a `Shapes` container can hold that has no polygon form.
_NON_POLYGON_SHAPES = [
    pytest.param(kf.kdb.Text("label", kf.kdb.Trans(500, 500)), id="text"),
    pytest.param(kf.kdb.Edge(100, 100, 900, 900), id="edge"),
    pytest.param(
        kf.kdb.EdgePair(
            kf.kdb.Edge(100, 100, 900, 100), kf.kdb.Edge(100, 900, 900, 900)
        ),
        id="edge_pair",
    ),
    pytest.param(kf.kdb.Point(500, 500), id="point"),
]


def _same(a: kf.kdb.Region, b: kf.kdb.Region) -> bool:
    return (a ^ b).is_empty()


def _cell_with(kcl: kf.KCLayout, layer: int, name: str, *shapes: object) -> kf.KCell:
    c = kcl.kcell(name)
    for shape in shapes:
        c.shapes(layer).insert(shape)  # ty:ignore[no-matching-overload]
    return c


@pytest.mark.parametrize("extra", _NON_POLYGON_SHAPES)
def test_collect_instance_region_skips_non_polygon_shapes(
    kcl: kf.KCLayout, layers: Layers, extra: object
) -> None:
    layer = kcl.layer(layers.WG)
    inner = _cell_with(kcl, layer, "inner", _BOX, extra)
    top = kcl.kcell("top")
    inst = top << inner

    region = collect_instance_region(top, layer, inst)

    assert _same(region, kf.kdb.Region(_BOX))


def test_collect_instance_region_keeps_paths(kcl: kf.KCLayout, layers: Layers) -> None:
    layer = kcl.layer(layers.WG)
    path = kf.kdb.Path([kf.kdb.Point(0, 500), kf.kdb.Point(3000, 500)], 200)
    inner = _cell_with(kcl, layer, "inner", _BOX, path)
    top = kcl.kcell("top")
    inst = top << inner

    region = collect_instance_region(top, layer, inst)

    assert _same(region, kf.kdb.Region(_BOX) + kf.kdb.Region(path.polygon()))


def test_collect_instance_region_matches_region_semantics(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    """The helper must drop exactly what `Region(RecursiveShapeIterator)` drops."""
    layer = kcl.layer(layers.WG)
    inner = _cell_with(
        kcl,
        layer,
        "inner",
        _BOX,
        *(p.values[0] for p in _NON_POLYGON_SHAPES),
    )
    top = kcl.kcell("top")
    inst = top << inner
    inst.transform(kf.kdb.Trans(1, False, 5000, 7000))

    region = collect_instance_region(top, layer, inst)

    assert _same(region, kf.kdb.Region(top.begin_shapes_rec(layer)))


def test_collect_instance_region_only_returns_that_instance(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    layer = kcl.layer(layers.WG)
    inner = _cell_with(kcl, layer, "inner", _BOX)
    top = kcl.kcell("top")
    top.shapes(layer).insert(kf.kdb.Box(200, 200, 400, 400))
    first = top << inner
    second = top << inner
    second.transform(kf.kdb.Trans(500, 500))

    region = collect_instance_region(top, layer, first)

    assert _same(region, kf.kdb.Region(_BOX))


def test_collect_instance_region_array_instance(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    layer = kcl.layer(layers.WG)
    inner = _cell_with(
        kcl, layer, "inner", _BOX, kf.kdb.Text("t", kf.kdb.Trans(500, 500))
    )
    top = kcl.kcell("top")
    inst = top.create_inst(
        inner, a=kf.kdb.Vector(2000, 0), b=kf.kdb.Vector(0, 2000), na=3, nb=2
    )

    region = collect_instance_region(top, layer, inst)

    expected = kf.kdb.Region(
        [
            kf.kdb.Polygon(_BOX.moved(2000 * i, 2000 * j))
            for i in range(3)
            for j in range(2)
        ]
    )
    assert _same(region, expected)


def test_collect_instance_region_dtype_instance(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    """A um-space instance must collect the same dbu geometry as its dbu twin."""
    layer = kcl.layer(layers.WG)
    far = kf.kdb.Box(50_000, 50_000, 51_000, 51_000)
    inner = _cell_with(kcl, layer, "inner", _BOX, far)
    top = kcl.dkcell("top")
    inst = top << inner
    inst.transform(kf.kdb.DTrans(100.0, 100.0))

    expected = kf.kdb.Region([kf.kdb.Polygon(_BOX), kf.kdb.Polygon(far)]).moved(
        100_000, 100_000
    )
    assert _same(collect_instance_region(top, layer, inst), expected)
    assert _same(collect_instance_region(top, layer, inst.to_itype()), expected)


def test_instance_overlap_check_with_labelled_instances(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    layer = kcl.layer(layers.WG)
    inner = _cell_with(
        kcl, layer, "inner", _BOX, kf.kdb.Text("label", kf.kdb.Trans(500, 500))
    )
    top = kcl.kcell("top")
    top << inner
    shifted = top << inner
    shifted.transform(kf.kdb.Trans(500, 500))

    db = kf.checks.instance_overlap_check(top, layers=[layer])

    assert db.num_items() == 1

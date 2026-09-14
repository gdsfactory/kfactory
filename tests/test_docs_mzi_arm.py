"""Geometry regressions for the executable MZI arm documentation example."""

import ast
import math
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import kfactory as kf
from kfactory.cells.euler import bend_euler
from kfactory.cells.straight import straight
from tests.conftest import Layers


@pytest.fixture(scope="module")
def mzi_arm(layers: Layers) -> Callable[..., kf.KCell]:
    # Execute the actual documented function without running unrelated plots.
    # Keep one decorated factory/cache for the shared layout across test cases.
    # Redefining it per test creates duplicate names for the reference arm.
    source = Path(__file__).parents[1] / "docs/source/components/cells/overview.py"
    function = next(
        node
        for node in ast.parse(source.read_text()).body
        if isinstance(node, ast.FunctionDef) and node.name == "mzi_arm"
    )
    namespace = {
        "kf": kf,
        "L": layers,
        "bend_euler": bend_euler,
        "straight": straight,
    }
    exec(  # noqa: S102 — exercise the checked-in documentation example
        compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"),
        namespace,
    )
    return cast("Callable[..., kf.KCell]", namespace["mzi_arm"])


@pytest.mark.parametrize("delta_length", [0.0, 1.5, 20.0, 40.0])
def test_mzi_arm_open_path(
    mzi_arm: Callable[..., kf.KCell], layers: Layers, delta_length: float
) -> None:
    arm = mzi_arm(length=20.0, delta_length=delta_length)
    reference = mzi_arm(length=20.0, delta_length=0.0)
    for name, angle in [("o1", 2), ("o2", 0)]:
        assert arm.ports[name].center == reference.ports[name].center
        assert arm.ports[name].angle == angle
    assert arm.ports["o1"].y == arm.ports["o2"].y
    assert arm.ports["o1"].x < arm.ports["o2"].x
    assert arm.dbbox().height() - reference.dbbox().height() == pytest.approx(
        delta_length / 2, abs=arm.kcl.dbu
    )

    junctions: Counter[tuple[int, int]] = Counter()
    straight_lengths = []
    for instance in arm.insts:
        p1, p2 = instance.ports
        junctions.update([p1.center, p2.center])
        if (p1.angle - p2.angle) % 4 == 2:
            straight_lengths.append(math.dist(p1.dcenter, p2.dcenter))
    expected_lengths = [20.0] + ([delta_length / 2] * 2 if delta_length else [])
    assert sorted(straight_lengths) == pytest.approx(sorted(expected_lengths))
    assert {point for point, count in junctions.items() if count == 1} == {
        arm.ports["o1"].center,
        arm.ports["o2"].center,
    }
    assert all(count in (1, 2) for count in junctions.values())

    core = kf.kdb.Region(arm.begin_shapes_rec(arm.kcl.find_layer(layers.WG)))
    core.merge()
    assert core.count() == 1
    assert sum(polygon.holes() for polygon in core.each()) == 0


@pytest.mark.parametrize(("length", "delta_length"), [(0.0, 20.0), (20.0, -1.0)])
def test_mzi_arm_invalid_lengths(
    mzi_arm: Callable[..., kf.KCell], length: float, delta_length: float
) -> None:
    with pytest.raises(ValueError, match="length must be positive"):
        mzi_arm(length=length, delta_length=delta_length)


def test_mzi_arm_layout_export(
    mzi_arm: Callable[..., kf.KCell], tmp_path: Path
) -> None:
    arm = mzi_arm(length=20.0, delta_length=0.0)
    # Export the whole layout, as later routing tests do. Exporting only one
    # arm would miss duplicate names created by earlier fixture invocations.
    arm.kcl.write(tmp_path / "mzi_arms.oas")

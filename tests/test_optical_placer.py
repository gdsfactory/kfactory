"""Tests for kfactory.routing.optical placer internals."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

import pytest

import kfactory as kf
from kfactory.routing.generic import ManhattanRoute
from kfactory.routing.optical import (
    _place_straight,
    _place_tapered_straight,
    place_manhattan,
    place_manhattan_asymmetric,
    place_manhattan_with_sbends,
    vec_angle_sbend,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.conftest import Layers


def _make_o_port(
    kcl: kf.KCLayout, layers: Layers, name: str, angle: int, x: int, y: int
) -> kf.Port:
    return kf.Port(
        name=name,
        trans=kf.kdb.Trans(angle, False, x, y),
        width=500,
        layer_info=layers.WG,
        kcl=kcl,
        port_type="optical",
    )


# vec_angle_sbend


def test_vec_angle_sbend_old_horizontal_up() -> None:
    assert vec_angle_sbend(0, kf.kdb.Vector(10, 5)) == 1


def test_vec_angle_sbend_old_horizontal_down() -> None:
    assert vec_angle_sbend(0, kf.kdb.Vector(10, -5)) == 3


def test_vec_angle_sbend_old_vertical_right() -> None:
    assert vec_angle_sbend(1, kf.kdb.Vector(10, 5)) == 0


def test_vec_angle_sbend_old_vertical_left() -> None:
    assert vec_angle_sbend(1, kf.kdb.Vector(-10, 5)) == 2


# _place_straight


@pytest.mark.parametrize("port_type", ["optical", "electrical"])
@pytest.mark.parametrize("rotation", range(4))
@pytest.mark.parametrize("mirror", [False, True])
@pytest.mark.parametrize("dy", [0, 40_000, -40_000])
@pytest.mark.parametrize("span", [20_000, 80_000])
def test_asymmetric_route_geometry(
    kcl: kf.KCLayout,
    layers: Layers,
    port_type: str,
    rotation: int,
    mirror: bool,
    dy: int,
    span: int,
) -> None:
    """Both GS conductors must remain connected through either bend handedness."""
    xs = kf.AsymmetricalCrossSection(
        layer=layers.WG,
        section_min=-1000,
        section_max=1000,
        sections=(
            kf.CrossSectionLayer(layer=layers.WG, section_min=3000, section_max=5000),
        ),
        radius=10_000,
    )

    def extrude(points: list[kf.kdb.Point], end_angle: int) -> kf.KCell:
        cell = kcl.kcell()
        kf.enclosure.extrude_path_cross_section(
            cell, [kcl.to_um(p) for p in points], xs, 0, end_angle * 90
        )
        cell.create_port(
            name="in",
            cross_section=xs,
            port_type=port_type,
            trans=kf.kdb.Trans(2, True, points[0].to_v()),
        )
        cell.create_port(
            name="out",
            cross_section=xs,
            port_type=port_type,
            trans=kf.kdb.Trans(end_angle, False, points[-1].to_v()),
        )
        return cell

    def straight(width: int, length: int) -> kf.KCell:
        assert width == xs.width
        return extrude([kf.kdb.Point(0, 0), kf.kdb.Point(length, 0)], 0)

    bends = tuple(
        extrude(
            [
                kf.kdb.Point(0, 0),
                kf.kdb.Point(10_000, 0),
                kf.kdb.Point(10_000, sign * 10_000),
            ],
            sign % 4,
        )
        for sign in (1, -1)
    )
    points = (
        [kf.kdb.Point(0, 0), kf.kdb.Point(span, 0)]
        if dy == 0
        else [
            kf.kdb.Point(0, 0),
            kf.kdb.Point(span // 2, 0),
            kf.kdb.Point(span // 2, dy),
            kf.kdb.Point(span, dy),
        ]
    )
    transform = kf.kdb.Trans(rotation, mirror, 100_000, 200_000)
    p1 = kf.Port(
        name="start",
        cross_section=xs,
        kcl=kcl,
        port_type=port_type,
        trans=transform,
    )
    p2 = kf.Port(
        name="end",
        cross_section=xs,
        kcl=kcl,
        port_type=port_type,
        trans=transform * kf.kdb.Trans(2, True, points[-1].to_v()),
    )
    cell = kcl.kcell()
    route = place_manhattan_asymmetric(
        cell,
        p1,
        p2,
        [transform * p for p in points],
        straight_factory=straight,
        bend90_cell=(bends[0], bends[1]),
        port_type=port_type,
    )
    # Include each bend's tangent points so extrusion samples the same corners.
    expected_points = [points[0]]
    for before, corner, after in zip(points, points[1:], points[2:], strict=False):
        incoming, outgoing = corner - before, after - corner
        expected_points.extend(
            [
                corner - incoming * (10_000 / incoming.length()),
                corner,
                corner + outgoing * (10_000 / outgoing.length()),
            ]
        )
    expected_points.append(points[-1])
    expected_points = [
        p
        for i, p in enumerate(expected_points)
        if i == 0 or p != expected_points[i - 1]
    ]
    expected = extrude(expected_points, 0)
    expected_region = kf.kdb.Region(expected.begin_shapes_rec(kcl.layer(layers.WG)))
    expected_region.transform(transform)
    actual = kf.kdb.Region(cell.begin_shapes_rec(kcl.layer(layers.WG)))
    assert (actual ^ expected_region).is_empty()
    assert actual.merged().count() == 2
    assert route.start_port.trans == p1.trans * kf.kdb.Trans.M90
    assert route.end_port.trans == p2.trans * kf.kdb.Trans.M90

    if dy:
        with pytest.raises(ValueError, match="opposite-handed bends"):
            place_manhattan_asymmetric(
                kcl.kcell(),
                p1,
                p2,
                [transform * p for p in points],
                straight_factory=straight,
                bend90_cell=(bends[0], bends[0]),
                port_type=port_type,
            )

    incompatible_end = p2.copy()
    incompatible_end.mirror = not p2.mirror
    with pytest.raises(ValueError, match="incompatible transverse orientations"):
        place_manhattan_asymmetric(
            kcl.kcell(),
            p1,
            incompatible_end,
            [transform * p for p in points],
            straight_factory=straight,
            bend90_cell=(bends[0], bends[1]),
            port_type=port_type,
        )


def test_place_straight_basic(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    c = kcl.kcell("place_straight_basic")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    route = ManhattanRoute(
        backbone=[],
        start_port=p1,
        end_port=p2,
        instances=[],
    )
    _new_p1, _new_p2 = _place_straight(
        c=c,
        straight_factory=straight_factory_dbu,
        purpose=None,
        w=500,
        route=route,
        p1=p1,
        p2=p2,
        route_width=None,
        port_type="optical",
        allow_width_mismatch=False,
        allow_layer_mismatch=False,
        allow_type_mismatch=False,
    )
    assert len(route.instances) == 1
    assert route.length_straights == 50_000


# _place_tapered_straight


def test_place_tapered_straight(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
) -> None:
    c = kcl.kcell("place_tapered_straight")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    taper_factory = kf.factories.taper.taper_factory(kcl=kcl)
    taper_cell = taper_factory(
        width1=500, width2=1000, length=5_000, layer=layers.WG, enclosure=wg_enc
    )
    # Identify the two ports
    tports = list(taper_cell.ports)

    route = ManhattanRoute(
        backbone=[],
        start_port=p1,
        end_port=p2,
        instances=[],
    )
    _place_tapered_straight(
        c=c,
        straight_factory=straight_factory_dbu,
        taper_cell=taper_cell,
        purpose=None,
        route=route,
        p1=p1,
        p2=p2,
        route_width=None,
        taper_ports=(tports[0], tports[1]),
        port_type="optical",
        allow_width_mismatch=True,
        allow_layer_mismatch=False,
        allow_type_mismatch=False,
    )
    # 2 tapers placed, may have 0 or 1 straight in middle depending on length
    assert route.n_taper == 2
    assert len(route.instances) >= 2


# place_manhattan validation


def test_place_manhattan_missing_straight_factory(
    bend90: kf.KCell, kcl: kf.KCLayout, layers: Layers
) -> None:
    c = kcl.kcell("pm_no_sf")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    with pytest.raises(ValueError, match="straight_factory"):
        place_manhattan(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
            bend90_cell=bend90,
        )


def test_place_manhattan_missing_bend90(
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    c = kcl.kcell("pm_no_b90")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    with pytest.raises(ValueError, match="bend90"):
        place_manhattan(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
            straight_factory=straight_factory_dbu,
        )


def test_place_manhattan_extra_kwargs(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    c = kcl.kcell("pm_extra_kwargs")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    with pytest.raises(ValueError, match="not allowed"):
        place_manhattan(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
            bend90_cell=bend90,
            straight_factory=straight_factory_dbu,
            unknown_kwarg=42,
        )


def test_place_manhattan_bend_wrong_port_count(
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    """bend90 cell with no optical ports should error."""
    c = kcl.kcell("pm_bad_b90")
    bad_bend = kcl.kcell("bad_bend")
    bad_bend.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 5000, 5000))
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    with pytest.raises(AttributeError, match="should have 2 ports"):
        place_manhattan(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
            bend90_cell=bad_bend,
            straight_factory=straight_factory_dbu,
        )


def test_place_manhattan_bend_ports_not_90(
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    """bend90 cell with two ports at the same angle should error."""
    c = kcl.kcell("pm_bend_not_90")
    bad_bend = kcl.kcell("bad_bend_not_90")
    bad_bend.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 5000, 5000))
    bad_bend.create_port(
        name="o1",
        trans=kf.kdb.Trans(0, False, 0, 0),
        width=500,
        layer=kcl.find_layer(layers.WG),
        port_type="optical",
    )
    bad_bend.create_port(
        name="o2",
        trans=kf.kdb.Trans(2, False, 5000, 0),
        width=500,
        layer=kcl.find_layer(layers.WG),
        port_type="optical",
    )
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    with pytest.raises(AttributeError, match="90"):
        place_manhattan(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
            bend90_cell=bad_bend,
            straight_factory=straight_factory_dbu,
        )


@pytest.mark.parametrize("point_count", [0, 1])
def test_place_manhattan_too_few_points(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
    point_count: int,
) -> None:
    """Less than 2 points should return an empty route."""
    c = kcl.kcell("pm_few_pts")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    route = place_manhattan(
        c,
        p1,
        p2,
        [kf.kdb.Point(0, 0)] * point_count,
        bend90_cell=bend90,
        straight_factory=straight_factory_dbu,
    )
    assert route.instances == []


def test_place_manhattan_two_points_straight(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    """2 points → single straight."""
    c = kcl.kcell("pm_two_pts")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    route = place_manhattan(
        c,
        p1,
        p2,
        [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
        bend90_cell=bend90,
        straight_factory=straight_factory_dbu,
    )
    assert len(route.instances) == 1


def test_place_manhattan_three_points_with_bend(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    """3 points → straight + bend + straight."""
    c = kcl.kcell("pm_three_pts")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 1, 50_000, 50_000)
    route = place_manhattan(
        c,
        p1,
        p2,
        [
            kf.kdb.Point(0, 0),
            kf.kdb.Point(50_000, 0),
            kf.kdb.Point(50_000, 50_000),
        ],
        bend90_cell=bend90,
        straight_factory=straight_factory_dbu,
    )
    # Should have at least the bend
    assert route.n_bend90 == 1
    assert len(route.instances) >= 1


def test_place_manhattan_small_distance_raises(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    """Too small distance between points raises."""
    c = kcl.kcell("pm_small_dist")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 1, 100, 100)
    with pytest.raises(ValueError, match="too small"):
        place_manhattan(
            c,
            p1,
            p2,
            [
                kf.kdb.Point(0, 0),
                kf.kdb.Point(100, 0),
                kf.kdb.Point(100, 100),
            ],
            bend90_cell=bend90,
            straight_factory=straight_factory_dbu,
        )


def test_place_manhattan_non_manhattan_vec_raises(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    """Non-manhattan vector between points raises."""
    c = kcl.kcell("pm_non_manhattan")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 1, 100_000, 100_000)
    with pytest.raises(ValueError, match=r"[Mm]anhattan"):
        place_manhattan(
            c,
            p1,
            p2,
            [
                kf.kdb.Point(0, 0),
                kf.kdb.Point(50_000, 50_000),
                kf.kdb.Point(100_000, 100_000),
            ],
            bend90_cell=bend90,
            straight_factory=straight_factory_dbu,
            allow_small_routes=True,
        )


def test_place_manhattan_with_taper(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
) -> None:
    """Place manhattan with a taper cell for a 2-point route."""
    c = kcl.kcell("pm_with_taper")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 200_000, 0)

    taper_factory = kf.factories.taper.taper_factory(kcl=kcl)
    taper_cell = taper_factory(
        width1=500, width2=1000, length=10_000, layer=layers.WG, enclosure=wg_enc
    )

    route = place_manhattan(
        c,
        p1,
        p2,
        [kf.kdb.Point(0, 0), kf.kdb.Point(200_000, 0)],
        bend90_cell=bend90,
        straight_factory=straight_factory_dbu,
        taper_cell=taper_cell,
        min_straight_taper=0,
    )
    # Either tapered or plain - at least one instance
    assert len(route.instances) >= 1


def test_place_manhattan_with_bad_taper_widths(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    """Taper whose port widths don't match bend's should raise."""
    c = kcl.kcell("pm_bad_taper_widths")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 200_000, 0)

    bad_taper = kcl.kcell("bad_taper")
    bad_taper.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 10_000, 5000))
    bad_taper.create_port(
        name="o1",
        trans=kf.kdb.Trans(2, False, 0, 0),
        width=998,
        layer=kcl.find_layer(layers.WG),
        port_type="optical",
    )
    bad_taper.create_port(
        name="o2",
        trans=kf.kdb.Trans(0, False, 10_000, 0),
        width=776,
        layer=kcl.find_layer(layers.WG),
        port_type="optical",
    )

    with pytest.raises(AttributeError, match="same width"):
        place_manhattan(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(200_000, 0)],
            bend90_cell=bend90,
            straight_factory=straight_factory_dbu,
            taper_cell=bad_taper,
        )


def test_place_manhattan_with_bad_taper_orientation(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    """Taper with ports not 180° opposing should raise."""
    c = kcl.kcell("pm_bad_taper_orient")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 200_000, 0)

    bad_taper = kcl.kcell("bad_taper_orient")
    bad_taper.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 10_000, 5000))
    bad_taper.create_port(
        name="o1",
        trans=kf.kdb.Trans(0, False, 0, 0),
        width=500,
        layer=kcl.find_layer(layers.WG),
        port_type="optical",
    )
    bad_taper.create_port(
        name="o2",
        trans=kf.kdb.Trans(1, False, 10_000, 0),
        width=1000,
        layer=kcl.find_layer(layers.WG),
        port_type="optical",
    )

    with pytest.raises(AttributeError, match="180"):
        place_manhattan(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(200_000, 0)],
            bend90_cell=bend90,
            straight_factory=straight_factory_dbu,
            taper_cell=bad_taper,
        )


# place_manhattan_with_sbends


def test_place_manhattan_with_sbends_missing_straight_factory(
    bend90: kf.KCell, kcl: kf.KCLayout, layers: Layers
) -> None:
    c = kcl.kcell("pmws_no_sf")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    with pytest.raises(ValueError, match="straight_factory"):
        place_manhattan_with_sbends(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
            bend90_cell=bend90,
        )


def test_place_manhattan_with_sbends_missing_bend90(
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    c = kcl.kcell("pmws_no_b90")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    with pytest.raises(ValueError, match="bend90"):
        place_manhattan_with_sbends(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
            straight_factory=straight_factory_dbu,
        )


def test_place_manhattan_with_sbends_missing_sbend_factory(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    c = kcl.kcell("pmws_no_sbend")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    with pytest.raises(ValueError, match="sbend_function"):
        place_manhattan_with_sbends(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
            bend90_cell=bend90,
            straight_factory=straight_factory_dbu,
        )


def test_place_manhattan_with_sbends_extra_kwargs(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    c = kcl.kcell("pmws_extra_kwargs")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    with pytest.raises(ValueError, match="not allowed"):
        place_manhattan_with_sbends(
            c,
            p1,
            p2,
            [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
            bend90_cell=bend90,
            straight_factory=straight_factory_dbu,
            unknown_kwarg=42,
        )


@pytest.mark.parametrize("point_count", [0, 1])
def test_place_manhattan_with_sbends_too_few_points(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
    point_count: int,
) -> None:
    """Less than 2 points returns empty-instance route."""
    c = kcl.kcell("pmws_few_pts")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)

    def sbend_factory(
        c: kf.ProtoTKCell[kf.kcell.Any], offset: int, length: int, width: int
    ) -> kf.InstanceGroup:
        ig = kf.InstanceGroup()
        sbend = c << kf.cells.euler.bend_s_euler(
            offset=c.kcl.to_um(offset),
            width=c.kcl.to_um(width),
            radius=10,
            layer=layers.WG,
            enclosure=wg_enc,
        )
        ig.add(sbend)
        ig.add_port(name="o1", port=sbend.ports["o1"])
        ig.add_port(name="o2", port=sbend.ports["o2"])
        return ig

    route = place_manhattan_with_sbends(
        c,
        p1,
        p2,
        [kf.kdb.Point(0, 0)] * point_count,
        bend90_cell=bend90,
        straight_factory=straight_factory_dbu,
        sbend_factory=sbend_factory,
    )
    assert route.instances == []


def test_place_manhattan_with_sbends_straight_path(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
) -> None:
    """2 manhattan-aligned points → just a straight, no sbend."""
    c = kcl.kcell("pmws_straight")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)

    def sbend_factory(
        c: kf.ProtoTKCell[kf.kcell.Any], offset: int, length: int, width: int
    ) -> kf.InstanceGroup:
        ig = kf.InstanceGroup()
        sbend = c << kf.cells.euler.bend_s_euler(
            offset=c.kcl.to_um(offset),
            width=c.kcl.to_um(width),
            radius=10,
            layer=layers.WG,
            enclosure=wg_enc,
        )
        ig.add(sbend)
        ig.add_port(name="o1", port=sbend.ports["o1"])
        ig.add_port(name="o2", port=sbend.ports["o2"])
        return ig

    route = place_manhattan_with_sbends(
        c,
        p1,
        p2,
        [kf.kdb.Point(0, 0), kf.kdb.Point(50_000, 0)],
        bend90_cell=bend90,
        straight_factory=straight_factory_dbu,
        sbend_factory=sbend_factory,
    )
    assert len(route.instances) == 1


# route_loopback parallel-error


@pytest.mark.parametrize("with_sbends", [False, True])
@pytest.mark.parametrize("span", [29_999, 30_000, 30_001, 40_000])
def test_symmetric_segment_taper_thresholds(
    kcl: kf.KCLayout,
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    with_sbends: bool,
    span: int,
) -> None:
    """Use the same taper threshold at the start, between bends and at the end."""
    taper = kf.factories.taper.taper_factory(kcl=kcl)(
        width1=500, width2=1000, length=5000, layer=layers.WG, enclosure=wg_enc
    )
    start = _make_o_port(kcl, layers, "start", 0, 0, 0)
    end = _make_o_port(kcl, layers, "end", 2, 2 * span, span)

    def unexpected_sbend(*args: object, **kwargs: object) -> kf.InstanceGroup:
        pytest.fail("A Manhattan backbone should not use S-bends")

    placer = (
        partial(place_manhattan_with_sbends, sbend_factory=unexpected_sbend)
        if with_sbends
        else place_manhattan
    )
    route = placer(
        kcl.kcell(),
        start,
        end,
        [
            kf.kdb.Point(0, 0),
            kf.kdb.Point(span, 0),
            kf.kdb.Point(span, span),
            kf.kdb.Point(2 * span, span),
        ],
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90,
        taper_cell=taper,
        min_straight_taper=10_000,
        purpose="segment-regression",
    )
    expected_tapers = (4 if span >= 30_000 else 0) + (2 if span >= 40_000 else 0)
    assert route.n_taper == expected_tapers
    assert route.n_bend90 == 2
    assert len(route.instances) == 5 + expected_tapers
    assert route.length_straights == 3 * span - 40_000 - expected_tapers * 5000
    assert route.start_port.trans == start.copy_polar().trans
    assert route.end_port.trans == end.copy_polar().trans
    assert all(inst.purpose == "segment-regression" for inst in route.instances)


def test_route_loopback_non_parallel_raises(kcl: kf.KCLayout, layers: Layers) -> None:
    from kfactory.routing.optical import route_loopback

    p1 = kf.Port(
        name="p1",
        trans=kf.kdb.Trans(0, False, 0, 0),
        width=500,
        layer_info=layers.WG,
        kcl=kcl,
    )
    # Different angle AND same x — triggers the error branch
    p2 = kf.Port(
        name="p2",
        trans=kf.kdb.Trans(1, False, 0, 50_000),
        width=500,
        layer_info=layers.WG,
        kcl=kcl,
    )
    with pytest.raises(ValueError, match="parallel"):
        route_loopback(p1, p2, bend90_radius=10_000)


def test_route_loopback_with_start_end_straights(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    from kfactory.routing.optical import route_loopback

    p1 = kf.Port(
        name="p1",
        trans=kf.kdb.Trans(0, False, 0, 0),
        width=500,
        layer_info=layers.WG,
        kcl=kcl,
    )
    p2 = kf.Port(
        name="p2",
        trans=kf.kdb.Trans(0, False, 0, 50_000),
        width=500,
        layer_info=layers.WG,
        kcl=kcl,
    )
    pts = route_loopback(
        p1,
        p2,
        bend90_radius=10_000,
        bend180_radius=20_000,
        start_straight=5_000,
        end_straight=5_000,
    )
    assert isinstance(pts, list)


def test_route_loopback_inside_with_bend180(kcl: kf.KCLayout, layers: Layers) -> None:
    from kfactory.routing.optical import route_loopback

    p1 = kf.Port(
        name="p1",
        trans=kf.kdb.Trans(0, False, 0, 0),
        width=500,
        layer_info=layers.WG,
        kcl=kcl,
    )
    p2 = kf.Port(
        name="p2",
        trans=kf.kdb.Trans(0, False, 0, 50_000),
        width=500,
        layer_info=layers.WG,
        kcl=kcl,
    )
    pts = route_loopback(
        p1,
        p2,
        bend90_radius=10_000,
        bend180_radius=20_000,
        inside=True,
    )
    assert isinstance(pts, list)


def test_route_loopback_with_trans_inputs(layers: Layers) -> None:
    from kfactory.routing.optical import route_loopback

    t1 = kf.kdb.Trans(0, False, 0, 0)
    t2 = kf.kdb.Trans(0, False, 0, 50_000)
    pts = route_loopback(t1, t2, bend90_radius=10_000)
    assert isinstance(pts, list)

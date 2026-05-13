"""Tests for kfactory.routing.optical placer internals."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import kfactory as kf
from kfactory.routing.generic import ManhattanRoute
from kfactory.routing.optical import (
    _place_straight,
    _place_tapered_straight,
    place_manhattan,
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


def test_place_manhattan_too_few_points(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    """Less than 2 points should return an empty route."""
    c = kcl.kcell("pm_few_pts")
    p1 = _make_o_port(kcl, layers, "p1", 0, 0, 0)
    p2 = _make_o_port(kcl, layers, "p2", 2, 50_000, 0)
    route = place_manhattan(
        c,
        p1,
        p2,
        [kf.kdb.Point(0, 0)],
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


def test_place_manhattan_with_sbends_too_few_points(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
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
        [kf.kdb.Point(0, 0)],
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

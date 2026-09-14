"""Asymmetric bundle dispatch and direct electrical profile geometry."""

from collections.abc import Sequence
from typing import Any

import pytest

import kfactory as kf
from kfactory.routing.electrical import place_asymmetric_wire
from kfactory.routing.generic import ManhattanRoute, route_bundle
from kfactory.routing.optical import place_manhattan_asymmetric


@pytest.fixture
def xs() -> kf.AsymmetricalCrossSection:
    return kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0),
        section_min=-1000,
        section_max=1000,
        sections=(
            kf.CrossSectionLayer(
                layer=kf.kdb.LayerInfo(1, 0), section_min=3000, section_max=5000
            ),
            kf.CrossSectionLayer(
                layer=kf.kdb.LayerInfo(2, 0), section_min=-7000, section_max=-6000
            ),
        ),
    )


def test_generic_dispatch_after_sorting(
    kcl: kf.KCLayout, xs: kf.AsymmetricalCrossSection
) -> None:
    """Each actual pair uses its own placer and kwargs in a mixed bundle."""
    symmetric = kf.Port(
        name="s",
        width=2000,
        layer_info=xs.layer,
        kcl=kcl,
        trans=kf.kdb.Trans(0, False, 0, 30_000),
    )
    asymmetric = kf.Port(name="a", cross_section=xs, kcl=kcl, trans=kf.kdb.Trans())
    starts = [symmetric, asymmetric]
    ends = [
        asymmetric.copy_polar(d=80_000, mirror=True),
        symmetric.copy_polar(d=80_000),
    ]
    called = []

    def placer(
        c: kf.KCell,
        p1: kf.Port,
        p2: kf.Port,
        pts: Sequence[kf.kdb.Point],
        route_width: int | None = None,
        **kwargs: Any,
    ) -> ManhattanRoute:
        called.append((p1.is_symmetric(), p2.is_symmetric(), kwargs["kind"]))
        return ManhattanRoute(
            backbone=list(pts), start_port=p1, end_port=p2, instances=[]
        )

    routes = route_bundle(
        c=kcl.kcell(),
        start_ports=[p.base for p in starts],
        end_ports=[p.base for p in ends],
        placer_function=placer,
        placer_kwargs={"kind": "symmetric"},
        asymmetric_placer_function=placer,
        asymmetric_placer_kwargs={"kind": "asymmetric"},
        routing_kwargs={"bend90_radius": 0, "separation": 5000, "sort_ports": True},
        on_collision=None,
        on_placer_error="error",
    )
    assert len(routes) == 2
    assert sorted(called) == [(False, False, "asymmetric"), (True, True, "symmetric")]


@pytest.mark.parametrize("asymmetric_end", [False, True])
def test_generic_missing_asymmetric_placer(
    kcl: kf.KCLayout, xs: kf.AsymmetricalCrossSection, asymmetric_end: bool
) -> None:
    """Check every endpoint before any placer runs, including with errors ignored."""
    sym = kf.Port(
        name="s", width=2000, layer_info=xs.layer, kcl=kcl, trans=kf.kdb.Trans()
    )
    asym = kf.Port(name="a", cross_section=xs, kcl=kcl, trans=kf.kdb.Trans())
    ports = [sym.base, asym.base]

    def unexpected(*args: Any, **kwargs: Any) -> ManhattanRoute:
        pytest.fail("Placement must not start")

    with pytest.raises(ValueError, match="asymmetric_placer_function"):
        route_bundle(
            c=kcl.kcell(),
            start_ports=[sym.base, sym.base] if asymmetric_end else ports,
            end_ports=ports if asymmetric_end else [sym.base, sym.base],
            placer_function=unexpected,
            on_placer_error=None,
        )


def test_generic_rejects_mixed_endpoint_pair(
    kcl: kf.KCLayout, xs: kf.AsymmetricalCrossSection
) -> None:
    start = kf.Port(
        name="s", width=2000, layer_info=xs.layer, kcl=kcl, trans=kf.kdb.Trans()
    )
    end = kf.Port(
        name="a", cross_section=xs, kcl=kcl, trans=kf.kdb.Trans(2, True, 80_000, 0)
    )

    def unexpected(*args: Any, **kwargs: Any) -> ManhattanRoute:
        pytest.fail("Placement must not start")

    with pytest.raises(ValueError, match="explicit transition"):
        route_bundle(
            c=kcl.kcell(),
            start_ports=[start.base],
            end_ports=[end.base],
            placer_function=unexpected,
            asymmetric_placer_function=unexpected,
            routing_kwargs={"bend90_radius": 0, "separation": 5000},
            on_placer_error=None,
        )


@pytest.mark.parametrize("mismatch", ["profile", "mirror"])
def test_generic_checks_all_asymmetric_pairs_before_placement(
    kcl: kf.KCLayout, xs: kf.AsymmetricalCrossSection, mismatch: str
) -> None:
    first = kf.Port(name="first", cross_section=xs, kcl=kcl, trans=kf.kdb.Trans())
    second = first.copy()
    second.trans = kf.kdb.Trans(0, False, 0, 30_000)
    ends = [p.copy_polar(d=80_000, mirror=True) for p in (first, second)]
    if mismatch == "mirror":
        ends[1].mirror = False
    else:
        other = kf.AsymmetricalCrossSection(
            layer=xs.layer,
            section_min=xs.section_min,
            section_max=xs.section_max,
            sections=(
                kf.CrossSectionLayer(
                    layer=xs.layer, section_min=5000, section_max=6000
                ),
            ),
        )
        ends[1] = kf.Port(
            name="other", cross_section=other, kcl=kcl, trans=ends[1].trans
        )

    def unexpected(*args: Any, **kwargs: Any) -> ManhattanRoute:
        pytest.fail("Every endpoint pair must be validated before placing any route")

    with pytest.raises(ValueError):
        route_bundle(
            c=kcl.kcell(),
            start_ports=[first.base, second.base],
            end_ports=[p.base for p in ends],
            placer_function=unexpected,
            asymmetric_placer_function=unexpected,
            routing_kwargs={"bend90_radius": 0, "separation": 5000},
            on_placer_error=None,
        )


@pytest.mark.parametrize("rotation", range(4))
@pytest.mark.parametrize("mirror", [False, True])
def test_electrical_asymmetric_geometry(
    kcl: kf.KCLayout, xs: kf.AsymmetricalCrossSection, rotation: int, mirror: bool
) -> None:
    """Exact mitered GS bands on two layers, with both turn directions."""
    transform = kf.kdb.Trans(rotation, mirror, 100_000, 200_000)
    points = [
        kf.kdb.Point(0, 0),
        kf.kdb.Point(40_000, 0),
        kf.kdb.Point(40_000, 40_000),
        kf.kdb.Point(80_000, 40_000),
    ]
    p1 = kf.Port(
        name="a", cross_section=xs, kcl=kcl, trans=transform, port_type="electrical"
    )
    p2 = kf.Port(
        name="a",
        cross_section=xs,
        kcl=kcl,
        port_type="electrical",
        trans=transform * kf.kdb.Trans(2, True, 80_000, 40_000),
    )
    cell = kcl.kcell()
    route = place_asymmetric_wire(cell, p1, p2, [transform * p for p in points])
    expected: dict[kf.kdb.LayerInfo, kf.kdb.Region] = {}
    for section in xs.get_sections():
        lo, hi = section.section_min, section.section_max
        polygon = kf.kdb.Polygon(
            [
                kf.kdb.Point(0, lo),
                kf.kdb.Point(40_000 - lo, lo),
                kf.kdb.Point(40_000 - lo, 40_000 + lo),
                kf.kdb.Point(80_000, 40_000 + lo),
                kf.kdb.Point(80_000, 40_000 + hi),
                kf.kdb.Point(40_000 - hi, 40_000 + hi),
                kf.kdb.Point(40_000 - hi, hi),
                kf.kdb.Point(0, hi),
            ]
        )
        expected.setdefault(section.layer, kf.kdb.Region()).insert(
            polygon.transformed(transform)
        )
    for layer, region in expected.items():
        actual = kf.kdb.Region(cell.begin_shapes_rec(kcl.layer(layer)))
        assert (actual ^ region).is_empty()
    assert len(route.polygons[xs.layer]) == 2
    assert route.length == 120_000


@pytest.mark.parametrize("dtype", [False, True])
def test_electrical_bundle_defaults_to_asymmetric_placer(
    kcl: kf.KCLayout, xs: kf.AsymmetricalCrossSection, dtype: bool
) -> None:
    cell = kcl.kcell()
    p1 = kf.Port(
        name="a",
        cross_section=xs,
        kcl=kcl,
        trans=kf.kdb.Trans(),
        port_type="electrical",
    )
    p2 = p1.copy_polar(d=80_000, mirror=True)
    if dtype:
        routes = kf.routing.electrical.route_bundle(
            cell.to_dtype(),
            [p1.to_dtype()],
            [p2.to_dtype()],
            separation=10,
            on_collision=None,
            on_placer_error="error",
        )
    else:
        routes = kf.routing.electrical.route_bundle(
            cell,
            [p1],
            [p2],
            separation=10_000,
            on_collision=None,
            on_placer_error="error",
        )
    assert len(routes) == 1
    assert len(routes[0].polygons[xs.layer]) == 2
    assert len(routes[0].polygons) == 2


def test_asymmetric_tapered_straight(
    kcl: kf.KCLayout, xs: kf.AsymmetricalCrossSection
) -> None:
    """Two tapers widen the core without reflecting or dropping auxiliary bands."""
    wide = kf.AsymmetricalCrossSection(
        layer=xs.layer, section_min=-1500, section_max=1500, sections=xs.sections
    )
    taper = kcl.kcell()
    taper.shapes(kcl.layer(xs.layer)).insert(
        kf.kdb.Polygon(
            [
                kf.kdb.Point(0, -1000),
                kf.kdb.Point(5000, -1500),
                kf.kdb.Point(5000, 1500),
                kf.kdb.Point(0, 1000),
            ]
        )
    )
    for section in xs.sections:
        taper.shapes(kcl.layer(section.layer)).insert(
            kf.kdb.Box(0, section.section_min, 5000, section.section_max)
        )
    taper.create_port(name="in", cross_section=xs, trans=kf.kdb.Trans(2, True, 0, 0))
    taper.create_port(name="out", cross_section=wide, trans=kf.kdb.Trans(5000, 0))

    def straight(width: int, length: int) -> kf.KCell:
        assert width == wide.width
        cell = kcl.kcell()
        for section in wide.get_sections():
            cell.shapes(kcl.layer(section.layer)).insert(
                kf.kdb.Box(0, section.section_min, length, section.section_max)
            )
        cell.create_port(
            name="in", cross_section=wide, trans=kf.kdb.Trans(2, True, 0, 0)
        )
        cell.create_port(name="out", cross_section=wide, trans=kf.kdb.Trans(length, 0))
        return cell

    # Only port geometry is needed: this backbone has no corners to place.
    left, right = kcl.kcell(), kcl.kcell()
    for bend, sign in ((left, 1), (right, -1)):
        bend.create_port(name="in", cross_section=xs, trans=kf.kdb.Trans(2, True, 0, 0))
        bend.create_port(
            name="out",
            cross_section=xs,
            trans=kf.kdb.Trans(sign % 4, False, 10_000, sign * 10_000),
        )
    start = kf.Port(name="start", cross_section=xs, kcl=kcl, trans=kf.kdb.Trans())
    end = start.copy_polar(d=80_000, mirror=True)
    cell = kcl.kcell()
    route = place_manhattan_asymmetric(
        cell,
        start,
        end,
        [kf.kdb.Point(0, 0), kf.kdb.Point(80_000, 0)],
        straight_factory=straight,
        bend90_cell=(left, right),
        taper_cell=taper,
    )
    assert route.n_taper == 2
    assert route.length_straights == 70_000
    actual = kf.kdb.Region(cell.begin_shapes_rec(kcl.layer(xs.layer)))
    expected = kf.kdb.Region(
        kf.kdb.Polygon(
            [
                kf.kdb.Point(0, -1000),
                kf.kdb.Point(5000, -1500),
                kf.kdb.Point(75_000, -1500),
                kf.kdb.Point(80_000, -1000),
                kf.kdb.Point(80_000, 1000),
                kf.kdb.Point(75_000, 1500),
                kf.kdb.Point(5000, 1500),
                kf.kdb.Point(0, 1000),
            ]
        )
    )
    expected.insert(kf.kdb.Box(0, 3000, 80_000, 5000))
    assert (actual ^ expected).is_empty()


@pytest.mark.parametrize("override", ["width", "layer", "profile", "mirror"])
def test_asymmetric_wire_rejects_incompatible_profiles(
    kcl: kf.KCLayout, xs: kf.AsymmetricalCrossSection, override: str
) -> None:
    start = kf.Port(name="start", cross_section=xs, kcl=kcl, trans=kf.kdb.Trans())
    end = start.copy_polar(d=80_000, mirror=True)
    if override == "mirror":
        end.mirror = False
    elif override == "profile":
        different = kf.AsymmetricalCrossSection(
            layer=xs.layer,
            section_min=-1000,
            section_max=1000,
            sections=(
                kf.CrossSectionLayer(
                    layer=xs.layer, section_min=4000, section_max=6000
                ),
            ),
        )
        end = kf.Port(name="end", cross_section=different, kcl=kcl, trans=end.trans)
    cell = kcl.kcell()
    with pytest.raises(ValueError):
        place_asymmetric_wire(
            cell,
            start,
            end,
            [kf.kdb.Point(0, 0), kf.kdb.Point(80_000, 0)],
            route_width=3000 if override == "width" else None,
            layer_info=kf.kdb.LayerInfo(99, 0) if override == "layer" else None,
        )
    assert cell.bbox().empty()

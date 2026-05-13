"""Tests for kfactory.routing.utils module."""

from __future__ import annotations

import kfactory as kf
from kfactory.routing.utils import RouteDebug


def test_route_debug_defaults() -> None:
    rd = RouteDebug()
    assert rd.fan_in_region.is_empty()
    assert rd.fan_out_region.is_empty()
    assert rd.waypoints_region.is_empty()
    # post_init should set merged_semantics to False
    assert rd.fan_in_region.merged_semantics is False
    assert rd.fan_out_region.merged_semantics is False
    assert rd.waypoints_region.merged_semantics is False


def test_route_debug_repr_does_not_crash() -> None:
    # to_dict is buggy (iterates over all fields including dicts), but the
    # model itself should still be representable.
    rd = RouteDebug()
    assert isinstance(repr(rd), str)


def test_route_debug_to_markers_empty() -> None:
    rd = RouteDebug()
    markers = rd.to_markers(dbu=0.001)
    assert markers == []


def test_route_debug_to_markers_with_shapes() -> None:
    rd = RouteDebug()
    rd.fan_in_region.insert(kf.kdb.Box(0, 0, 1000, 1000))
    rd.fan_out_region.insert(kf.kdb.Box(0, 0, 500, 500))
    rd.waypoints_region.insert(kf.kdb.Box(0, 0, 200, 200))

    markers = rd.to_markers(dbu=0.001)
    # one polygon per region
    assert len(markers) == 3
    for shape, cfg in markers:
        assert hasattr(shape, "bbox") or hasattr(shape, "to_s")
        assert "color" in cfg


def test_route_debug_marker_configs_are_marker_config() -> None:
    rd = RouteDebug()
    # Each marker config field should be a MarkerConfig (TypedDict-shaped dict)
    assert "color" in rd.fan_in_marker_config
    assert "color" in rd.fan_out_marker_config
    assert "color" in rd.waypoints_marker_config


def test_route_debug_to_markers_with_text_properties() -> None:
    """to_markers should also yield markers for text-valued properties."""
    from tests.conftest import Layers

    rd = RouteDebug()
    layers = Layers()
    kcl = kf.KCLayout("ROUTE_DEBUG_PROP", infos=Layers)
    c = kcl.kcell(name="route_debug_to_markers_props")
    l_ = 3
    transformations = [kf.kdb.Trans(0, False, 0, i * 50_000) for i in range(l_)]
    start_ports = [
        kf.Port(name=f"in{i}", width=500, layer_info=layers.WG, kcl=kcl, trans=trans)
        for i, trans in enumerate(transformations)
    ]
    end_ports = [
        kf.Port(
            name=f"out_{i}",
            width=500,
            layer_info=layers.WG,
            kcl=kcl,
            trans=kf.kdb.Trans(2, False, 500_000, 0) * trans,
        )
        for i, trans in enumerate(transformations)
    ]

    bend90 = kf.factories.circular.bend_circular_factory(kcl=kcl)(
        width=0.5, radius=5, layer=layers.WG, angle=90
    )
    sf = kf.factories.straight.straight_dbu_factory(kcl=kcl)

    kf.routing.optical.route_bundle(  # ty:ignore[no-matching-overload]
        c,
        start_ports,
        end_ports,
        separation=4000,
        straight_factory=lambda **kwargs: sf(layer=layers.WG, **kwargs),
        bend90_cell=bend90,
        waypoints=[
            kf.kdb.Point(250_000, 0),
            kf.kdb.Point(250_000, 100_000),
            kf.kdb.Point(300_000, 100_000),
        ],
        sort_ports=True,
        route_debug=rd,
    )
    # Regions should now contain polygons with text properties
    assert not rd.fan_in_region.is_empty()

    markers = rd.to_markers(dbu=kcl.dbu)
    # markers list should include polygons + their parsed text labels
    assert len(markers) > 3

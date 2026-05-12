"""Tests for kfactory.routing.length_functions module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import kfactory as kf
from kfactory.routing.generic import ManhattanRoute
from kfactory.routing.length_functions import (
    LengthFunction,
    get_length_from_area,
    get_length_from_backbone,
    get_length_from_info,
)

if TYPE_CHECKING:
    from tests.conftest import Layers


def _make_port(kcl: kf.KCLayout, layers: Layers) -> kf.Port:
    return kf.Port(
        name="o1",
        trans=kf.kdb.Trans.R0,
        layer=kcl.find_layer(layers.WG),
        width=500,
        port_type="optical",
        kcl=kcl,
    )


def test_length_function_protocol() -> None:
    assert isinstance(get_length_from_backbone, LengthFunction)
    assert isinstance(get_length_from_area(), LengthFunction)


def test_get_length_from_backbone(kcl: kf.KCLayout, layers: Layers) -> None:
    port = _make_port(kcl, layers)
    route = ManhattanRoute(
        backbone=[
            kf.kdb.Point(0, 0),
            kf.kdb.Point(1000, 0),
            kf.kdb.Point(1000, 2000),
        ],
        start_port=port,
        end_port=port,
    )
    assert get_length_from_backbone(route) == 3000


def test_get_length_from_backbone_single_point(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    port = _make_port(kcl, layers)
    route = ManhattanRoute(
        backbone=[kf.kdb.Point(0, 0)],
        start_port=port,
        end_port=port,
    )
    assert get_length_from_backbone(route) == 0


def test_get_length_from_area_empty_instances(kcl: kf.KCLayout, layers: Layers) -> None:
    port = _make_port(kcl, layers)
    route = ManhattanRoute(
        backbone=[kf.kdb.Point(0, 0), kf.kdb.Point(1000, 0)],
        start_port=port,
        end_port=port,
        instances=[],
    )
    assert get_length_from_area()(route) == 0


def test_get_length_from_info(kcl: kf.KCLayout, layers: Layers) -> None:
    port = _make_port(kcl, layers)
    # Create a real instance whose cell has an info["length"] value
    inner = kcl.kcell("len_info_inner")
    inner.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 1000, 500))
    inner.info["length"] = 1000

    parent = kcl.kcell("len_info_parent")
    inst = parent.create_inst(inner)

    route = ManhattanRoute(
        backbone=[kf.kdb.Point(0, 0), kf.kdb.Point(1000, 0)],
        start_port=port,
        end_port=port,
        instances=[inst],
    )
    assert get_length_from_info(route) == 1000


def test_get_length_from_info_custom_attribute(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    port = _make_port(kcl, layers)
    inner = kcl.kcell("len_info_custom")
    inner.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 1000, 500))
    inner.info["my_attr"] = 42

    parent = kcl.kcell("len_info_custom_parent")
    inst = parent.create_inst(inner)

    route = ManhattanRoute(
        backbone=[kf.kdb.Point(0, 0)],
        start_port=port,
        end_port=port,
        instances=[inst],
    )
    assert get_length_from_info(route, attribute_name="my_attr") == 42

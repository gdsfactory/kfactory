"""Extra factory tests targeting coverage in bezier and virtual factories."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

import kfactory as kf
from kfactory.factories.bezier import bend_s_bezier_factory, bezier_curve
from kfactory.factories.virtual.circular import virtual_bend_circular_factory

if TYPE_CHECKING:
    from tests.conftest import Layers


def test_bezier_curve_2_points() -> None:
    pts = bezier_curve(
        t=np.linspace(0, 1, 5),
        control_points=[(0.0, 0.0), (10.0, 5.0)],
    )
    assert len(pts) == 5
    assert pts[0].x == pytest.approx(0.0)
    assert pts[-1].x == pytest.approx(10.0)


def test_bezier_curve_cubic() -> None:
    pts = bezier_curve(
        t=np.linspace(0, 1, 50),
        control_points=[(0.0, 0.0), (5.0, 0.0), (5.0, 10.0), (10.0, 10.0)],
    )
    assert len(pts) == 50
    assert pts[0].x == pytest.approx(0.0)
    assert pts[-1].x == pytest.approx(10.0)


def test_bend_s_bezier_basic(kcl: kf.KCLayout, layers: Layers) -> None:
    factory = bend_s_bezier_factory(kcl=kcl)
    c = factory(width=0.5, height=2.0, length=10.0, layer=layers.WG)
    assert isinstance(c, kf.KCell)
    assert len(c.ports) >= 2


def test_bend_s_bezier_with_enclosure(kcl: kf.KCLayout, layers: Layers) -> None:
    enc = kf.LayerEnclosure(
        [(layers.WGCLAD, 1000)], main_layer=layers.WG, kcl=kcl, name="benc"
    )
    factory = bend_s_bezier_factory(kcl=kcl)
    c = factory(width=0.5, height=2.0, length=10.0, layer=layers.WG, enclosure=enc)
    assert isinstance(c, kf.KCell)


def test_bend_s_bezier_with_static_info(kcl: kf.KCLayout, layers: Layers) -> None:
    factory = bend_s_bezier_factory(kcl=kcl, additional_info={"static": "val"})
    c = factory(width=0.5, height=1.0, length=8.0, layer=layers.WG)
    assert c.info["static"] == "val"


def test_bend_s_bezier_with_callable_info(kcl: kf.KCLayout, layers: Layers) -> None:
    def info_func(**kwargs: object) -> dict[str, object]:
        xs = kwargs["cross_section"]
        return {"computed_width": xs.width}  # ty:ignore[unresolved-attribute]

    factory = bend_s_bezier_factory(kcl=kcl, additional_info=info_func)  # ty:ignore[invalid-argument-type]
    c = factory(width=0.5, height=1.0, length=8.0, layer=layers.WG)
    assert c.info["computed_width"] == 500


def test_virtual_bend_circular_basic(kcl: kf.KCLayout, layers: Layers) -> None:
    factory = virtual_bend_circular_factory(kcl=kcl)
    c = factory(width=0.5, radius=10.0, layer=layers.WG)
    assert isinstance(c, kf.VKCell)


def test_virtual_bend_circular_negative_angle(kcl: kf.KCLayout, layers: Layers) -> None:
    factory = virtual_bend_circular_factory(kcl=kcl)
    # negative angle gets flipped positive
    c = factory(width=0.5, radius=10.0, layer=layers.WG, angle=-90)
    assert isinstance(c, kf.VKCell)


def test_virtual_bend_circular_negative_width(kcl: kf.KCLayout, layers: Layers) -> None:
    factory = virtual_bend_circular_factory(kcl=kcl)
    # negative width gets flipped positive
    c = factory(width=-0.5, radius=10.0, layer=layers.WG, angle=90)
    assert isinstance(c, kf.VKCell)


def test_virtual_bend_circular_with_enclosure(kcl: kf.KCLayout, layers: Layers) -> None:
    enc = kf.LayerEnclosure(
        [(layers.WGCLAD, 1000)], main_layer=layers.WG, kcl=kcl, name="vbenc"
    )
    factory = virtual_bend_circular_factory(kcl=kcl)
    c = factory(width=0.5, radius=10.0, layer=layers.WG, enclosure=enc)
    assert isinstance(c, kf.VKCell)


def test_virtual_bend_circular_with_static_info(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    factory = virtual_bend_circular_factory(kcl=kcl, additional_info={"k": "v"})
    c = factory(width=0.5, radius=10.0, layer=layers.WG)
    assert c.info["k"] == "v"


def test_virtual_bend_circular_with_callable_info(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    def info_func(**kwargs: object) -> dict[str, object]:
        return {"rad": kwargs["radius"]}

    factory = virtual_bend_circular_factory(kcl=kcl, additional_info=info_func)  # ty:ignore[invalid-argument-type]
    c = factory(width=0.5, radius=10.0, layer=layers.WG)
    assert c.info["rad"] == 10.0

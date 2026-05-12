"""Tests for kfactory.factories.utils module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import kfactory as kf
from kfactory.factories.utils import (
    _is_additional_info_func,
    extrude_backbone,
    extrude_backbone_dynamic,
)

if TYPE_CHECKING:
    from tests.conftest import Layers


def test_is_additional_info_func_callable() -> None:
    def f() -> dict[str, str]:
        return {}

    assert _is_additional_info_func(f) is True  # ty:ignore[invalid-argument-type]


def test_is_additional_info_func_dict() -> None:
    assert _is_additional_info_func({"a": 1}) is False


def test_is_additional_info_func_none() -> None:
    assert _is_additional_info_func(None) is False


def _make_backbone() -> list[kf.kdb.DPoint]:
    return [kf.kdb.DPoint(0, 0), kf.kdb.DPoint(10, 0), kf.kdb.DPoint(20, 0)]


def test_extrude_backbone_no_enclosure(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell("eb_no_enc")
    extrude_backbone(
        c,
        backbone=_make_backbone(),
        width=1.0,
        layer=layers.WG,
        start_angle=0,
        end_angle=0,
        dbu=c.kcl.dbu,
    )
    # We at least inserted shapes for the main layer
    assert len(list(c.shapes(c.kcl.layer(layers.WG)).each())) >= 1


def test_extrude_backbone_with_enclosure_dmax_only(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    enc = kf.LayerEnclosure([(layers.WGCLAD, 1000)], main_layer=layers.WG, kcl=kcl)
    c = kcl.vkcell("eb_with_enc_dmax")
    extrude_backbone(
        c,
        backbone=_make_backbone(),
        width=1.0,
        layer=layers.WG,
        start_angle=0,
        end_angle=0,
        dbu=c.kcl.dbu,
        enclosure=enc,
    )
    # main + enclosure layer should have shapes
    assert len(list(c.shapes(c.kcl.layer(layers.WG)).each())) >= 1
    assert len(list(c.shapes(c.kcl.layer(layers.WGCLAD)).each())) >= 1


def test_extrude_backbone_with_enclosure_dmin_dmax(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    enc = kf.LayerEnclosure([(layers.WGCLAD, 500, 1000)], main_layer=layers.WG, kcl=kcl)
    c = kcl.vkcell("eb_with_enc_dmin_dmax")
    extrude_backbone(
        c,
        backbone=_make_backbone(),
        width=1.0,
        layer=layers.WG,
        start_angle=0,
        end_angle=0,
        dbu=c.kcl.dbu,
        enclosure=enc,
    )
    # the enclosure layer should have two polygons (one per side)
    assert len(list(c.shapes(c.kcl.layer(layers.WGCLAD)).each())) >= 2


def test_extrude_backbone_dynamic_no_enclosure(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    c = kcl.vkcell("ebd_no_enc")
    extrude_backbone_dynamic(
        c,
        backbone=_make_backbone(),
        width1=1.0,
        width2=2.0,
        layer=layers.WG,
        start_angle=0,
        end_angle=0,
        dbu=c.kcl.dbu,
    )
    assert len(list(c.shapes(c.kcl.layer(layers.WG)).each())) >= 1


def test_extrude_backbone_dynamic_with_enclosure_dmax(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    enc = kf.LayerEnclosure([(layers.WGCLAD, 1000)], main_layer=layers.WG, kcl=kcl)
    c = kcl.vkcell("ebd_with_enc_dmax")
    extrude_backbone_dynamic(
        c,
        backbone=_make_backbone(),
        width1=1.0,
        width2=2.0,
        layer=layers.WG,
        start_angle=0,
        end_angle=0,
        dbu=c.kcl.dbu,
        enclosure=enc,
    )
    assert len(list(c.shapes(c.kcl.layer(layers.WGCLAD)).each())) >= 1


def test_extrude_backbone_dynamic_with_enclosure_dmin_dmax(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    enc = kf.LayerEnclosure([(layers.WGCLAD, 500, 1000)], main_layer=layers.WG, kcl=kcl)
    c = kcl.vkcell("ebd_with_enc_dmin_dmax")
    extrude_backbone_dynamic(
        c,
        backbone=_make_backbone(),
        width1=1.0,
        width2=2.0,
        layer=layers.WG,
        start_angle=0,
        end_angle=0,
        dbu=c.kcl.dbu,
        enclosure=enc,
    )
    assert len(list(c.shapes(c.kcl.layer(layers.WGCLAD)).each())) >= 2

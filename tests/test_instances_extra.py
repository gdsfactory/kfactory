"""Extra tests for instances.py covering missing branches."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import kfactory as kf

if TYPE_CHECKING:
    from tests.conftest import Layers


def _straight(kcl: kf.KCLayout, layers: Layers) -> kf.KCell:
    return kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)


def test_instances_repr_str(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    _ = c << _straight(kcl, layers)
    assert "n=1" in repr(c.insts)
    assert "Instances" in str(c.insts)


def test_instances_iter_returns_instance(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    _ = c << _straight(kcl, layers)
    items = list(c.insts)
    assert len(items) == 1
    assert isinstance(items[0], kf.Instance)


def test_dinstances_iter_returns_dinstance(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.dkcell()
    _ = c << _straight(kcl, layers)
    items = list(c.insts)
    assert len(items) == 1
    assert isinstance(items[0], kf.DInstance)


def test_instances_getitem_by_name(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    ref = c << _straight(kcl, layers)
    ref.name = "named_inst"
    assert isinstance(c.insts["named_inst"], kf.Instance)


def test_dinstances_getitem_by_name(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.dkcell()
    ref = c << _straight(kcl, layers)
    ref.name = "dnamed_inst"
    assert isinstance(c.insts["dnamed_inst"], kf.DInstance)


def test_instances_get_missing_name_raises(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    _ = c << _straight(kcl, layers)
    with pytest.raises(ValueError, match="not found"):
        c.insts["missing"]


def test_instances_contains_false_on_missing(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    _ = c << _straight(kcl, layers)
    assert "missing" not in c.insts


def test_instances_clear(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    _ = c << _straight(kcl, layers)
    _ = c << _straight(kcl, layers)
    assert len(c.insts) == 2
    c.insts.clear()
    assert len(c.insts) == 0


def test_instances_delitem_by_int(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    _ = c << _straight(kcl, layers)
    _ = c << _straight(kcl, layers)
    del c.insts[0]
    assert len(c.insts) == 1


def test_instances_delitem_by_instance(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    ref1 = c << _straight(kcl, layers)
    _ = c << _straight(kcl, layers)
    del c.insts[ref1]
    assert len(c.insts) == 1


def test_instances_remove(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    ref1 = c << _straight(kcl, layers)
    c.insts.remove(ref1)
    assert len(c.insts) == 0


def test_instances_to_dtype_to_itype(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    _ = c << _straight(kcl, layers)
    d = c.insts.to_dtype()
    assert isinstance(d, kf.DInstances)
    i = d.to_itype()
    assert isinstance(i, kf.Instances)


def test_instances_eq_not_an_instances(kcl: kf.KCLayout, layers: Layers) -> None:
    c1 = kcl.kcell()
    _ = c1 << _straight(kcl, layers)
    assert c1.insts != "not an instances object"


def test_vinstances_iter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    _ = c << _straight(kcl, layers)
    insts = list(c.insts)
    assert len(insts) == 1


def test_vinstances_getitem_by_int(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    _ = c << _straight(kcl, layers)
    assert isinstance(c.insts[0], kf.VInstance)


def test_vinstances_getitem_by_name(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    ref = c << _straight(kcl, layers)
    ref.name = "vname"
    assert c.insts["vname"] is ref


def test_vinstances_getitem_missing_raises(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    _ = c << _straight(kcl, layers)
    with pytest.raises(KeyError, match="No instance found"):
        c.insts["missing"]


def test_vinstances_contains_false(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    _ = c << _straight(kcl, layers)
    assert "no_such_name" not in c.insts


def test_vinstances_delitem_by_int(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    _ = c << _straight(kcl, layers)
    _ = c << _straight(kcl, layers)
    del c.insts[0]
    assert len(c.insts) == 1


def test_vinstances_delitem_by_vinstance(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    ref = c << _straight(kcl, layers)
    _ = c << _straight(kcl, layers)
    del c.insts[ref]
    assert len(c.insts) == 1


def test_vinstances_clear(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    _ = c << _straight(kcl, layers)
    _ = c << _straight(kcl, layers)
    c.insts.clear()
    assert len(c.insts) == 0


def test_vinstances_remove(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    ref = c << _straight(kcl, layers)
    c.insts.remove(ref)
    assert len(c.insts) == 0


def test_vinstances_dup_copy(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    _ = c << _straight(kcl, layers)
    dup = c.insts.dup()
    assert len(dup) == 1
    copy = c.insts.copy()
    assert len(copy) == 1

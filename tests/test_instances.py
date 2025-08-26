import kfactory as kf
from tests.conftest import Layers


def test_vinstances_contains(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell(name="test_vinstances_contains")
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    assert ref in c.insts


def test_instances_contains(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell(name="test_instances_contains")
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    assert ref in c.insts


def test_dinstances_contains(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.dkcell(name="test_dinstances_contains")
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    assert ref in c.insts


def test_vinstances_contains_int(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell(name="test_vinstances_contains_int")
    _ = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    _ = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    assert 0 in c.insts
    assert 1 in c.insts


def test_instances_contains_int(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell(name="test_instances_contains_int")
    _ = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    _ = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    assert 0 in c.insts
    assert 1 in c.insts


def test_dinstances_contains_int(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.dkcell(name="test_dinstances_contains_int")
    _ = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    _ = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    assert 0 in c.insts
    assert 1 in c.insts


def test_vinstances_contains_str(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell(name="test_vinstances_contains_str")
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    ref.name = "test_vinstances_contains_str_instance"
    assert ref.name is not None
    assert ref.name in c.insts


def test_instances_contains_str(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell(name="test_instances_contains_str")
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    ref.name = "test_instances_contains_str_instance"
    assert ref.name is not None
    assert ref.name in c.insts


def test_dinstances_contains_str(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.dkcell(name="test_dinstances_contains_str")
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    ref.name = "test_dinstances_contains_str_instance"
    assert ref.name is not None
    assert ref.name in c.insts


def test_to_itype(kcl: kf.KCLayout) -> None:
    cell = kcl.kcell()
    dkcell = kcl.dkcell()
    dkcell.shapes(0).insert(kf.kdb.DBox(-5, -5, 5, 5))
    _ = cell << dkcell
    ref = cell.insts[0]
    assert isinstance(ref, kf.Instance)
    assert ref.bbox() == kf.kdb.Box(-5000, -5000, 5000, 5000)
    dref = ref.to_dtype()
    assert isinstance(dref, kf.DInstance)
    assert dref.bbox() == kf.kdb.DBox(-5, -5, 5, 5)


def test_to_dtype(kcl: kf.KCLayout) -> None:
    cell = kcl.dkcell()
    dkcell = kcl.kcell()
    dkcell.shapes(0).insert(kf.kdb.DBox(-5, -5, 5, 5))
    _ = cell << dkcell
    dref = cell.insts[0]
    assert isinstance(dref, kf.DInstance)
    assert dref.bbox() == kf.kdb.DBox(-5, -5, 5, 5)
    ref = dref.to_itype()
    assert ref.bbox() == kf.kdb.Box(-5000, -5000, 5000, 5000)
    assert isinstance(ref, kf.Instance)

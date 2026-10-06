from collections.abc import Callable
from functools import partial
from pathlib import Path

import pytest

import kfactory as kf
from kfactory.exceptions import DuplicateCellNameError
from tests.conftest import Layers


def test_virtual_cell(kcl: kf.KCLayout) -> None:
    c = kcl.vkcell("TEST_VIRTUAL_CELL")
    c.shapes(kcl.find_layer(1, 0)).insert(
        kf.kdb.DPolygon([kf.kdb.DPoint(0, 0), kf.kdb.DPoint(1, 0), kf.kdb.DPoint(0, 1)])
    )


def test_virtual_inst(straight: kf.KCell, kcl: kf.KCLayout) -> None:
    c = kcl.vkcell()
    c << straight


def test_virtual_cell_insert(
    layers: Layers, straight: kf.KCell, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout
) -> None:
    c = kcl.kcell()

    vc = kcl.vkcell(name="test_virtual_insert")

    e_bend = kf.factories.virtual.euler.virtual_bend_euler_factory(kcl=kcl)(
        width=0.5,
        radius=10,
        layer=layers.WG,
        angle=25,
        enclosure=wg_enc,
    )
    e1 = vc << e_bend
    e2 = vc << e_bend
    e3 = vc << e_bend
    e4 = vc << e_bend
    _s = kf.cells.virtual.straight.virtual_straight(
        width=0.5, length=10, layer=layers.WG, enclosure=wg_enc
    )
    s = vc << _s

    s.connect("o1", e1, "o2")

    e2.connect("o1", s, "o2")
    e3.connect("o1", e2, "o2")
    e4.connect("o2", e3, "o2")
    s2 = vc << straight
    s2.connect("o1", e4, "o1")

    vi = kf.VInstance(vc)
    vi.insert_into(c)


def test_all_angle_route(
    layers: Layers, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout
) -> None:
    bb = [kf.kdb.DPoint(x, y) for x, y in [(0, 0), (500, 0), (250, 200), (500, 250)]]
    vc = kcl.vkcell(name="test_all_angle")
    kf.routing.aa.optical.route(
        vc,
        width=5,
        backbone=bb,
        straight_factory=partial(
            kf.factories.virtual.straight.virtual_straight_factory(kcl=kcl),
            layer=layers.WG,
            enclosure=wg_enc,
        ),
        bend_factory=partial(
            kf.factories.virtual.euler.virtual_bend_euler_factory(kcl=kcl),
            width=5,
            radius=20,
            layer=layers.WG,
            enclosure=wg_enc,
        ),
    )
    file = Path("test_all_angle.oas")
    vc.write(file)
    assert file.is_file()
    file.unlink()


def test_virtual_connect(
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
) -> None:
    e_bend = kf.factories.virtual.euler.virtual_bend_euler_factory(kcl=kcl)(
        width=0.5,
        radius=10,
        layer=layers.WG,
        angle=25,
        enclosure=wg_enc,
    )

    wg = straight_factory_dbu(
        width=500, enclosure=wg_enc, layer=layers.WG, length=10_000
    )

    c = kcl.kcell()

    wg1 = c << wg
    wg2 = c << wg

    b1 = c.create_vinst(e_bend)

    b1.connect("o1", wg1, "o2")
    wg2.connect("o1", b1, "o2")


def test_vinst_copy() -> None:
    kcl = kf.KCLayout("VINST_DUP")
    c = kcl.kcell()
    vk = kcl.vkcell()
    vk.name = "vinst_test"
    c.create_vinst(vk)

    c2 = c.dup()

    c.insert_vinsts()

    assert len(c2.vinsts) == 1
    assert c2.vinsts[0].cell is vk


@pytest.mark.parametrize(("first_angle", "second_angle"), [(0, 0), (17, 17), (17, 23)])
def test_virtual_name_collision(
    kcl: kf.KCLayout, first_angle: float, second_angle: float
) -> None:
    layer = kcl.layer(1, 0)
    a = kf.VKCell(kcl=kcl, name="dupe")
    a.shapes(layer).insert(kf.kdb.DBox(0, 0, 10, 10))
    b = kf.VKCell(kcl=kcl, name="dupe")
    b.shapes(layer).insert(kf.kdb.DBox(0, 0, 30, 1))
    top = kcl.kcell("top")
    top.create_vinst(a).trans = kf.kdb.DCplxTrans(1, first_angle, False, 0, 0)
    top.create_vinst(b).trans = kf.kdb.DCplxTrans(1, second_angle, False, 0, 0)

    with pytest.raises(DuplicateCellNameError, match="different cell"):
        top.insert_vinsts()

    assert len(top.insts) == 1


@pytest.mark.parametrize(("virtual", "angle"), [(True, 0), (True, 17), (False, 17)])
def test_vinstance_existing_real_cell(
    kcl: kf.KCLayout, angle: float, *, virtual: bool
) -> None:
    source = kcl.vkcell("source") if virtual else kcl.kcell("source")
    trans = kf.kdb.DCplxTrans(1, angle, False, 0, 0)
    name = "source" if angle == 0 else f"source_{trans.hash():x}"
    existing = kcl.kcell(name)
    layer = kcl.layer(1, 0)
    existing.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))
    top = kcl.kcell("top")

    with pytest.raises(DuplicateCellNameError, match="same source cell and transform"):
        kf.VInstance(source, trans).insert_into(top)

    assert len(top.insts) == 0
    assert kf.kdb.Region(existing.shapes(layer)).area() == 1_000_000


@pytest.mark.parametrize("virtual", [True, False])
def test_vinstance_reuse_and_transforms(kcl: kf.KCLayout, *, virtual: bool) -> None:
    source = kcl.vkcell("source") if virtual else kcl.kcell("source")
    layer = kcl.layer(1, 0)
    if isinstance(source, kf.VKCell):
        source.shapes(layer).insert(kf.kdb.DBox(0, 0, 10, 10))
        wrapper = kf.VKCell(base=source.base)
    else:
        source.shapes(layer).insert(kf.kdb.Box(0, 0, 10000, 10000))
        wrapper = kf.KCell(base=source.base)
    top = kcl.kcell("top")
    indexes = []
    for angle in (0, 17, 23):
        trans = kf.kdb.DCplxTrans(1, angle, False, 0, 0)
        first = kf.VInstance(source, trans).insert_into(top)
        # Reuse also works across separate calls, parents, and wrappers.
        other_top = kcl.kcell(f"top_{angle}")
        second = kf.VInstance(wrapper, trans).insert_into(other_top)
        assert first.cell.cell_index() == second.cell.cell_index()
        assert kf.kdb.Region(first.cell.shapes(layer)).area() > 0
        indexes.append(first.cell.cell_index())
    assert len(set(indexes)) == 3


def test_virtual_duplicate_has_distinct_identity(kcl: kf.KCLayout) -> None:
    source = kcl.vkcell("source")
    duplicate = source.dup(new_name="source")
    top = kcl.kcell("top")
    kf.VInstance(source).insert_into(top)
    with pytest.raises(DuplicateCellNameError, match="different cell"):
        kf.VInstance(duplicate).insert_into(top)


def test_virtual_names_are_layout_local_and_cleared(kcl: kf.KCLayout) -> None:
    for layout in (kcl, kf.KCLayout(f"{kcl.name}_other"), kcl):
        source = layout.vkcell("source")
        top = layout.kcell("top")
        kf.VInstance(source).insert_into(top)
        assert len(top.insts) == 1
        layout.clear()


def test_virtual_recreate_deleted_materialization(kcl: kf.KCLayout) -> None:
    source = kcl.vkcell("source")
    top = kcl.kcell("top")
    inst = kf.VInstance(source).insert_into(top)
    kcl.delete_cell(inst.cell)
    inst = kf.VInstance(source).insert_into(top)
    assert not inst.cell.kdb_cell._destroyed()
    assert inst.cell.name == "source"


@pytest.mark.parametrize("virtual", [True, False])
def test_vinstance_transform_hash_collision(
    kcl: kf.KCLayout, monkeypatch: pytest.MonkeyPatch, *, virtual: bool
) -> None:
    monkeypatch.setattr(kf.kdb.DCplxTrans, "hash", lambda self: 1)
    source = kcl.vkcell("source") if virtual else kcl.kcell("source")
    top = kcl.kcell("top")
    kf.VInstance(source, kf.kdb.DCplxTrans(1, 17, False, 0, 0)).insert_into(top)
    with pytest.raises(DuplicateCellNameError, match="same source cell and transform"):
        kf.VInstance(source, kf.kdb.DCplxTrans(1, 23, False, 0, 0)).insert_into(top)
    assert len(top.insts) == 1


def test_virtual_collision_does_not_reserve_name(kcl: kf.KCLayout) -> None:
    existing = kcl.kcell("source")
    top = kcl.kcell("top")
    with pytest.raises(DuplicateCellNameError):
        kf.VInstance(kcl.vkcell("source")).insert_into(top)
    kcl.delete_cell(existing)
    kf.VInstance(kcl.vkcell("source")).insert_into(top)
    assert len(top.insts) == 1


def test_virtual_identity_survives_layout_clear(kcl: kf.KCLayout) -> None:
    original = kcl.vkcell("source")
    kf.VInstance(original).insert_into(kcl.kcell("top"))
    kcl.clear()
    replacement = kcl.vkcell("source")
    top = kcl.kcell("top")
    kf.VInstance(replacement).insert_into(top)
    with pytest.raises(DuplicateCellNameError, match="different cell"):
        kf.VInstance(original).insert_into(top)


def test_virtual_identity_includes_source_layout(kcl: kf.KCLayout) -> None:
    other = kf.KCLayout(f"{kcl.name}_other")
    source = kcl.vkcell("source")
    foreign = other.vkcell("source")
    top = kcl.kcell("top")
    kf.VInstance(source).insert_into(top)
    with pytest.raises(DuplicateCellNameError, match="different cell"):
        kf.VInstance(foreign).insert_into(top)


def test_virtual_identity_distinct_from_real_index(kcl: kf.KCLayout) -> None:
    real = kcl.kcell("source")
    trans = kf.kdb.DCplxTrans(1, 17, False, 0, 0)
    virtual = kcl.vkcell(f"source_{trans.hash():x}")
    top = kcl.kcell("top")
    kf.VInstance(real, trans).insert_into(top)
    with pytest.raises(DuplicateCellNameError, match="same source cell and transform"):
        kf.VInstance(virtual).insert_into(top)

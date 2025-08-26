from typing import TypeAlias

import pytest

import kfactory as kf


def _instances_equal(instance1: kf.Instance, instance2: kf.Instance) -> bool:
    return (
        instance1.instance.cell_index == instance2.instance.cell_index
        and instance1.instance.dcplx_trans == instance2.instance.dcplx_trans
    )


_InstanceGroupTuple: TypeAlias = tuple[
    kf.InstanceGroup, kf.InstanceGroup, kf.InstanceGroup
]


def _instance_group_equal(
    instance1: kf.InstanceGroup, instance2: kf.InstanceGroup
) -> bool:
    for i1, i2 in zip(instance1.insts, instance2.insts, strict=False):
        if not _instances_equal(i1, i2):
            return False
    return True


@pytest.fixture
def instance_groups() -> _InstanceGroupTuple:
    layer = kf.kdb.LayerInfo(1, 0)
    cell = kf.KCell()
    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))

    parent_cell = kf.KCell()

    instance_group1 = kf.InstanceGroup(insts=[parent_cell << cell, parent_cell << cell])
    instance_group2 = kf.InstanceGroup(insts=[parent_cell << cell, parent_cell << cell])
    instance_group3 = kf.InstanceGroup(insts=[parent_cell << cell, parent_cell << cell])

    return instance_group1, instance_group2, instance_group3


def test_mirror_x(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, instance2, instance3 = instance_groups

    instance1.mirror_x(1000)
    instance2.dmirror_x(1)
    instance3.mirror_x(1000)

    assert _instance_group_equal(instance1, instance2)
    assert _instance_group_equal(instance1, instance3)


def test_mirror_y(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, instance2, instance3 = instance_groups

    instance1.mirror_y(1000)
    instance2.dmirror_y(1)
    instance3.mirror_y(1000)

    assert _instance_group_equal(instance1, instance2)
    assert _instance_group_equal(instance1, instance3)


def test_mirror(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, instance2, instance3 = instance_groups

    p1 = (2000, 0)
    p2 = (0, 2000)

    instance1.mirror(p1, p2)
    instance2.dmirror((0, 2), (2, 0))
    instance3.imirror(p1, p2)

    assert _instance_group_equal(instance1, instance2)
    assert _instance_group_equal(instance1, instance3)


def test_move(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, instance2, instance3 = instance_groups

    origin = (0, 0)
    destination = (2000, 2000)

    instance1.move(origin, destination)
    instance2.dmove((0, 0), (2, 2))
    instance3.imove(origin, destination)

    assert _instance_group_equal(instance1, instance2)
    assert _instance_group_equal(instance1, instance3)


def test_movex(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, instance2, instance3 = instance_groups

    origin = 0
    destination = 2000

    instance1.movex(origin, destination)
    instance2.dmovex(0, 2)
    instance3.imovex(origin, destination)

    assert _instance_group_equal(instance1, instance2)
    assert _instance_group_equal(instance1, instance3)


def test_movey(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, instance2, instance3 = instance_groups

    origin = 0
    destination = 2000

    instance1.movey(origin, destination)
    instance2.dmovey(0, 2)
    instance3.imovey(origin, destination)

    assert _instance_group_equal(instance1, instance2)
    assert _instance_group_equal(instance1, instance3)


def test_rotate(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, instance2, instance3 = instance_groups

    instance1.rotate(1)
    instance2.drotate(90)
    instance3.irotate(1)

    assert _instance_group_equal(instance1, instance2)
    assert _instance_group_equal(instance1, instance3)


def test_instance_group_bounding_box(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, _, instance3 = instance_groups

    assert instance1.ibbox() == instance3.ibbox()

    instance3.insts = []

    assert instance1.dbbox() == kf.kdb.DBox(0, 0, 1, 1)
    assert instance1.ibbox() == kf.kdb.DBox(0, 0, 1000, 1000)
    assert instance3.dbbox() == kf.kdb.DBox()
    assert instance3.ibbox() == kf.kdb.Box()


def test_instance_group_attributes(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, instance2, _ = instance_groups

    instance1.movex(1000).rotate(1).mirror_x(1000)
    instance2.dmovex(1).drotate(90).dmirror_x(1)

    assert instance1.x == instance2.x
    assert instance1.y == instance2.y
    assert instance1.xmin == instance2.xmin
    assert instance1.ymin == instance2.ymin
    assert instance1.xmax == instance2.xmax
    assert instance1.ymax == instance2.ymax
    assert instance1.xsize == instance2.xsize
    assert instance1.ysize == instance2.ysize
    assert instance1.center == instance2.center


def test_to_itype(kcl: kf.KCLayout) -> None:
    cell = kcl.kcell()
    dkcell = kcl.dkcell()
    dkcell.shapes(0).insert(kf.kdb.DBox(-5, -5, 5, 5))
    ref = cell << dkcell
    ref2 = cell << dkcell
    ref2.move((0, 0), (1000, 1000))
    instance_group = kf.InstanceGroup(insts=[ref, ref2])
    assert instance_group.bbox() == kf.kdb.Box(-5000, -5000, 6000, 6000)
    dinstance_group = instance_group.to_dtype()
    assert dinstance_group.bbox() == kf.kdb.DBox(-5, -5, 6, 6)
    assert isinstance(dinstance_group, kf.DInstanceGroup)


def test_to_dtype(kcl: kf.KCLayout) -> None:
    cell = kcl.kcell()
    dkcell = kcl.dkcell()
    cell.shapes(0).insert(kf.kdb.DBox(-5, -5, 5, 5))
    ref = dkcell << cell
    ref2 = dkcell << cell
    ref2.move((0, 0), (1, 1))
    instance_group = kf.DInstanceGroup(insts=[ref, ref2])
    assert instance_group.bbox() == kf.kdb.DBox(-5, -5, 6, 6)
    dinstance_group = instance_group.to_itype()
    assert dinstance_group.bbox() == kf.kdb.Box(-5000, -5000, 6000, 6000)
    assert isinstance(dinstance_group, kf.InstanceGroup)


def test_instance_group_kcl(kcl: kf.KCLayout) -> None:
    instance_group = kf.InstanceGroup()
    with pytest.raises(ValueError):
        _ = instance_group.kcl

    with pytest.raises(ValueError):
        instance_group.kcl = kcl


def test_instnace_group_iter(
    instance_groups: _InstanceGroupTuple,
) -> None:
    instance1, *_ = instance_groups
    for inst in instance1:
        assert isinstance(inst, kf.Instance)

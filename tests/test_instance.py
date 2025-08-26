from typing import Any, TypeAlias

import klayout.db as kdb
import pytest

import kfactory as kf
from kfactory import exceptions
from tests.conftest import Layers


def test_instance_xsize(layers: Layers) -> None:
    c = kf.KCell()
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    assert ref.xsize


def test_instance_center(layers: Layers) -> None:
    c = kf.KCell()
    ref1 = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)
    ref2 = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)

    ref1.center = ref2.center
    ref2.center = (ref1.center[0], ref2.center[1] + 1000)
    ref2.dmove((0, 10))
    assert ref2.center == (ref1.center[0], ref1.center[1] + 11_000)


def test_instance_d_move(layers: Layers) -> None:
    c = kf.KCell()
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)

    ref.dmovex(10)
    ref.dmovex(10.0)

    ref.dmovey(10)
    ref.dmovey(10.0)
    ref.dmovex(10).movey(10)
    ref.drotate(45).movey(10)

    ref.dxmin = 0
    ref.dxmax = 0
    ref.dymin = 0
    ref.dymax = 0

    ref.dmirror_y(0)
    ref.dmirror_x(0)


def test_instance_array(layers: Layers) -> None:
    c = kf.KCell()
    ref = c.create_inst(
        kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG),
        na=4,
        nb=6,
        a=kf.kdb.Vector(3000, 0),
        b=kf.kdb.Vector(0, 2000),
    )

    ref.dmovex(10)
    ref.dmovex(10.0)

    ref.dmovey(10)
    ref.dmovey(10.0)
    ref.dmovex(10).movey(10)
    ref.drotate(45).movey(10)

    ref.dxmin = 0
    ref.dxmax = 0
    ref.dymin = 0
    ref.dymax = 0

    ref.dmirror_y(0)
    ref.dmirror_x(0)

    for x in range(4):
        for y in range(6):
            disp_o1 = (
                ref.ports["o1", x, y].dcplx_trans.disp
                - (
                    kf.kdb.DCplxTrans(
                        trans=kf.kdb.InstElement(
                            ref.instance, x, y
                        ).specific_cplx_trans(),
                        dbu=c.kcl.dbu,
                    )
                    * ref.cell.ports["o1"].dcplx_trans
                ).disp
            )
            disp_o2 = (
                ref.ports["o2", x, y].dcplx_trans.disp
                - (
                    kf.kdb.DCplxTrans(
                        trans=kf.kdb.InstElement(
                            ref.instance, x, y
                        ).specific_cplx_trans(),
                        dbu=c.kcl.dbu,
                    )
                    * ref.cell.ports["o2"].dcplx_trans
                ).disp
            )
            assert abs(disp_o1.x) < 0.0005
            assert abs(disp_o1.y) < 0.0005
            assert abs(disp_o2.x) < 0.0005
            assert abs(disp_o2.y) < 0.0005


def test_instance_mirror(layers: Layers) -> None:
    """Test arbitrary mirror."""
    c = kf.KCell()
    b = kf.cells.euler.bend_euler(width=1, radius=10, layer=layers.WG)

    c << b
    b2 = c << b
    disp = kdb.Trans(5000, 5000)
    mp1 = kf.kdb.Point(50000, 25000)
    mp2 = -mp1

    p1 = disp * mp1
    p2 = disp * mp2

    b2.mirror((p1.x, p1.y), (p2.x, p2.y))

    c.shapes(c.kcl.find_layer(layers.WG)).insert(
        kf.kdb.Edge(mp1, mp2).transformed(disp)
    )


def test_dmirror(layers: Layers) -> None:
    """Test arbitrary mirror."""
    c = kf.KCell()
    b = kf.cells.euler.bend_euler(width=1, radius=10, layer=layers.WG)

    c << b
    b2 = c << b
    disp = kdb.Trans(5000, 5000).to_dtype(c.kcl.dbu)
    mp1 = c.kcl.to_um(kf.kdb.Point(50000, 25000))
    mp2 = -mp1

    p1 = disp * mp1
    p2 = disp * mp2

    b2.dmirror((p1.x, p1.y), (p2.x, p2.y))

    c.shapes(c.kcl.find_layer(layers.WG)).insert(
        kf.kdb.DEdge(mp1, mp2).transformed(disp)
    )


def _instances_equal(
    instance1: kf.instance.ProtoTInstance[Any],
    instance2: kf.instance.ProtoTInstance[Any],
) -> bool:
    return (
        instance1.instance.cell_index == instance2.instance.cell_index
        and instance1.instance.dcplx_trans == instance2.instance.dcplx_trans
    )


_DBUInstanceTuple: TypeAlias = tuple[
    kf.instance.Instance, kf.instance.Instance, kf.instance.Instance
]


_UMInstanceTuple: TypeAlias = tuple[
    kf.instance.DInstance, kf.instance.DInstance, kf.instance.DInstance
]


@pytest.fixture
def dbu_instance_tuple() -> _DBUInstanceTuple:
    cell = kf.kcell.KCell()
    layer = kf.kdb.LayerInfo(1, 0)
    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))
    parent_cell = kf.kcell.KCell()
    return (
        parent_cell << cell,
        parent_cell << cell,
        parent_cell << cell,
    )


@pytest.fixture
def um_instance_tuple() -> _UMInstanceTuple:
    cell = kf.kcell.DKCell()
    layer = kf.kdb.LayerInfo(1, 0)
    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))
    parent_cell = kf.kcell.DKCell()
    return (
        parent_cell << cell,
        parent_cell << cell,
        parent_cell << cell,
    )


def test_mirror_x(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.mirror_x(1000)
    instance2.dmirror_x(1)
    instance3.imirror_x(1000)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror_y(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.mirror_y(1000)
    instance2.dmirror_y(1)
    instance3.imirror_y(1000)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    p1 = (2000, 0)
    p2 = (0, 2000)

    instance1.mirror(p1, p2)
    instance2.dmirror((0, 2), (2, 0))
    instance3.imirror(p1, p2)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_move(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    origin = (0, 0)
    destination = (2000, 2000)

    instance1.move(origin, destination)
    instance2.dmove((0, 0), (2, 2))
    instance3.imove(origin, destination)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_move_no_origin(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    destination = (2000, 2000)

    instance1.move(destination)
    instance2.dmove((2.0, 2.0))
    instance3.imove(destination)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_movex(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    origin = 0
    destination = 2000

    instance1.movex(origin, destination)
    instance2.dmovex(0, 2)
    instance3.imovex(origin, destination)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_movex_no_origin(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    destination = 2000

    instance1.movex(destination)
    instance2.dmovex(2)
    instance3.imovex(destination)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_movey(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    origin = 0
    destination = 2000

    instance1.movey(origin, destination)
    instance2.dmovey(0, 2)
    instance3.imovey(origin, destination)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_movey_no_origin(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    destination = 2000

    instance1.movey(destination)
    instance2.dmovey(2)
    instance3.imovey(destination)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_rotate(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.rotate(1)
    instance2.drotate(90)
    instance3.irotate(1)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_rotate_um(um_instance_tuple: _UMInstanceTuple) -> None:
    instance1, instance2, instance3 = um_instance_tuple

    instance1.rotate(90)
    instance2.drotate(90)
    instance3.irotate(1)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror_x_um(um_instance_tuple: _UMInstanceTuple) -> None:
    instance1, instance2, instance3 = um_instance_tuple

    instance1.mirror_x(1)
    instance2.dmirror_x(1)
    instance3.imirror_x(1000)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror_y_um(um_instance_tuple: _UMInstanceTuple) -> None:
    instance1, instance2, instance3 = um_instance_tuple

    instance1.mirror_y(1)
    instance2.dmirror_y(1)
    instance3.imirror_y(1000)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror_um(um_instance_tuple: _UMInstanceTuple) -> None:
    instance1, instance2, instance3 = um_instance_tuple

    instance1.mirror((0, 2), (2, 0))
    instance2.dmirror((0, 2), (2, 0))
    instance3.imirror((0, 2000), (2000, 0))

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_x_um(um_instance_tuple: _UMInstanceTuple) -> None:
    instance1, instance2, instance3 = um_instance_tuple

    instance1.x = 1
    instance2.dx = 1
    instance3.ix = 1000

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_instance_attributes(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, _ = dbu_instance_tuple

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


def test_dinstance_attributes(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, _ = dbu_instance_tuple

    instance1.imovex(1000).irotate(1).imirror_x(1000)
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


def test_x(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.x = 1000
    instance2.dx = 1
    instance3.ix = 1000

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_y(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.y = 1000
    instance2.dy = 1
    instance3.iy = 1000

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_xmin(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.xmin = 1000
    instance2.dxmin = 1
    instance3.ixmin = 1000

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_ymin(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.ymin = 1000
    instance2.dymin = 1
    instance3.iymin = 1000

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_xmax(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.xmax = 1000
    instance2.dxmax = 1
    instance3.ixmax = 1000

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_ymax(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.ymax = 1000
    instance2.dymax = 1
    instance3.iymax = 1000

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_xsize(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.xsize = 1000
    instance2.dxsize = 1
    instance3.ixsize = 1000

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_ysize(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.ysize = 1000
    instance2.dysize = 1
    instance3.iysize = 1000

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_center(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.center = (1000, 1000)
    instance2.dcenter = (1, 1)
    instance3.icenter = (1000, 1000)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_vinstance_connect_by_port(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    straight_factory = kf.factories.straight.straight_dbu_factory(kcl)
    straight = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    straight2 = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    ref = c << straight
    ref2 = c << straight2
    ref2.move((50, 10))
    ref.connect("o1", ref2.ports["o2"])
    assert c.bbox() == kdb.DBox(50, 7.5, 70, 12.5)


def test_vinstance_connect_by_port_use_angle_false(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    c = kcl.vkcell()
    straight_factory = kf.factories.straight.straight_dbu_factory(kcl)
    straight = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    straight2 = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    ref = c << straight
    ref2 = c << straight2
    ref2.move((10, 10)).rotate(90)
    ref.connect("o1", ref2.ports["o2"], use_angle=False)
    assert c.bbox() == kdb.DBox(-12.5, 10, 0, 22.5)


def test_vinstance_connect_by_port_use_mirror_false(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    c = kcl.vkcell()
    straight_factory = kf.factories.straight.straight_dbu_factory(kcl)
    straight = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    straight2 = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    ref = c << straight
    ref2 = c << straight2
    ref2.move((10, 10)).rotate(270)
    ref.connect("o1", ref2.ports["o2"], use_mirror=False)
    assert c.bbox() == kdb.DBox(7.5, -30, 12.5, -10)


def test_vinstance_connect_by_port_use_mirror_use_angle_false(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    c = kcl.vkcell()
    straight_factory = kf.factories.straight.straight_dbu_factory(kcl)
    straight = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    straight2 = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    ref = c << straight
    ref2 = c << straight2
    ref2.move((10, 10)).rotate(270)
    ref.connect("o1", ref2.ports["o2"], use_mirror=False, use_angle=False)
    assert c.bbox() == kdb.DBox(7.5, -22.5, 20, -10)


def test_vinstance_connect_by_str(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    straight_factory = kf.factories.straight.straight_dbu_factory(kcl)
    straight = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    straight2 = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(20), layer=layers.WG
    )
    ref = c << straight
    ref2 = c << straight2
    ref2.move((50, 10))
    ref.connect(ref.ports["o1"], ref2.ports["o2"])
    assert c.bbox() == kdb.DBox(50, 7.5, 80, 12.5)


def test_vinstance_errors(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    straight_factory = kf.factories.straight.straight_dbu_factory(kcl)
    straight = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(10), layer=layers.WG
    )
    straight2 = straight_factory(
        width=kcl.to_dbu(10), length=kcl.to_dbu(20), layer=layers.WG
    )
    straight3 = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(20), layer=layers.FILL1
    )
    straight4 = straight_factory(
        width=kcl.to_dbu(5), length=kcl.to_dbu(20), layer=layers.WG
    ).dup()
    straight4.ports["o1"].port_type = "non-optical"
    ref = c << straight
    ref2 = c << straight2
    ref3 = c << straight3
    ref4 = c << straight4
    ref5 = c << straight.dup()
    with pytest.raises(exceptions.PortWidthMismatchError):
        ref.connect("o1", ref2.ports["o2"])
    with pytest.raises(exceptions.PortLayerMismatchError):
        ref.connect("o1", ref3.ports["o2"])
    with pytest.raises(exceptions.PortTypeMismatchError):
        ref.connect("o1", ref4.ports["o1"])
    with pytest.raises(ValueError):
        ref.connect("o1", ref5)  # type: ignore[call-overload]


def test_mirror_y_default_arg(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.mirror_y()
    instance2.dmirror_y()
    instance3.imirror_y()

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror_x_default_arg(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.mirror_x()
    instance2.dmirror_x()
    instance3.imirror_x()

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror_default_arg(dbu_instance_tuple: _DBUInstanceTuple) -> None:
    instance1, instance2, instance3 = dbu_instance_tuple

    instance1.mirror()
    instance2.dmirror()
    instance3.imirror()

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror_x_equal() -> None:
    cell = kf.kcell.DKCell()
    layer = kf.kdb.LayerInfo(1, 0)
    cell.shapes(layer).insert(kf.kdb.DBox(-5, -5, 5, 5))
    parent_cell = kf.kcell.DKCell()
    _ = parent_cell << cell
    ref2 = parent_cell << cell
    ref3 = parent_cell << cell

    ref2.dmirror_x()
    ref3.imirror_x()

    assert parent_cell.bbox() == kf.kdb.DBox(-5, -5, 5, 5)


def test_mirror_y_equal() -> None:
    cell = kf.kcell.DKCell()
    layer = kf.kdb.LayerInfo(1, 0)
    cell.shapes(layer).insert(kf.kdb.DBox(-5, -5, 5, 5))
    parent_cell = kf.kcell.DKCell()
    _ = parent_cell << cell
    ref2 = parent_cell << cell
    ref3 = parent_cell << cell

    ref2.dmirror_y()
    ref3.imirror_y()

    assert parent_cell.bbox() == kf.kdb.DBox(-5, -5, 5, 5)


def test_to_itype(kcl: kf.KCLayout) -> None:
    cell = kcl.kcell()
    dkcell = kcl.dkcell()
    dkcell.shapes(0).insert(kf.kdb.DBox(-5, -5, 5, 5))
    ref = cell << dkcell
    assert isinstance(ref, kf.Instance)
    assert ref.bbox() == kf.kdb.Box(-5000, -5000, 5000, 5000)
    dref = ref.to_dtype()
    assert isinstance(dref, kf.DInstance)
    assert dref.bbox() == kf.kdb.DBox(-5, -5, 5, 5)


def test_to_dtype(kcl: kf.KCLayout) -> None:
    cell = kcl.dkcell()
    dkcell = kcl.kcell()
    dkcell.shapes(0).insert(kf.kdb.DBox(-5, -5, 5, 5))
    dref = cell << dkcell
    assert isinstance(dref, kf.DInstance)
    assert dref.bbox() == kf.kdb.DBox(-5, -5, 5, 5)
    ref = dref.to_itype()
    assert ref.bbox() == kf.kdb.Box(-5000, -5000, 5000, 5000)
    assert isinstance(ref, kf.Instance)

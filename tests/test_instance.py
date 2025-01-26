import klayout.db as kdb
import pytest
from conftest import Layers

import kfactory as kf


def test_instance_xsize(LAYER: Layers) -> None:
    c = kf.KCell()
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)
    assert ref.xsize


def test_instance_center(LAYER: Layers) -> None:
    c = kf.KCell()
    ref1 = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)
    ref2 = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)

    ref1.center = ref2.center
    ref2.center = (ref1.center[0], ref2.center[1] + 1000)
    ref2.dmove((0, 10))
    assert ref2.center == (ref1.center[0], ref1.center[1] + 11_000)


def test_instance_d_move(LAYER: Layers) -> None:
    c = kf.KCell()
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)

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


def test_instance_mirror(LAYER: Layers) -> None:
    """Test arbitrary mirror."""
    c = kf.KCell()
    b = kf.cells.euler.bend_euler(width=1, radius=10, layer=LAYER.WG)

    c << b
    b2 = c << b
    disp = kdb.Trans(5000, 5000)
    # mp1 = kf.kdb.Point(-10000, 10000)
    mp1 = kf.kdb.Point(50000, 25000)
    mp2 = -mp1

    p1 = disp * mp1
    p2 = disp * mp2

    b2.mirror((p1.x, p1.y), (p2.x, p2.y))

    c.shapes(c.kcl.find_layer(LAYER.WG)).insert(kf.kdb.Edge(mp1, mp2).transformed(disp))


def test_dmirror(LAYER: Layers) -> None:
    """Test arbitrary mirror."""
    c = kf.KCell()
    b = kf.cells.euler.bend_euler(width=1, radius=10, layer=LAYER.WG)

    c << b
    b2 = c << b
    disp = kdb.Trans(5000, 5000).to_dtype(c.kcl.dbu)
    # mp1 = kf.kdb.Point(-10000, 10000)
    mp1 = c.kcl.to_um(kf.kdb.Point(50000, 25000))
    mp2 = -mp1

    p1 = disp * mp1
    p2 = disp * mp2

    b2.dmirror((p1.x, p1.y), (p2.x, p2.y))

    c.shapes(c.kcl.find_layer(LAYER.WG)).insert(
        kf.kdb.DEdge(mp1, mp2).transformed(disp)
    )


def _instances_equal(
    instance1: kf.kcell.Instance, instance2: kf.kcell.Instance
) -> bool:
    return (
        instance1.instance.cell_index == instance2.instance.cell_index
        and instance1.instance.dcplx_trans == instance2.instance.dcplx_trans
    )


def test_mirror_x() -> None:
    cell = kf.kcell.KCell()

    layer = kf.kdb.LayerInfo(1, 0)

    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))

    parent_cell = kf.kcell.KCell()

    instance1 = parent_cell << cell
    instance2 = parent_cell << cell
    instance3 = parent_cell << cell

    instance1.mirror_x(1000)
    instance2.dmirror_x(1)
    instance3.imirror_x(1000)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror_y() -> None:
    cell = kf.kcell.KCell()

    layer = kf.kdb.LayerInfo(1, 0)

    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))

    parent_cell = kf.kcell.KCell()

    instance1 = parent_cell << cell
    instance2 = parent_cell << cell
    instance3 = parent_cell << cell

    instance1.mirror_y(1000)
    instance2.dmirror_y(1)
    instance3.imirror_y(1000)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_mirror() -> None:
    cell = kf.kcell.KCell()

    layer = kf.kdb.LayerInfo(1, 0)

    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))

    parent_cell = kf.kcell.KCell()

    instance1 = parent_cell << cell
    instance2 = parent_cell << cell
    instance3 = parent_cell << cell

    p1 = (2000, 0)
    p2 = (0, 2000)

    instance1.mirror(p1, p2)
    instance2.dmirror((0, 2), (2, 0))
    instance3.imirror(p1, p2)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_move() -> None:
    cell = kf.kcell.KCell()

    layer = kf.kdb.LayerInfo(1, 0)

    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))

    parent_cell = kf.kcell.KCell()

    instance1 = parent_cell << cell
    instance2 = parent_cell << cell
    instance3 = parent_cell << cell

    origin = (0, 0)
    destination = (2000, 2000)

    instance1.move(origin, destination)
    instance2.dmove((0, 0), (2, 2))
    instance3.imove(origin, destination)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_movex() -> None:
    cell = kf.kcell.KCell()

    layer = kf.kdb.LayerInfo(1, 0)

    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))

    parent_cell = kf.kcell.KCell()

    instance1 = parent_cell << cell
    instance2 = parent_cell << cell
    instance3 = parent_cell << cell

    origin = 0
    destination = 2000

    instance1.movex(origin, destination)
    instance2.dmovex(0, 2)
    instance3.imovex(origin, destination)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_movey() -> None:
    cell = kf.kcell.KCell()

    layer = kf.kdb.LayerInfo(1, 0)

    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))

    parent_cell = kf.kcell.KCell()

    instance1 = parent_cell << cell
    instance2 = parent_cell << cell
    instance3 = parent_cell << cell

    origin = 0
    destination = 2000

    instance1.movey(origin, destination)
    instance2.dmovey(0, 2)
    instance3.imovey(origin, destination)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_rotate() -> None:
    cell = kf.kcell.KCell()

    layer = kf.kdb.LayerInfo(1, 0)

    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))

    parent_cell = kf.kcell.KCell()

    instance1 = parent_cell << cell
    instance2 = parent_cell << cell
    instance3 = parent_cell << cell

    instance1.rotate(1)
    instance2.drotate(90)
    instance3.irotate(1)

    assert _instances_equal(instance1, instance2)
    assert _instances_equal(instance1, instance3)


def test_instance_attributes() -> None:
    cell = kf.kcell.KCell()

    layer = kf.kdb.LayerInfo(1, 0)

    cell.shapes(layer).insert(kf.kdb.Box(0, 0, 1000, 1000))

    parent_cell = kf.kcell.KCell()

    instance1 = parent_cell << cell
    instance2 = parent_cell << cell

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


def test_dinstance_attributes() -> None:
    cell = kf.kcell.DKCell()

    layer = kf.kdb.LayerInfo(1, 0)

    cell.shapes(layer).insert(kf.kdb.DBox(0, 0, 1, 1))

    parent_cell = kf.kcell.DKCell()

    instance1 = parent_cell << cell
    instance2 = parent_cell << cell

    instance1.imovex(1000).irotate(1).imirror_x(1000)
    instance2.movex(1).rotate(90).mirror_x(1)

    assert instance1.x == instance2.x
    assert instance1.y == instance2.y
    assert instance1.xmin == instance2.xmin
    assert instance1.ymin == instance2.ymin
    assert instance1.xmax == instance2.xmax
    assert instance1.ymax == instance2.ymax
    assert instance1.xsize == instance2.xsize
    assert instance1.ysize == instance2.ysize
    assert instance1.center == instance2.center


if __name__ == "__main__":
    pytest.main([__file__])

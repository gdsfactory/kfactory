import kfactory as kf
import klayout.db as kdb
from conftest import Layers


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


def test_mirror(LAYER: Layers) -> None:
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

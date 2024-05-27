import kfactory as kf
import klayout.db as kdb


def test_instance_xsize(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)
    assert ref.xsize


def test_instance_center(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()
    ref1 = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)
    ref2 = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)

    ref1.center = ref2.center
    ref2.center = ref1.center + kdb.Point(0, 1000).to_v()
    ref2.dmove((0, 10))


def test_instance_d_move(LAYER: kf.LayerEnum) -> None:
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


def test_mirror(LAYER: kf.LayerEnum) -> None:
    """Test arbitrary mirror."""
    c = kf.KCell()
    b = kf.cells.euler.bend_euler(width=1, radius=10, layer=LAYER.WG)

    c << b
    b2 = c << b
    disp = kdb.Trans(5000, 5000)
    # mp1 = kf.kdb.Point(-10000, 10000)
    mp1 = kf.kdb.Point(50000, 25000)
    mp2 = -mp1

    b2.mirror(disp * mp1, disp * mp2)

    c.shapes(LAYER.WG).insert(kf.kdb.Edge(mp1, mp2).transformed(disp))
    c.show()


def test_dmirror(LAYER: kf.LayerEnum) -> None:
    """Test arbitrary mirror."""
    c = kf.KCell()
    b = kf.cells.euler.bend_euler(width=1, radius=10, layer=LAYER.WG)

    c << b
    b2 = c << b
    disp = kdb.Trans(5000, 5000).to_dtype(c.kcl.dbu)
    # mp1 = kf.kdb.Point(-10000, 10000)
    mp1 = kf.kdb.Point(50000, 25000).to_dtype(c.kcl.dbu)
    mp2 = -mp1

    b2.dmirror(disp * mp1, disp * mp2)

    c.shapes(LAYER.WG).insert(kf.kdb.DEdge(mp1, mp2).transformed(disp))
    c.show()

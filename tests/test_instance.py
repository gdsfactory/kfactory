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
    ref2.center = ref1.center + kdb.Point(0, 1000)
    ref2.d.move((0, 10))


def test_instance_d_move(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)

    ref.d.movex(10)
    ref.d.movex(10.0)

    ref.d.movey(10)
    ref.d.movey(10.0)

    ref.d.xmin = 0
    ref.d.xmax = 0
    ref.d.ymin = 0
    ref.d.ymax = 0

    ref.d.mirror_y(0)
    ref.d.mirror_x(0)

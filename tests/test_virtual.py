import kfactory as kf
import pytest

from collections.abc import Callable


def test_virtual_cell() -> None:
    c = kf.VKCell()
    c.shapes(kf.kcl.layer(1, 0)).insert(
        kf.kdb.DPolygon([kf.kdb.DPoint(0, 0), kf.kdb.DPoint(1, 0), kf.kdb.DPoint(0, 1)])
    )
    print(c.shapes(kf.kcl.layer(1, 0)))


def test_virtual_inst(straight: kf.KCell) -> None:
    c = kf.VKCell()
    inst = c << straight

    print(inst)


def test_virtual_cell_insert(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()

    vc = kf.VKCell()

    straight = kf.VKCell()
    straight.shapes(LAYER.WG).insert(
        kf.kdb.DPolygon(
            [
                kf.kdb.DPoint(x, y)
                for x, y in [(0, -0.25), (0, 0.25), (1.0005, 0.25), (1.0005, -0.25)]
            ]
        )
    )
    straight.create_port(
        name="o1",
        dcplx_trans=kf.kdb.DCplxTrans(1, 180, False, 0, 0),
        layer=LAYER.WG,
        dwidth=0.5,
    )
    straight.create_port(
        name="o2",
        dcplx_trans=kf.kdb.DCplxTrans(1, 0, False, 1.0005, 0),
        layer=LAYER.WG,
        dwidth=0.5,
    )

    # e_bend = kf.cells.euler.bend_euler(width=0.5, radius=10, layer=LAYER.WG, angle=30)
    # e1 = vc << e_bend
    # e2 = vc << e_bend
    s = vc << straight
    s.trans = kf.kdb.DCplxTrans(1, 30, False, 0, 0)

    for _ in range(10):
        _s = vc << straight
        _s.connect("o1", s, "o2")
        s = _s

    vi = kf.VInstance(vc)
    vi.insert_into(c)

    # vi = kf.VInstance(straight, kf.kdb.DCplxTrans(1, 30, False, 0, 0))

    c.show()

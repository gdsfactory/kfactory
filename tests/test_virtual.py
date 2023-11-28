import kfactory as kf
from functools import partial


def test_virtual_cell() -> None:
    c = kf.VKCell()
    c.shapes(kf.kcl.layer(1, 0)).insert(
        kf.kdb.DPolygon([kf.kdb.DPoint(0, 0), kf.kdb.DPoint(1, 0), kf.kdb.DPoint(0, 1)])
    )


def test_virtual_inst(straight: kf.KCell) -> None:
    c = kf.VKCell()
    inst = c << straight


def test_virtual_cell_insert(
    LAYER: kf.LayerEnum, straight: kf.KCell, wg_enc: kf.LayerEnclosure
) -> None:
    c = kf.KCell()

    vc = kf.VKCell("test_virtual_insert")

    e_bend = kf.cells.virtual.euler.virtual_bend_euler(
        width=0.5,
        radius=10,
        layer=LAYER.WG,
        angle=25,
        enclosure=wg_enc,
    )
    e1 = vc << e_bend
    e2 = vc << e_bend
    e3 = vc << e_bend
    e4 = vc << e_bend
    _s = kf.cells.virtual.straight.straight(
        width=0.5, length=10, layer=LAYER.WG, enclosure=wg_enc
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

    c.show()


def test_all_angle_route(LAYER: kf.LayerEnum, wg_enc: kf.LayerEnclosure) -> None:
    bb = [kf.kdb.DPoint(x, y) for x, y in [(0, 0), (500, 0), (250, 200), (500, 250)]]
    c = kf.KCell("test_virtual")
    vc = kf.VKCell("test_all_angle")
    _r = kf.routing.aa.optical.route(
        vc,
        width=5,
        layer=c.kcl.layer(1, 0),
        backbone=bb,
        straight_factory=partial(
            kf.cells.virtual.straight.straight,
            layer=c.kcl.layer(1, 0),
            enclosure=wg_enc,
        ),
        bend_factory=partial(
            kf.cells.virtual.euler.virtual_bend_euler,
            width=5,
            radius=20,
            layer=c.kcl.layer(1, 0),
            enclosure=wg_enc,
        ),
    )
    kf.VInstance(vc, kf.kdb.DCplxTrans()).insert_into(c)
    c.show()

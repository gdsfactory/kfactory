from collections.abc import Callable
from functools import partial
from pathlib import Path

import kfactory as kf
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

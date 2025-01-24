import re

import pytest
from conftest import Layers

import kfactory as kf
from kfactory.kcell import kcl


@kf.cell
def straight(width: int, length: int, layer: kf.kdb.LayerInfo) -> kf.KCell:
    c = kf.KCell()

    c.shapes(c.kcl.find_layer(layer)).insert(
        kf.kdb.Box(0, -width // 2, length, width // 2)
    )

    c.create_port(
        name="o1",
        trans=kf.kdb.Trans(2, False, 0, 0),
        width=width,
        layer=c.kcl.find_layer(layer),
    )
    c.create_port(
        name="o2",
        trans=kf.kdb.Trans(0, False, length, 0),
        width=width,
        layer=c.kcl.find_layer(layer),
    )
    return c


@pytest.fixture()
def wg(LAYER: Layers) -> kf.KCell:
    return straight(1000, 20000, LAYER.WG)


@pytest.fixture()
@kf.cell
def wg_floating_off_grid(LAYER: Layers) -> kf.KCell:
    with pytest.raises(AssertionError):
        c = kf.KCell()
        dbu = c.kcl.dbu

        p1 = kf.kcell.Port(
            width=c.kcl.to_dbu(10 + dbu / 2),
            name="o1",
            dcplx_trans=kf.kdb.DCplxTrans(1, 180, False, dbu / 2, 0),
            layer=c.kcl.find_layer(LAYER.WG),
        )
        p2 = kf.kcell.Port(
            width=c.kcl.to_dbu(10 + dbu / 2),
            name="o2",
            dcplx_trans=kf.kdb.DCplxTrans(1, 0, False, 20 + dbu, 0),
            layer=c.kcl.find_layer(LAYER.WG),
        )
        c.shapes(LAYER.WG).insert(kf.kdb.DBox(p1.x, -p1.width / 2, p2.x, p1.width / 2))

        c.add_port(p1)
        c.add_port(p2)

        kf.config.logfilter.regex = None

    return c


def test_straight(LAYER: Layers) -> None:
    straight(1000, 20000, LAYER.WG)


def test_settings(LAYER: Layers) -> None:
    c = straight(1000, 20000, LAYER.WG)

    assert c.settings["length"] == 20000
    assert c.settings["width"] == 1000
    assert c.name == "straight_W1000_L20000_LWG"


def test_connect_cplx_port(LAYER: Layers) -> None:
    c = kf.KCell()
    wg1 = c << straight(1000, 20000, LAYER.WG)
    port = kf.Port(
        width=c.kcl.to_dbu(1),
        layer=c.kcl.find_layer(LAYER.WG),
        name="cplxp1",
        dcplx_trans=kf.kdb.DCplxTrans(1, 30, False, 5, 10),
    )
    wg1.connect("o1", port)


def test_connect_cplx_inst(LAYER: Layers) -> None:
    c = kf.KCell()

    wg1 = c << straight(1000, 20000, LAYER.WG)
    wg2 = c << straight(1000, 20000, LAYER.WG)
    wg1.transform(kf.kdb.DCplxTrans(1, 30, False, 5, 10))
    wg2.connect("o1", wg1, "o2")
    kf.config.logfilter.regex = (
        f"Port ({re.escape(str(wg1.ports['o1']))}|"
        f"{re.escape(str(wg2.ports['o2']))}) is not an integer based port, "
        "converting to integer based"
    )

    c.add_port(wg1.ports["o1"])
    c.add_port(wg2.ports["o2"])

    kf.config.logfilter.regex = None
    c.flatten()


def test_connect_integer(wg: kf.KCell) -> None:
    c = kf.KCell()

    wg1 = c << wg
    wg2 = c << wg
    wg2.connect("o1", wg1, "o1")

    assert wg2.ports["o1"].trans == kf.kdb.Trans(0, False, 0, 0)


def test_keep_mirror(LAYER: Layers) -> None:
    c = kf.KCell()

    p1 = kf.Port(
        trans=kf.kdb.Trans.M90, width=1000, layer=c.kcl.find_layer(LAYER.WG), kcl=c.kcl
    )

    c.add_port(p1, name="o1")
    c.add_port(p1, name="o2", keep_mirror=True)

    assert c["o1"].trans.is_mirror() is False
    assert c["o2"].trans.is_mirror() is True


def test_addports_keep_mirror(LAYER: Layers) -> None:
    c = kf.KCell()

    ports = [
        kf.Port(
            name=f"{i}",
            width=1000,
            layer=c.kcl.find_layer(LAYER.WG),
            trans=kf.kdb.Trans(i, True, 0, 0),
        )
        for i in range(4)
    ]

    c.add_ports(ports, prefix="mirr_", keep_mirror=True)
    c.add_ports(ports, prefix="nomirr_", keep_mirror=False)

    for i in range(4):
        t1 = c[f"mirr_{i}"].trans
        t2 = c[f"nomirr_{i}"].trans

        t2_mirr = t2.dup()
        t2_mirr.mirror = not t2_mirr.is_mirror()

        assert t1 == t2_mirr


def test_contains(LAYER: Layers) -> None:
    s = kf.cells.straight.straight(width=1, length=10, layer=LAYER.WG)
    assert "o1" in s.ports
    assert s.ports["o1"] in s.ports
    assert s.ports["o1"].copy() in s.ports


def test_ports_set_center(LAYER: Layers) -> None:
    c = kf.KCell()
    p = c.create_port(
        name="o1",
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=c.kcl.find_layer(LAYER.WG),
    )
    p.center = (0, 0)
    assert p.dcplx_trans.disp == kf.kdb.DVector(0, 0)


def test_polar_copy(LAYER: Layers) -> None:
    c = kf.KCell()
    p = c.create_port(
        name="o1",
        width=1000,
        trans=kf.kdb.Trans(1, False, 0, 0),
        layer=c.kcl.find_layer(LAYER.WG),
    )

    p2 = p.copy_polar(500, 500, 2, True)
    assert p2.trans == kf.kdb.Trans(3, True, -500, 500)
    c.add_port(name="o2", port=p2)


def test_polar_copy_complex(LAYER: Layers) -> None:
    c = kf.KCell()
    p = c.create_port(
        name="o1",
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 30, False, 0.755, 0),
        layer=c.kcl.find_layer(LAYER.WG),
    )

    p2 = p.copy_polar(500, 500, 2, True)
    c.add_port(name="o2", port=p2)

    assert p2.dcplx_trans == kf.kdb.DCplxTrans(
        1, 210, True, 0.938012701892, 0.683012701892
    )


def test_dplx_port_dbu_port_conversion(LAYER: Layers) -> None:
    t1 = kf.kdb.DCplxTrans(1, 90, False, 10, 10)
    t2 = kf.kdb.Trans(1, False, 10_000, 10_000)
    p = kf.Port(
        width=kcl.to_dbu(1),
        dcplx_trans=t1,
        layer=kf.kcl.find_layer(LAYER.WG),
        kcl=kf.kcl,
    )
    assert p.trans == t2


def test_ports_eq() -> None:
    kcell = kf.KCell(name="test_ports_eq")
    dkcell = kf.DKCell.from_kcell(kcell)

    port = kf.Port(name="test", layer=1, width=2, center=(0, 0), angle=90)

    dkcell.ports = [port]  # type: ignore[assignment]
    assert kcell.ports == [port]


if __name__ == "__main__":
    test_ports_eq()

import re

import pytest
from conftest import Layers

import kfactory as kf
from kfactory.exceptions import PortWidthMismatchError


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
def wg(layers: Layers) -> kf.KCell:
    return straight(1000, 20000, layers.WG)


@pytest.fixture()
@kf.cell
def wg_floating_off_grid(layers: Layers) -> kf.KCell:
    with pytest.raises(AssertionError):
        c = kf.KCell()
        dbu = c.kcl.dbu

        p1 = kf.Port(
            width=c.kcl.to_dbu(10 + dbu / 2),
            name="o1",
            dcplx_trans=kf.kdb.DCplxTrans(1, 180, False, dbu / 2, 0),
            layer=c.kcl.find_layer(layers.WG),
        )
        p2 = kf.Port(
            width=c.kcl.to_dbu(10 + dbu / 2),
            name="o2",
            dcplx_trans=kf.kdb.DCplxTrans(1, 0, False, 20 + dbu, 0),
            layer=c.kcl.find_layer(layers.WG),
        )
        c.shapes(layers.WG).insert(kf.kdb.DBox(p1.x, -p1.width / 2, p2.x, p1.width / 2))

        c.add_port(port=p1)
        c.add_port(port=p2)

        kf.config.logfilter.regex = None

    return c


def test_straight(layers: Layers) -> None:
    straight(1000, 20000, layers.WG)


def test_settings(layers: Layers) -> None:
    c = straight(1000, 20000, layers.WG)

    assert c.settings["length"] == 20000
    assert c.settings["width"] == 1000
    assert c.name == "straight_W1000_L20000_LWG"


def test_connect_cplx_port(layers: Layers) -> None:
    c = kf.KCell()
    wg1 = c << straight(1000, 20000, layers.WG)
    port = kf.Port(
        width=c.kcl.to_dbu(1),
        layer=c.kcl.find_layer(layers.WG),
        name="cplxp1",
        dcplx_trans=kf.kdb.DCplxTrans(1, 30, False, 5, 10),
    )
    wg1.connect("o1", port)


def test_connect_cplx_inst(layers: Layers) -> None:
    c = kf.KCell()

    wg1 = c << straight(1000, 20000, layers.WG)
    wg2 = c << straight(1000, 20000, layers.WG)
    wg1.transform(kf.kdb.DCplxTrans(1, 30, False, 5, 10))
    wg2.connect("o1", wg1, "o2")
    kf.config.logfilter.regex = (
        f"Port ({re.escape(str(wg1.ports['o1']))}|"
        f"{re.escape(str(wg2.ports['o2']))}) is not an integer based port, "
        "converting to integer based"
    )

    c.add_port(port=wg1.ports["o1"])
    c.add_port(port=wg2.ports["o2"])

    kf.config.logfilter.regex = None
    c.flatten()


def test_connect_integer(wg: kf.KCell) -> None:
    c = kf.KCell()

    wg1 = c << wg
    wg2 = c << wg
    wg2.connect("o1", wg1, "o1")

    assert wg2.ports["o1"].trans == kf.kdb.Trans(0, False, 0, 0)


def test_connect_port_width_mismatch(layers: Layers, wg: kf.KCell) -> None:
    c = kf.KCell()
    wg1 = c << straight(1000, 20000, layers.WG)
    port = kf.Port(
        width=c.kcl.to_dbu(2),
        layer=c.kcl.find_layer(layers.WG),
        name="cplxp1",
        dcplx_trans=kf.kdb.DCplxTrans(1, 30, False, 5, 10),
    )
    with pytest.raises(PortWidthMismatchError) as excinfo:
        wg1.connect("o1", port)
    assert str(excinfo.value) == (
        f'Width mismatch between the ports {wg1.cell_name}["o1"] and Port "cplxp1" '
        f'("{wg1.ports["o1"].width}"/"2000")'
    )


def test_connect_instance_width_mismatch(layers: Layers, wg: kf.KCell) -> None:
    c = kf.KCell()
    wg1 = c << straight(1000, 20000, layers.WG)
    port = kf.Port(
        width=c.kcl.to_dbu(2),
        layer=c.kcl.find_layer(layers.WG),
        name="cplxp1",
        dcplx_trans=kf.kdb.DCplxTrans(1, 30, False, 5, 10),
    )
    c2 = kf.KCell()
    c2.add_port(port=port, name="o2")
    wg1_instance = c << c2

    with pytest.raises(PortWidthMismatchError) as excinfo:
        wg1.connect("o1", wg1_instance, "o2")
    assert str(excinfo.value) == (
        f'Width mismatch between the ports {wg1.cell_name}["o1"] and '
        f'{wg1_instance.cell_name}["o2"]("{wg1.ports["o1"].width}"/"2000")'
    )


def test_keep_mirror(layers: Layers) -> None:
    c = kf.KCell()

    p1 = kf.Port(
        trans=kf.kdb.Trans.M90, width=1000, layer=c.kcl.find_layer(layers.WG), kcl=c.kcl
    )

    c.add_port(port=p1, name="o1")
    c.add_port(port=p1, name="o2", keep_mirror=True)

    assert c["o1"].trans.is_mirror() is False
    assert c["o2"].trans.is_mirror() is True


def test_addports_keep_mirror(layers: Layers) -> None:
    c = kf.KCell()

    ports = [
        kf.Port(
            name=f"{i}",
            width=1000,
            layer=c.kcl.find_layer(layers.WG),
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


def test_contains(layers: Layers) -> None:
    s = kf.cells.straight.straight(width=1, length=10, layer=layers.WG)
    assert "o1" in s.ports
    assert s.ports["o1"] in s.ports
    assert s.ports["o1"].copy() in s.ports


def test_ports_set_center(layers: Layers) -> None:
    c = kf.KCell()
    p = c.create_port(
        name="o1",
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=c.kcl.find_layer(layers.WG),
    )
    p.center = (0, 0)
    assert p.dcplx_trans.disp == kf.kdb.DVector(0, 0)


def test_polar_copy(layers: Layers) -> None:
    c = kf.KCell()
    p = c.create_port(
        name="o1",
        width=1000,
        trans=kf.kdb.Trans(1, False, 0, 0),
        layer=c.kcl.find_layer(layers.WG),
    )

    p2 = p.copy_polar(500, 500, 2, True)
    assert p2.trans == kf.kdb.Trans(3, True, -500, 500)
    c.add_port(name="o2", port=p2)


def test_polar_copy_complex(layers: Layers) -> None:
    c = kf.KCell()
    p = c.create_port(
        name="o1",
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 30, False, 0.755, 0),
        layer=c.kcl.find_layer(layers.WG),
    )

    p2 = p.copy_polar(500, 500, 2, True)
    c.add_port(name="o2", port=p2)

    assert p2.dcplx_trans == kf.kdb.DCplxTrans(
        1, 210, True, 0.938012701892, 0.683012701892
    )


def test_dplx_port_dbu_port_conversion(layers: Layers, kcl: kf.KCLayout) -> None:
    t1 = kf.kdb.DCplxTrans(1, 90, False, 10, 10)
    t2 = kf.kdb.Trans(1, False, 10_000, 10_000)
    p = kf.Port(
        width=kcl.to_dbu(1),
        dcplx_trans=t1,
        layer=kcl.find_layer(layers.WG),
        kcl=kcl,
    )
    assert p.trans == t2


def test_ports_eq() -> None:
    kcell = kf.KCell(name="test_ports_eq")
    dkcell = kcell.to_dtype()

    port = kf.Port(name="test", layer=1, width=2, center=(0, 0), angle=90)

    dkcell.ports = [port]  # type: ignore[assignment]
    assert kcell.ports == [port]


def test_to_dtype(kcl: kf.KCLayout) -> None:
    port = kf.Port(name="o1", width=10, layer=1, center=(1000, 1000), angle=1)
    dtype = port.to_dtype()
    assert dtype.name == "o1"
    assert dtype.width == 0.01
    assert dtype.layer == 1
    assert dtype.center == (1, 1)
    assert dtype.angle == 90


def test_to_itype(kcl: kf.KCLayout) -> None:
    port = kf.DPort(name="o1", width=0.01, layer=1, center=(1, 1), angle=90)
    itype = port.to_itype()
    assert itype.name == "o1"
    assert itype.width == 10
    assert itype.layer == 1
    assert itype.center == (1000, 1000)
    assert itype.angle == 1


def test_ports_to_dtype() -> None:
    port = kf.Port(name="o1", width=10, layer=1, center=(1000, 1000), angle=1)
    ports = kf.Ports(
        kcl=kf.kcl,
        ports=[port],
    )
    dtype = ports.to_dtype()
    assert dtype[0] == port


def test_ports_to_itype() -> None:
    port = kf.DPort(name="o1", width=0.01, layer=1, center=(1, 1), angle=90)
    ports = kf.DPorts(
        kcl=kf.kcl,
        ports=[port],
    )
    itype = ports.to_itype()
    assert itype[0] == port


if __name__ == "__main__":
    pytest.main([__file__])

import re
from collections.abc import Sequence

import pytest

import kfactory as kf
from kfactory.exceptions import PortWidthMismatchError
from tests.conftest import Layers


@kf.cell
def straight_test(width: int, length: int, layer: kf.kdb.LayerInfo) -> kf.KCell:
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


@pytest.fixture
def wg(layers: Layers) -> kf.KCell:
    return straight_test(1000, 20000, layers.WG)


def test_settings(layers: Layers) -> None:
    c = straight_test(1000, 20000, layers.WG)

    assert c.settings["length"] == 20000
    assert c.settings["width"] == 1000
    assert c.name == "straight_test_W1000_L20000_LWG"


def test_connect_cplx_port(layers: Layers) -> None:
    c = kf.KCell()
    wg1 = c << straight_test(1000, 20000, layers.WG)
    port = kf.Port(
        width=c.kcl.to_dbu(1),
        layer=c.kcl.find_layer(layers.WG),
        name="cplxp1",
        dcplx_trans=kf.kdb.DCplxTrans(1, 30, False, 5, 10),
    )
    wg1.connect("o1", port)


def test_connect_cplx_inst(layers: Layers) -> None:
    c = kf.KCell()

    wg1 = c << straight_test(1000, 20000, layers.WG)
    wg2 = c << straight_test(1000, 20000, layers.WG)
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


def test_connect_port_width_mismatch(layers: Layers) -> None:
    c = kf.KCell()
    wg1 = c << straight_test(1000, 20000, layers.WG)
    port = kf.Port(
        width=c.kcl.to_dbu(2),
        layer=c.kcl.find_layer(layers.WG),
        name="cplxp1",
        dcplx_trans=kf.kdb.DCplxTrans(1, 30, False, 5, 10),
    )
    with pytest.raises(PortWidthMismatchError) as excinfo:
        wg1.connect("o1", port)
    assert str(excinfo.value) == (
        f'Width mismatch between the ports {wg1.cell_name}_0_0["o1"] and Port "cplxp1" '
        f'("{wg1.ports["o1"].width}"/"2000")'
    )


def test_connect_instance_width_mismatch(layers: Layers) -> None:
    c = kf.KCell()
    wg1 = c << straight_test(1000, 20000, layers.WG)
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
        f'Width mismatch between the ports {wg1.name}["o1"] and '
        f'{wg1_instance.name}["o2"]("{wg1.ports["o1"].width}"/"2000")'
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


def test_ports_to_dtype(kcl: kf.KCLayout) -> None:
    port = kf.Port(name="o1", width=10, layer=1, center=(1000, 1000), angle=1)
    ports = kf.Ports(
        kcl=kcl,
        ports=[port],
    )
    dtype = ports.to_dtype()
    assert dtype[0] == port


def test_ports_to_itype(kcl: kf.KCLayout) -> None:
    port = kf.DPort(name="o1", width=0.01, layer=1, center=(1, 1), orientation=90)
    ports = kf.DPorts(
        kcl=kcl,
        ports=[port],
    )
    itype = ports.to_itype()
    assert itype[0] == port


def test_ports_filter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = c.ports

    assert len(ports.filter(angle=0)) == 1
    assert len(ports.filter(angle=1)) == 0
    assert len(ports.filter(angle=2)) == 1
    assert len(ports.filter(angle=3)) == 0

    assert len(ports.filter(orientation=0)) == 1
    assert len(ports.filter(orientation=180)) == 1

    assert len(ports.filter(layer=0)) == 2
    assert len(ports.filter(layer=1)) == 0

    assert len(ports.filter(regex="o.*")) == 2
    assert len(ports.filter(regex="o3")) == 0

    assert len(ports.filter(port_type="optical")) == 2
    assert len(ports.filter(port_type="non-optical")) == 0


def test_ports_contains(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = c.ports
    port1 = ports[0]
    assert port1 in ports
    assert port1.base in ports
    assert port1.name is not None
    assert port1.name in ports
    assert "o3" not in ports


def test_ports_eq(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = c.ports
    ports2 = c.ports.copy()
    assert ports == ports2
    assert ports != list(ports)[:-1]
    assert ports != list(ports)[::-1]
    assert ports != 1


def test_ports_create_port(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = c.ports
    port = ports.create_port(name="o1", width=10, layer=1, center=(1000, 1000), angle=1)
    assert port in ports

    with pytest.raises(ValueError):
        ports.create_port(name="o1", layer=1, center=(1000, 1000), angle=1)  # type: ignore[call-overload]

    with pytest.raises(ValueError):
        ports.create_port(name="o1", width=10, center=(1000, 1000), angle=1)  # type: ignore[call-overload]

    with pytest.raises(ValueError):
        ports.create_port(name="o1", layer=1, width=10)  # type: ignore[call-overload]

    with pytest.raises(ValueError, match=r"and greater than 0."):
        ports.create_port(name="o1", width=-10, layer=1, center=(1000, 1000), angle=1)


def test_ports_get_all_named(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = c.ports
    assert ports.get_all_named().keys() == {"o1", "o2"}


def test_ports_copy(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = c.ports
    ports2 = ports.copy()
    assert ports2 == ports

    def _rename(ports: Sequence[kf.Port]) -> None:
        ports[0].name = "o3"
        ports[1].name = "o4"

    ports3 = ports.copy(rename_function=_rename)
    assert ports3[0].name == "o3"
    assert ports3[1].name == "o4"


def test_ports_print(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = c.ports
    ports.print()


def test_ports_pformat(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = c.ports
    assert ports.pformat()


def test_ports_getitem(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = c.ports
    assert ports[0] == ports["o1"]
    with pytest.raises(KeyError):
        ports["o3"]


def test_dports_add_port(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    ).to_dtype()
    ports = c.ports
    port = kf.Port(name="o3", width=10, layer=1, center=(1000, 1000), angle=1, kcl=kcl)
    ports.add_port(port=port, name="o3")
    assert ports["o3"] == port

    port2 = kf.DPort(name="o4", width=10, layer=1, center=(1000, 1000), orientation=1)
    out_port = ports.add_port(port=port2, name="o4")
    assert out_port == ports["o4"]

    port3 = kf.DPort(
        name="o5", width=10, layer=1, center=(1000, 1000), orientation=1, kcl=kcl
    )
    port3.base.trans = None
    port3.base.dcplx_trans = kf.kdb.DCplxTrans(1, 90, False, 0, 0)
    out_port = ports.add_port(port=port3, name="o5")
    assert out_port == ports["o5"]

    port4 = kf.DPort(
        name="o6", width=10, layer=1, center=(1000, 1000), orientation=1, kcl=kcl
    )
    port4.base.trans = kf.kdb.Trans.R90
    port4.base.dcplx_trans = None
    out_port = ports.add_port(port=port4, name="o6")
    assert out_port in ports


def test_dports_create_port(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    ).to_dtype()
    ports = c.ports
    port = ports.create_port(
        name="o1", width=10, layer=1, center=(1000, 1000), orientation=1
    )
    assert port in ports

    with pytest.raises(ValueError):
        ports.create_port(name="o1", layer=1, center=(1000, 1000), orientation=1)  # type: ignore[call-overload]

    with pytest.raises(ValueError):
        ports.create_port(name="o1", width=10, center=(1000, 1000), orientation=1)  # type: ignore[call-overload]

    with pytest.raises(ValueError):
        ports.create_port(name="o1", layer=1, width=10)  # type: ignore[call-overload]

    with pytest.raises(ValueError, match=r"and greater than 0."):
        ports.create_port(
            name="o1", width=-10, layer=1, center=(1000, 1000), orientation=1
        )

    with pytest.raises(ValueError, match="width needs to be even to snap to grid"):
        ports.create_port(
            name="o1", width=0.001, layer=1, center=(1000, 1000), orientation=1
        )

    port = ports.create_port(name="o1", width=10, layer=1, trans=kf.kdb.Trans.R90)
    assert port in ports


def test_dports_get_all_named(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    ).to_dtype()
    ports = c.ports
    assert ports.get_all_named().keys() == {"o1", "o2"}


def test_dports_getitem(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    ).to_dtype()
    ports = c.ports
    assert ports[0] == ports["o1"]
    with pytest.raises(KeyError):
        ports["o3"]


def test_dports_copy(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    ).to_dtype()
    ports = c.ports
    ports2 = ports.copy()
    assert ports2 == ports

    def _rename(ports: Sequence[kf.DPort]) -> None:
        ports[0].name = "o3"
        ports[1].name = "o4"

    ports3 = ports.copy(rename_function=_rename)
    assert ports3[0].name == "o3"
    assert ports3[1].name == "o4"


def test_dports_filter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    ).to_dtype()
    ports = c.ports

    assert len(ports.filter(angle=0)) == 1
    assert len(ports.filter(angle=1)) == 0
    assert len(ports.filter(angle=2)) == 1
    assert len(ports.filter(angle=3)) == 0

    assert len(ports.filter(orientation=0)) == 1
    assert len(ports.filter(orientation=180)) == 1

    assert len(ports.filter(layer=0)) == 2
    assert len(ports.filter(layer=1)) == 0

    assert len(ports.filter(regex="o.*")) == 2
    assert len(ports.filter(regex="o3")) == 0

    assert len(ports.filter(port_type="optical")) == 2
    assert len(ports.filter(port_type="non-optical")) == 0


def test_dports_print(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    ).to_dtype()
    ports = c.ports
    ports.print()


def test_dports_pformat(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    ).to_dtype()
    ports = c.ports
    assert ports.pformat()


def test_kcell_transformation(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell("Test Port Transformation")
    t_ = kf.kdb.Trans(rot=1, x=0, y=5000)
    p = c.create_port(trans=t_, width=1000, layer_info=layers.WG, name="o1")
    p_ = p.copy()

    t = kf.kdb.Trans(rot=2, mirrx=False, x=10_0000, y=20_000)
    c.transform(t)
    assert p.trans == t * t_
    assert p.trans == p_.copy(t).trans
    c.delete()


def test_ports_hash(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    d = {c: 1}
    assert d[c] == 1


def test_ports_repr(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    repr(c.ports)


if __name__ == "__main__":
    pytest.main([__file__, "-s"])

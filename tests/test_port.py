import math
from typing import Any

import pytest

import kfactory as kf
from kfactory.cross_section import CrossSection, CrossSectionSpec
from tests.conftest import Layers

_PortsType = tuple[kf.port.DPort, kf.port.Port, kf.port.DPort, kf.port.Port]


kcl = kf.KCLayout("TEST_PORT")
layers = Layers()
kcl.infos = layers


def get_ports() -> _PortsType:
    base = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(0, 0),
    )
    complex_base = base.__copy__()
    complex_base.dcplx_trans = kf.kdb.DCplxTrans(1, rot=20, x=0, y=0)
    complex_base.trans = None
    return (
        kf.port.DPort(base=base.__copy__()),
        kf.port.Port(base=base.__copy__()),
        kf.port.DPort(base=complex_base.__copy__()),
        kf.port.Port(base=complex_base.__copy__()),
    )


def test_create_port_error(kcl: kf.KCLayout, layers: Layers) -> None:
    db = kf.rdb.ReportDatabase("Connectivity Check")
    db_cell = db.create_cell("test")
    subc = db.create_category("WidthMismatch")

    straight_factory = kf.factories.straight.straight_dbu_factory(kcl)

    cell = straight_factory(length=10000, width=2000, layer=layers.WG)
    cell2 = straight_factory(length=10000, width=2000, layer=layers.WG)

    kf.port.create_port_error(
        cell.ports["o1"],
        cell2.ports["o1"],
        cell,
        cell2,
        db,
        db_cell,
        subc,
        kcl.dbu,
    )


def test_invalid_base_port_trans(kcl: kf.KCLayout, layers: Layers) -> None:
    with pytest.raises(ValueError, match="Both trans and dcplx_trans cannot be None."):
        kf.port.BasePort(
            name=None,
            kcl=kcl,
            cross_section=kcl.get_symmetrical_cross_section(
                CrossSectionSpec(layer=layers.WG, width=2000)
            ),
            port_type="optical",
        )

    with pytest.raises(
        ValueError, match="Only one of trans or dcplx_trans can be set."
    ):
        kf.port.BasePort(
            name=None,
            kcl=kcl,
            cross_section=kcl.get_symmetrical_cross_section(
                CrossSectionSpec(layer=layers.WG, width=2000)
            ),
            port_type="optical",
            trans=kf.kdb.Trans(1, 0),
            dcplx_trans=kf.kdb.DCplxTrans(1, 0),
        )


def test_base_port_ser_model(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    assert port.ser_model()
    port = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        dcplx_trans=kf.kdb.DCplxTrans(1, 0),
    )
    assert port.ser_model()


def test_base_port_get_trans(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )

    assert port.get_trans() == kf.kdb.Trans(1, 0)
    assert port.get_dcplx_trans() == kf.kdb.DCplxTrans(0.001, 0)

    port = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        dcplx_trans=kf.kdb.DCplxTrans(1, 0),
    )

    assert port.get_dcplx_trans() == kf.kdb.ICplxTrans(1, 0)
    assert port.get_trans() == kf.kdb.ICplxTrans(1000, 0).s_trans()


def test_base_port_eq(kcl: kf.KCLayout, layers: Layers) -> None:
    port1 = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    port2 = port1.model_copy()
    assert port1 == port2
    port2.trans = kf.kdb.Trans(2, 0)
    assert port1 != port2
    assert port1 != 2


@pytest.mark.parametrize("port", get_ports())
def test_port_eq(port: kf.port.ProtoPort[Any]) -> None:
    port2 = port.copy()
    assert port == port2
    port2.trans = kf.kdb.Trans(2, 0)
    assert port != port2
    assert port != 2


def test_port_kcl(kcl: kf.KCLayout, pdk: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.Port(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    assert port.kcl is kcl
    port.kcl = pdk
    assert port.kcl is pdk


def test_port_cross_section(kcl: kf.KCLayout, layers: Layers) -> None:
    base_port = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    port = kf.port.Port(base=base_port)
    assert port.cross_section.base is kcl.get_symmetrical_cross_section(
        CrossSectionSpec(layer=layers.WG, width=2000)
    )
    assert port.cross_section.width == 2000
    port.cross_section = kcl.get_symmetrical_cross_section(
        CrossSectionSpec(layer=layers.WG, width=3000)
    )
    assert port.cross_section.base is kcl.get_symmetrical_cross_section(
        CrossSectionSpec(layer=layers.WG, width=3000)
    )
    port.cross_section = CrossSection(
        kcl,
        base=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=3000)
        ),
    )
    assert port.cross_section.base is kcl.get_symmetrical_cross_section(
        CrossSectionSpec(layer=layers.WG, width=3000)
    )
    assert port.width == 3000
    dport = port.to_dtype()
    dport.cross_section = CrossSection(
        kcl,
        base=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=3000)
        ),
    )
    assert dport.cross_section.base is kcl.get_symmetrical_cross_section(
        CrossSectionSpec(layer=layers.WG, width=3000)
    )


def test_port_info() -> None:
    port = get_ports()[0].copy()
    assert port.info == kf.Info()
    port.info = kf.Info(test="test")
    assert port.info == kf.Info(test="test")


@pytest.mark.parametrize("port", get_ports())
def test_port_orientation(port: kf.port.ProtoPort[Any]) -> None:
    port.orientation = 0
    assert port.orientation == 0
    assert port.angle == 0

    port.orientation = 90
    assert port.orientation == 90
    assert port.angle == 1

    port.orientation = 180
    assert port.orientation == 180
    assert port.angle == 2

    port.orientation = 270
    assert port.orientation == 270
    assert port.angle == 3

    port.orientation = 360
    assert port.orientation == 0
    assert port.angle == 0

    port.orientation = 361
    assert math.isclose(port.orientation, 1)
    assert port.angle == 0

    port.orientation = 45
    assert math.isclose(port.orientation, 45)
    assert port.angle == 0

    port.angle = 7
    assert port.orientation == 270

    port.angle = 12
    assert port.angle == 0
    assert port.orientation == 0


def test_to_dtype() -> None:
    port = kf.Port(name="o1", width=10, layer=1, center=(1000, 1000), angle=1)
    dtype = port.to_dtype()
    assert dtype.name == "o1"
    assert dtype.width == 0.01
    assert dtype.layer == 1
    assert dtype.center == (1, 1)
    assert dtype.icenter == (1000, 1000)
    assert dtype.angle == 1
    assert dtype.orientation == 90


def test_to_itype() -> None:
    port = kf.DPort(name="o1", width=0.01, layer=1, center=(1, 1), orientation=90)
    itype = port.to_itype()
    assert itype.name == "o1"
    assert itype.width == 10
    assert itype.layer == 1
    assert itype.center == (1000, 1000)
    assert itype.icenter == (1000, 1000)
    assert itype.angle == 1


def test_port_copy(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.DPort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_symmetrical_cross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    port2 = port.copy()
    port.trans = kf.kdb.Trans(2, 0)
    assert port2.name is None
    assert port2.kcl is kcl
    assert port2.cross_section.base is kcl.get_symmetrical_cross_section(
        CrossSectionSpec(layer=layers.WG, width=2000)
    )
    assert port2.port_type == "optical"
    assert port2.trans == kf.kdb.Trans(1, 0)
    assert port.trans == kf.kdb.Trans(2, 0)


@pytest.mark.parametrize("port", get_ports())
def test_port_mirror(port: kf.port.ProtoPort[Any]) -> None:
    port.mirror = True
    assert port.mirror
    port.mirror = False
    assert not port.mirror


@pytest.mark.parametrize("port", get_ports())
def test_port_xy_center(port: kf.port.ProtoPort[Any]) -> None:
    port.dx = 543
    assert port.dx == 543

    port.dy = 789
    assert port.dy == 789

    port.dcenter = (654, 321)
    assert port.dcenter == (654, 321)

    port.x = 987
    assert port.x == 987

    port.y = 654
    assert port.y == 654

    port.center = (1, 1)
    assert port.center == (1, 1)

    port.icenter = (152, 153)
    assert port.icenter == (152, 153)

    port.ix = 121
    assert port.ix == 121

    port.iy = 122
    assert port.iy == 122


def test_print() -> None:
    port = get_ports()[0]
    port.print()


def test_port_init_with_port() -> None:
    port = kf.Port(name="o1", width=10, layer=1, center=(1000, 1000), angle=1)
    port2 = kf.Port(port=port)
    assert port2.name == "o1"
    assert port2.width == 10
    assert port2.layer == 1
    assert port2.center == (1000, 1000)
    assert port2.angle == 1


def test_dport_init_with_port() -> None:
    port = kf.DPort(name="o1", width=10, layer=1, center=(1000, 1000), orientation=45)
    port2 = kf.DPort(port=port)
    assert port2.name == "o1"
    assert port2.width == 10
    assert port2.center == (1000, 1000)
    assert math.isclose(port2.orientation, 45)


def test_port_invalid_init() -> None:
    with pytest.raises(ValueError):
        kf.Port(name="o1", layer=1, center=(1000, 1000), angle=1)  # type: ignore[call-overload]

    with pytest.raises(ValueError):
        kf.Port(name="o1", width=10, center=(1000, 1000), angle=1)  # type: ignore[call-overload]

    with pytest.raises(ValueError):
        kf.Port(name="o1", layer=1, width=10)  # type: ignore[call-overload]

    with pytest.raises(ValueError, match="Width must be greater than 0."):
        kf.Port(name="o1", width=-10, layer=1, center=(1000, 1000), angle=1)


def test_dport_invalid_init() -> None:
    with pytest.raises(ValueError):
        kf.DPort(name="o1", layer=1, center=(1000, 1000), orientation=90)

    with pytest.raises(ValueError):
        kf.DPort(name="o1", width=10, center=(1000, 1000), orientation=90)

    with pytest.raises(ValueError, match="Width must be greater than 0."):
        kf.DPort(name="o1", width=-10, layer=1, center=(1000, 1000), orientation=90)


def test_port_init(kcl: kf.KCLayout) -> None:
    port = kf.Port(
        name="o1",
        width=10,
        layer=1,
        trans=kf.kdb.Trans(1, 0).to_s(),
        kcl=kcl,
        port_type="optical",
    )
    assert port.trans == kf.kdb.Trans(1, 0)

    port = kf.Port(
        name="o1",
        width=10,
        layer=1,
        dcplx_trans=kf.kdb.DCplxTrans(1, 0).to_s(),
        kcl=kcl,
        port_type="optical",
    )
    assert port.dcplx_trans == kf.kdb.DCplxTrans(1, 0)


def test_dport_init() -> None:
    dport = kf.DPort(name="o1", width=10, layer=1, trans=kf.kdb.Trans(1, 0).to_s())
    assert dport.trans == kf.kdb.Trans(1, 0)

    dport = kf.DPort(
        name="o1", width=10, layer=1, dcplx_trans=kf.kdb.DCplxTrans(1, 0).to_s()
    )
    assert dport.dcplx_trans == kf.kdb.DCplxTrans(1, 0)


def test_dport_copy_polar() -> None:
    port = kf.DPort(name="o1", width=10, layer=1, center=(0, 0), orientation=0)
    port2 = port.copy_polar(d=1, d_orth=1, orientation=45, mirror=True)
    assert port2.dcplx_trans == kf.kdb.DCplxTrans(x=1, y=1, rot=45, mirrx=True)


def test_autorename(kcl: kf.KCLayout, layers: Layers) -> None:
    cell = kf.factories.straight.straight_dbu_factory(kcl)(
        length=10000, width=2000, layer=layers.WG
    )

    def _rename_ports(ports: kf.Ports) -> None:
        ports["o1"].name = "o3"
        ports["o2"].name = "o4"

    kf.port.autorename(cell, _rename_ports)

    assert cell.ports.get_all_named().keys() == {"o3", "o4"}


def test_rename_clockwise(kcl: kf.KCLayout, layers: Layers) -> None:
    cell = kf.factories.straight.straight_dbu_factory(kcl)(
        length=10000, width=2000, layer=layers.WG
    )
    _ports = cell.ports
    kf.port.rename_clockwise(_ports, start=0)
    assert _ports[0].name == "o0"
    assert _ports[1].name == "o1"


def test_filter_regex(kcl: kf.KCLayout, layers: Layers) -> None:
    cell = kf.factories.straight.straight_dbu_factory(kcl)(
        length=10000, width=2000, layer=layers.WG
    )
    ports = cell.ports
    filtered = list(kf.port.filter_regex(ports, "o2"))
    assert len(filtered) == 1

    filtered[0].name = None
    filtered = kf.port.filter_regex(filtered, "o2")
    assert len(list(filtered)) == 0


def test_filter_layer_pt_reg(kcl: kf.KCLayout, layers: Layers) -> None:
    cell = kf.factories.straight.straight_dbu_factory(kcl)(
        length=10000, width=2000, layer=layers.WG
    )
    ports = cell.ports
    filtered = kf.port.filter_layer_pt_reg(
        ports, layer=0, port_type="optical", regex="o2"
    )
    assert len(list(filtered)) == 1


def test_rename_clockwise_multi(kcl: kf.KCLayout, layers: Layers) -> None:
    cell = kf.factories.straight.straight_dbu_factory(kcl)(
        length=10000, width=2000, layer=layers.WG
    )
    ports = cell.ports
    ports["o1"].name = "o4"
    ports["o2"].name = "o5"
    kf.port.rename_clockwise_multi(ports, layers=[0], regex="o4")
    assert len(list(ports)) == 2


def test_create(kcl: kf.KCLayout, layers: Layers) -> None:
    cell = kcl.kcell()

    cell.create_port(
        name="o1",
        cross_section=kcl.get_icross_section(
            CrossSectionSpec(layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )


if __name__ == "__main__":
    pytest.main(["-s", __file__])

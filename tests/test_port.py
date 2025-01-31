import math

import pytest
from conftest import Layers

import kfactory as kf
from kfactory.cross_section import CrossSectionSpec


def test_create_port_error(kcl: kf.KCLayout, layers: Layers) -> None:
    db = kf.rdb.ReportDatabase("Connectivity Check")
    db_cell = db.create_cell("test")
    subc = db.create_category("WidthMismatch")

    cell = kf.factories.straight.straight_dbu_factory(kcl)(
        length=10000, width=2000, layer=layers.WG
    )
    cell2 = kf.factories.straight.straight_dbu_factory(kcl)(
        length=10000, width=2000, layer=layers.WG
    )

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
            cross_section=kcl.get_cross_section(
                CrossSectionSpec(main_layer=layers.WG, width=2000)
            ),
            port_type="optical",
        )

    with pytest.raises(
        ValueError, match="Only one of trans or dcplx_trans can be set."
    ):
        kf.port.BasePort(
            name=None,
            kcl=kcl,
            cross_section=kcl.get_cross_section(
                CrossSectionSpec(main_layer=layers.WG, width=2000)
            ),
            port_type="optical",
            trans=kf.kdb.Trans(1, 0),
            dcplx_trans=kf.kdb.DCplxTrans(1, 0),
        )


def test_base_port_ser_model(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_cross_section(
            CrossSectionSpec(main_layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    assert port.ser_model()
    port = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_cross_section(
            CrossSectionSpec(main_layer=layers.WG, width=2000)
        ),
        port_type="optical",
        dcplx_trans=kf.kdb.DCplxTrans(1, 0),
    )
    assert port.ser_model()


def test_base_port_get_trans(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_cross_section(
            CrossSectionSpec(main_layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )

    assert port.get_trans() == kf.kdb.Trans(1, 0)
    assert port.get_dcplx_trans() == kf.kdb.DCplxTrans(0.001, 0)

    port = kf.port.BasePort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_cross_section(
            CrossSectionSpec(main_layer=layers.WG, width=2000)
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
        cross_section=kcl.get_cross_section(
            CrossSectionSpec(main_layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    port2 = port1.model_copy()
    assert port1 == port2
    port2.trans = kf.kdb.Trans(2, 0)
    assert port1 != port2
    assert port1 != 2


def test_port_eq(kcl: kf.KCLayout, layers: Layers) -> None:
    port1 = kf.port.Port(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_cross_section(
            CrossSectionSpec(main_layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    port2 = port1.copy()
    assert port1 == port2
    port2.trans = kf.kdb.Trans(2, 0)
    assert port1 != port2
    assert port1 != 2


def test_port_kcl(kcl: kf.KCLayout, pdk: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.Port(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_cross_section(
            CrossSectionSpec(main_layer=layers.WG, width=2000)
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
        cross_section=kcl.get_cross_section(
            CrossSectionSpec(main_layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    port = kf.port.Port(base=base_port)
    assert port.cross_section is kcl.get_cross_section(
        CrossSectionSpec(main_layer=layers.WG, width=2000)
    )
    assert port.cross_section.width == 2000
    port.cross_section = kcl.get_cross_section(
        CrossSectionSpec(main_layer=layers.WG, width=3000)
    )
    assert port.cross_section is kcl.get_cross_section(
        CrossSectionSpec(main_layer=layers.WG, width=3000)
    )
    assert port.width == 3000


def test_port_info(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.Port(
        base=kf.port.BasePort(
            name=None,
            kcl=kcl,
            cross_section=kcl.get_cross_section(
                CrossSectionSpec(main_layer=layers.WG, width=2000)
            ),
            port_type="optical",
            trans=kf.kdb.Trans(1, 0),
        )
    )
    assert port.info == kf.Info()
    port.info = kf.Info(test="test")
    assert port.info == kf.Info(test="test")


def test_port_orientation(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.Port(
        base=kf.port.BasePort(
            name=None,
            kcl=kcl,
            cross_section=kcl.get_cross_section(
                CrossSectionSpec(main_layer=layers.WG, width=2000)
            ),
            port_type="optical",
            trans=kf.kdb.Trans(1, 0),
        )
    )
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
    assert port.orientation == 45
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
    assert dtype.angle == 1
    assert dtype.orientation == 90


def test_to_itype() -> None:
    port = kf.DPort(name="o1", width=0.01, layer=1, center=(1, 1), orientation=90)
    itype = port.to_itype()
    assert itype.name == "o1"
    assert itype.width == 10
    assert itype.layer == 1
    assert itype.center == (1000, 1000)
    assert itype.angle == 1


def test_port_copy(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.DPort(
        name=None,
        kcl=kcl,
        cross_section=kcl.get_cross_section(
            CrossSectionSpec(main_layer=layers.WG, width=2000)
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )
    port2 = port.copy()
    port.trans = kf.kdb.Trans(2, 0)
    assert port2.name is None
    assert port2.kcl is kcl
    assert port2.cross_section is kcl.get_cross_section(
        CrossSectionSpec(main_layer=layers.WG, width=2000)
    )
    assert port2.port_type == "optical"
    assert port2.trans == kf.kdb.Trans(1, 0)
    assert port.trans == kf.kdb.Trans(2, 0)


def test_port_mirror(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.DPort(
        base=kf.port.BasePort(
            name=None,
            kcl=kcl,
            cross_section=kcl.get_cross_section(
                CrossSectionSpec(main_layer=layers.WG, width=2000)
            ),
            port_type="optical",
            trans=kf.kdb.Trans(1, 0),
        )
    )
    port.mirror = True
    assert port.mirror
    port.mirror = False
    assert not port.mirror


def test_port_xy(kcl: kf.KCLayout, layers: Layers) -> None:
    port = kf.port.DPort(
        base=kf.port.BasePort(
            name=None,
            kcl=kcl,
            cross_section=kcl.get_cross_section(
                CrossSectionSpec(main_layer=layers.WG, width=2000)
            ),
            port_type="optical",
            trans=kf.kdb.Trans(0, 0),
        )
    )
    port.dx = 1000
    assert port.dx == 1000
    assert port.dy == 0
    assert port.dcenter == (1000, 0)

    port.dcenter = (1000, 1000)
    assert port.dx == 1000
    assert port.dy == 1000
    assert port.dcenter == (1000, 1000)

    port.dy = 1000
    assert port.dx == 1000
    assert port.dy == 1000
    assert port.dcenter == (1000, 1000)

    port.center = (1, 1)
    assert port.x == 1
    assert port.y == 1
    assert port.center == (1, 1)


if __name__ == "__main__":
    pytest.main(["-s", __file__])

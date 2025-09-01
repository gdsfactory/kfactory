import klayout.db as kdb
import pytest

import kfactory as kf
from kfactory.cross_section import CrossSection, CrossSectionSpec, DCrossSection
from kfactory.exceptions import LockedError
from tests.conftest import Layers


def test_unnamed_dkcell(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def unnamed_dkcell(name: str = "a") -> kf.DKCell:
        return kcl.dkcell(name)

    c1 = unnamed_dkcell("test_unnamed_dkcell")
    c2 = unnamed_dkcell("test_unnamed_dkcell")
    assert c1 is c2


def test_nested_dict_list_dkcell(kcl: kf.KCLayout) -> None:
    dl: dict[str, list[dict[str, str | int] | int] | int] = {
        "a": 5,
        "b": [5, {"c": "d", "e": 6}],
    }

    @kcl.cell
    def nested_list_dict_dkcell(
        arg1: dict[str, list[dict[str, str | int] | int] | int],
    ) -> kf.DKCell:
        return kcl.dkcell("test_nested_list_dict_dkcell")

    c = nested_list_dict_dkcell(dl)
    assert dl == c.settings["arg1"]
    assert dl is not c.settings["arg1"]


def test_dkcell_ports() -> None:
    kcl = kf.KCLayout("TEST_DKCELL_PORTS")
    c = kcl.dkcell("test_dkcell_ports")
    assert isinstance(c.ports, kf.DPorts)
    assert list(c.ports) == []
    p = c.create_port(width=1, layer=1, center=(0, 0), orientation=90)
    assert p in c.ports
    assert c.ports == [p]


def test_dkcell_locked(layers: Layers) -> None:
    kcl = kf.KCLayout("TEST_DKCELL_LOCKED")
    kcl.infos = layers
    c = kcl.dkcell("test_dkcell_locked")
    assert c.locked is False
    c.base.lock()
    assert c.locked is True

    p = kf.port.DPort(
        name="o1",
        kcl=kcl,
        cross_section=DCrossSection(
            kcl,
            base=kcl.get_symmetrical_cross_section(
                CrossSectionSpec(layer=layers.WG, width=2000)
            ),
        ),
        port_type="optical",
        trans=kf.kdb.Trans(1, 0),
    )

    with pytest.raises(LockedError):
        c.ports = []

    with pytest.raises(LockedError):
        c.create_port(width=1, layer=1, center=(0, 0), orientation=90)

    with pytest.raises(LockedError):
        c.add_port(port=p)

    with pytest.raises(LockedError):
        c.add_ports(ports=[p])

    with pytest.raises(LockedError):
        c.create_port(
            name="o1",
            cross_section=CrossSection(
                kcl,
                base=kcl.get_symmetrical_cross_section(
                    CrossSectionSpec(layer=layers.WG, width=2000)
                ),
            ),
            port_type="optical",
            trans=kf.kdb.Trans(1, 0),
        )

    with pytest.raises(ValueError):
        _ = c.factory_name

    with pytest.raises(LockedError):
        c.create_vinst(c)

    with pytest.raises(LockedError):
        c.base.name = "test_dkcell_locked"


def test_dkcell_attributes() -> None:
    kcl = kf.KCLayout("TEST_DKCELL_ATTRIBUTES")
    c = kcl.dkcell("test_dkcell_attributes")
    c.shapes(1).insert(kdb.DBox(0, 0, 10, 10))
    assert c.shapes(1).size() == 1
    assert c.bbox(1) == kdb.DBox(0, 0, 10, 10)
    assert c.ibbox(1) == kdb.Box(0, 0, 10_000, 10_000)
    assert c.dbbox(1) == kdb.DBox(0, 0, 10, 10)

    assert c.x == 5
    assert c.y == 5
    assert c.xmin == 0
    assert c.ymin == 0
    assert c.xmax == 10
    assert c.ymax == 10
    assert c.xsize == 10
    assert c.ysize == 10
    assert c.center == (5, 5)

    assert c.ix == 5000
    assert c.iy == 5000
    assert c.ixmin == 0
    assert c.iymin == 0
    assert c.ixmax == 10000
    assert c.iymax == 10000
    assert c.ixsize == 10000
    assert c.iysize == 10000
    assert c.icenter == (5000, 5000)

    assert c.dxmin == 0.0
    assert c.dymin == 0.0
    assert c.dxmax == 10.0
    assert c.dymax == 10.0
    assert c.dxsize == 10.0
    assert c.dysize == 10.0
    assert c.dx == 5.0
    assert c.dy == 5.0
    assert c.dcenter == (5.0, 5.0)

    assert (
        str(c.isize_info)
        == "SizeInfo: self.width=10000, self.height=10000, self.west=0, self.east=10000"
        ", self.south=0, self.north=10000"
    )
    assert c.isize_info.west == 0
    assert c.isize_info.east == 10000
    assert c.isize_info.south == 0
    assert c.isize_info.north == 10000
    assert c.isize_info.width == 10000
    assert c.isize_info.height == 10000
    assert c.isize_info.sw == (0, 0)
    assert c.isize_info.nw == (0, 10000)
    assert c.isize_info.se == (10000, 0)
    assert c.isize_info.ne == (10000, 10000)
    assert c.isize_info.cw == (0, 5000)
    assert c.isize_info.ce == (10000, 5000)
    assert c.isize_info.sc == (5000, 0)
    assert c.isize_info.nc == (5000, 10000)
    assert c.isize_info.cc == (5000, 5000)
    assert c.isize_info.center == (5000, 5000)

    assert (
        str(c.dsize_info)
        == "SizeInfo: self.width=10.0, self.height=10.0, self.west=0.0, self.east=10.0"
        ", self.south=0.0, self.north=10.0"
    )
    assert c.dsize_info.west == 0.0
    assert c.dsize_info.east == 10.0
    assert c.dsize_info.south == 0.0
    assert c.dsize_info.north == 10.0
    assert c.dsize_info.width == 10.0
    assert c.dsize_info.height == 10.0
    assert c.dsize_info.sw == (0.0, 0.0)
    assert c.dsize_info.nw == (0.0, 10.0)
    assert c.dsize_info.se == (10.0, 0.0)
    assert c.dsize_info.ne == (10.0, 10.0)
    assert c.dsize_info.cw == (0.0, 5.0)
    assert c.dsize_info.ce == (10.0, 5.0)
    assert c.dsize_info.sc == (5.0, 0.0)
    assert c.dsize_info.nc == (5.0, 10.0)
    assert c.dsize_info.cc == (5.0, 5.0)
    assert c.dsize_info.center == (5.0, 5.0)

    assert (
        str(c.size_info)
        == "SizeInfo: self.width=10.0, self.height=10.0, self.west=0.0, self.east=10.0"
        ", self.south=0.0, self.north=10.0"
    )
    assert c.size_info.west == 0.0
    assert c.size_info.east == 10.0
    assert c.size_info.south == 0.0
    assert c.size_info.north == 10.0
    assert c.size_info.width == 10
    assert c.size_info.height == 10
    assert c.size_info.sw == (0, 0)
    assert c.size_info.nw == (0, 10)
    assert c.size_info.se == (10, 0)
    assert c.size_info.ne == (10, 10)
    assert c.size_info.cw == (0, 5)
    assert c.size_info.ce == (10, 5)
    assert c.size_info.sc == (5, 0)
    assert c.size_info.nc == (5, 10)
    assert c.size_info.cc == (5, 5)
    assert c.size_info.center == (5, 5)


def test_size_info_call(kcl: kf.KCLayout) -> None:
    c = kcl.kcell()

    c.shapes(1).insert(kdb.DBox(0, 0, 10, 10))

    new_size_info = c.size_info(1)

    assert new_size_info._bf() == c.size_info._bf()


def test_tkcell(kcl: kf.KCLayout) -> None:
    c = kcl.dkcell("test_dkcell_getattr")
    assert c.base.called_cells() == []


def test_cell_decorator(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def test_cell(name: str) -> kf.DKCell:
        return kcl.dkcell(name)

    @kcl.cell()
    def test_cell2(name: str) -> kf.DKCell:
        return kcl.dkcell(name)

    def post_process(x: kf.DKCell) -> None: ...

    @kcl.cell(post_process=[post_process])
    def test_cell3(name: str) -> kf.DKCell:
        return kcl.dkcell(name)

    @kcl.cell(post_process=[lambda x: None], output_type=kf.DKCell)
    def test_cell4(name: str) -> kf.DKCell:
        return kcl.dkcell(name)

    @kcl.cell(output_type=kf.DKCell)
    def test_cell5(name: str) -> kf.DKCell:
        return kcl.dkcell(name)

    cell1 = test_cell("cell1")
    cell2 = test_cell2("cell2")
    cell3 = test_cell3("cell3")
    cell4 = test_cell4("cell4")
    cell5 = test_cell5("cell5")

    assert isinstance(cell1, kf.DKCell)
    assert isinstance(cell2, kf.DKCell)
    assert isinstance(cell3, kf.DKCell)
    assert isinstance(cell4, kf.DKCell)
    assert isinstance(cell5, kf.DKCell)

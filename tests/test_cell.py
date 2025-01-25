from collections.abc import Callable
from tempfile import NamedTemporaryFile

import pytest
from conftest import Layers

import kfactory as kf


def test_enclosure_name(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    wg = straight_factory_dbu(width=1000, length=10000)
    assert wg.name == "straight_W1000_L10000_LWG_EWGSTD"


def test_circular_snapping(LAYER: Layers) -> None:
    b = kf.cells.circular.bend_circular(width=1, radius=10, layer=LAYER.WG, angle=90)
    assert b.ports["o2"].dcplx_trans.disp == kf.kcl.to_um(b.ports["o2"].trans.disp)


def test_euler_snapping(LAYER: Layers) -> None:
    b = kf.cells.euler.bend_euler(width=1, radius=10, layer=LAYER.WG, angle=90)
    assert b.ports["o2"].dcplx_trans.disp == kf.kcl.to_um(b.ports["o2"].trans.disp)


@kf.cell
def unnamed_cell(name: str = "a") -> kf.KCell:
    c = kf.kcl.kcell(name)
    return c


def test_unnamed_cell() -> None:
    c1 = unnamed_cell("test_unnamed_cell")
    c2 = unnamed_cell("test_unnamed_cell")
    assert c1 is c2


@kf.cell
def nested_list_dict(
    arg1: dict[str, list[dict[str, str | int] | int] | int],
) -> kf.KCell:
    c = kf.kcl.kcell()
    return c


def test_nested_dict_list() -> None:
    dl: dict[str, list[dict[str, str | int] | int] | int] = {
        "a": 5,
        "b": [5, {"c": "d", "e": 6}],
    }
    c = nested_list_dict(dl)
    assert dl == c.settings["arg1"]
    assert dl is not c.settings["arg1"]


def test_no_snap(LAYER: Layers) -> None:
    c = kf.KCell()

    c.create_port(
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=c.kcl.find_layer(LAYER.WG),
    )

    p = c.ports[0]

    assert p.dcplx_trans.disp != c.kcl.to_um(p.trans.disp)


def test_namecollision(LAYER: Layers) -> None:
    b1 = kf.cells.circular.bend_circular(width=1, radius=10.5, layer=LAYER.WG)
    b2 = kf.cells.circular.bend_circular(width=1, radius=10.5000005, layer=LAYER.WG)

    assert b1.name != b2.name


def test_nested_dic() -> None:
    @kf.kcl.cell
    def recursive_dict_cell(d: dict[str, dict[str, str] | str]) -> kf.KCell:
        c = kf.KCell()
        return c

    recursive_dict_cell({"test": {"test2": "test3"}, "test4": "test5"})


def test_ports_cell(LAYER: Layers) -> None:
    c = kf.KCell()
    c.create_port(
        name="o1",
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=c.kcl.find_layer(LAYER.WG),
    )
    assert c["o1"]
    assert "o1" in c.ports


def test_ports_instance(LAYER: Layers) -> None:
    c = kf.KCell()
    c.create_port(
        name="o1",
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=c.kcl.find_layer(LAYER.WG),
    )
    c2 = kf.KCell()
    ref = c2 << c
    assert c["o1"]
    assert "o1" in c.ports
    assert ref["o1"]
    assert "o1" in ref.ports


def test_getter(LAYER: Layers) -> None:
    c = kf.KCell()
    c << kf.cells.straight.straight(width=1, length=10, layer=LAYER.WG)
    assert c.y == 0
    assert c.dy == 0


def test_array(straight: kf.KCell) -> None:
    c = kf.KCell()
    wg_array = c.create_inst(
        straight, a=kf.kdb.Vector(15_000, 0), b=kf.kdb.Vector(0, 3_000), na=3, nb=5
    )
    for b in range(5):
        for a in range(3):
            wg_array["o1", a, b]
            wg_array["o1", a, b]


def test_array_indexerror(straight: kf.KCell) -> None:
    c = kf.KCell()
    wg_array = c.create_inst(
        straight, a=kf.kdb.Vector(15_000, 0), b=kf.kdb.Vector(0, 3_000), na=3, nb=5
    )
    regex = kf.config.logfilter.regex
    kf.config.logfilter.regex = r"^An error has been caught in function '__getitem__'"
    with pytest.raises(IndexError):
        wg_array["o1", 3, 5]
        wg_array["o1", 3, 5]
    kf.config.logfilter.regex = regex


def test_invalid_array(monkeypatch: pytest.MonkeyPatch, straight: kf.KCell) -> None:
    c = kf.KCell()
    wg = c.create_inst(straight)
    regex = kf.config.logfilter.regex
    kf.config.logfilter.regex = r"^An error has been caught in function '__getitem__'"
    with pytest.raises(KeyError):
        for b in range(1):
            for a in range(1):
                wg["o1", a, b]
                wg["o1", a, b]
    kf.config.logfilter.regex = regex


def test_cell_decorator_error(LAYER: Layers) -> None:
    kcl2 = kf.KCLayout("decorator_test")

    @kf.kcl.cell
    def wrong_cell() -> kf.KCell:
        c = kcl2.kcell("wrong_test")
        return c

    regex = kf.config.logfilter.regex
    kf.config.logfilter.regex = (
        r"^An error has been caught in function 'wrapper_autocell'"
    )
    with pytest.raises(ValueError):
        wrong_cell()
    kf.config.logfilter.regex = regex


def test_info(LAYER: Layers) -> None:
    @kf.kcl.cell(info={"test": 42})
    def test_info_cell(test: int) -> kf.KCell:
        return kf.kcl.kcell()

    c = test_info_cell(42)
    assert c.info["test"] == 42


def test_flatten(LAYER: Layers) -> None:
    c = kf.KCell()
    _ = c << kf.cells.straight.straight(width=1, length=10, layer=LAYER.WG)
    assert len(c.insts) == 1, "c.insts should have 1 inst after adding a cell"
    c.flatten()
    assert len(c.insts) == 0, "c.insts should have 0 insts after flatten()"


def test_size_info(LAYER: Layers) -> None:
    c = kf.KCell()
    ref = c << kf.cells.straight.straight(width=1, length=10, layer=LAYER.WG)
    assert ref.size_info.ne[0] == 10000
    assert ref.dsize_info.ne[0] == 10


def test_overwrite(LAYER: Layers) -> None:
    kcl = kf.KCLayout("CELL_OVERWRITE")

    @kcl.cell
    def test_overwrite_cell() -> kf.KCell:
        print("overwrite1")
        c = kcl.kcell()
        return c

    c1 = test_overwrite_cell()

    @kcl.cell(overwrite_existing=True)  # type: ignore[no-redef]
    def test_overwrite_cell() -> kf.KCell:
        print("overwrite2")
        c = kcl.kcell()
        return c

    c2 = test_overwrite_cell()

    assert c2 is not c1
    assert c1._destroyed()


def test_layout_cache(LAYER: Layers) -> None:
    kcl_write = kf.KCLayout("TEST_LAYOUT_CACHE_WRITE")
    kcl_read = kf.KCLayout("TEST_LAYOUT_CACHE_READ")

    @kcl_write.cell(basename="straight")
    def write_straight() -> kf.KCell:
        c = kcl_write.kcell()
        c.shapes(kcl_write.layer(1, 0)).insert(kf.kdb.Box(10_000, 1000))
        return c

    s_write = write_straight()
    tf = NamedTemporaryFile(suffix=".gds.gz")
    kcl_write.write(tf.name)
    kcl_read.read(tf.name)

    @kcl_read.cell(basename="straight", layout_cache=True)
    def read_straight() -> kf.KCell:
        c = kcl_read.kcell()
        c.shapes(kcl_read.layer(1, 0)).insert(kf.kdb.Box(5000, 1000))
        return c

    s_read = read_straight()
    assert s_write.bbox() == s_read.bbox()


def test_check_ports(LAYER: Layers) -> None:
    kcl = kf.KCLayout("CHECK_PORTS", infos=Layers)
    kcl.layers = kcl.layerenum_from_dict(layers=LAYER)

    @kcl.cell
    def test_multi_ports() -> kf.KCell:
        c = kcl.kcell()
        c.create_port(
            name="a", trans=kf.kdb.Trans.R0, width=1000, layer=kcl.find_layer(1, 0)
        )
        c.create_port(
            name="a", trans=kf.kdb.Trans.R180, width=1000, layer=kcl.find_layer(1, 0)
        )
        return c

    regex = kf.config.logfilter.regex
    kf.config.logfilter.regex = (
        "^An error has been caught in function "
        "'wrapper_autocell', process 'MainProcess'"
    )

    with pytest.raises(ValueError):
        test_multi_ports()

    kf.config.logfilter.regex = regex


def test_ports_in_cells() -> None:
    kcell = kf.KCell(name="test")
    dkcell = kf.DKCell.from_kcell(kcell)

    port = kf.Port(name="test", layer=1, width=2, center=(0, 0), angle=90)
    new_port = kcell.add_port(port, "o1")

    assert new_port in kcell.ports
    assert new_port in dkcell.ports


def test_kcell_attributes() -> None:
    c = kf.kcl.kcell("test_kcell_attributes")
    c.shapes(1).insert(kf.kdb.Box(0, 0, 10, 10))
    assert c.shapes(1).size() == 1
    assert c.bbox(1) == kf.kdb.Box(0, 0, 10, 10)
    assert c.ibbox(1) == kf.kdb.Box(0, 0, 10, 10)
    assert c.dbbox(1) == kf.kdb.DBox(0, 0, 0.01, 0.01)

    assert c.x == 5
    assert c.y == 5
    assert c.xmin == 0
    assert c.ymin == 0
    assert c.xmax == 10
    assert c.ymax == 10
    assert c.xsize == 10
    assert c.ysize == 10
    assert c.center == (5, 5)

    assert c.ix == 5
    assert c.iy == 5
    assert c.ixmin == 0
    assert c.iymin == 0
    assert c.ixmax == 10
    assert c.iymax == 10
    assert c.ixsize == 10
    assert c.iysize == 10
    assert c.icenter == (5, 5)

    assert c.dxmin == 0.0
    assert c.dymin == 0.0
    assert c.dxmax == 0.01
    assert c.dymax == 0.01
    assert c.dxsize == 0.01
    assert c.dysize == 0.01
    assert c.dx == 0.005
    assert c.dy == 0.005
    assert c.dcenter == (0.005, 0.005)

    assert (
        str(c.isize_info)
        == "SizeInfo: self.width=10, self.height=10, self.west=0, self.east=10"
        ", self.south=0, self.north=10"
    )
    assert c.isize_info.west == 0
    assert c.isize_info.east == 10
    assert c.isize_info.south == 0
    assert c.isize_info.north == 10
    assert c.isize_info.width == 10
    assert c.isize_info.height == 10
    assert c.isize_info.sw == (0, 0)
    assert c.isize_info.nw == (0, 10)
    assert c.isize_info.se == (10, 0)
    assert c.isize_info.ne == (10, 10)
    assert c.isize_info.cw == (0, 5)
    assert c.isize_info.ce == (10, 5)
    assert c.isize_info.sc == (5, 0)
    assert c.isize_info.nc == (5, 10)
    assert c.isize_info.cc == (5, 5)
    assert c.isize_info.center == (5, 5)

    assert (
        str(c.dsize_info)
        == "SizeInfo: self.width=0.01, self.height=0.01, self.west=0.0, self.east=0.01"
        ", self.south=0.0, self.north=0.01"
    )
    assert c.dsize_info.west == 0.0
    assert c.dsize_info.east == 0.01
    assert c.dsize_info.south == 0.0
    assert c.dsize_info.north == 0.01
    assert c.dsize_info.width == 0.01
    assert c.dsize_info.height == 0.01
    assert c.dsize_info.sw == (0.0, 0.0)
    assert c.dsize_info.nw == (0.0, 0.01)
    assert c.dsize_info.se == (0.01, 0.0)
    assert c.dsize_info.ne == (0.01, 0.01)
    assert c.dsize_info.cw == (0.0, 0.005)
    assert c.dsize_info.ce == (0.01, 0.005)
    assert c.dsize_info.sc == (0.005, 0.0)
    assert c.dsize_info.nc == (0.005, 0.01)
    assert c.dsize_info.cc == (0.005, 0.005)
    assert c.dsize_info.center == (0.005, 0.005)

    assert (
        str(c.size_info)
        == "SizeInfo: self.width=10, self.height=10, self.west=0, self.east=10"
        ", self.south=0, self.north=10"
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


if __name__ == "__main__":
    test_kcell_attributes()

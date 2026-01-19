import functools
import threading
import warnings
from collections.abc import Callable
from tempfile import NamedTemporaryFile
from typing import Any

import pytest

import kfactory as kf
from kfactory.cross_section import CrossSection, CrossSectionSpec
from kfactory.exceptions import LockedError
from tests.conftest import Layers


def test_enclosure_name(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    wg = straight_factory_dbu(width=1000, length=10000)
    assert wg.name == "straight_W1000_L10000_LWG_EWGSTD"
    gds_regression(wg)


def test_circular_snapping(
    kcl: kf.KCLayout,
    layers: Layers,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    b = kf.factories.circular.bend_circular_factory(kcl=kcl)(
        width=1, radius=10, layer=layers.WG, angle=90
    )
    assert b.ports["o2"].dcplx_trans.disp == kcl.to_um(b.ports["o2"].trans.disp)
    gds_regression(b)


def test_euler_snapping(
    kcl: kf.KCLayout,
    layers: Layers,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    b = kf.factories.euler.bend_euler_factory(kcl=kcl)(
        width=1, radius=10, layer=layers.WG, angle=90
    )
    assert b.ports["o2"].dcplx_trans.disp == kcl.to_um(b.ports["o2"].trans.disp)
    gds_regression(b)


def test_unnamed_cell(
    kcl: kf.KCLayout,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    @kcl.cell
    def unnamed_cell(name: str = "a") -> kf.KCell:
        return kcl.kcell(name)

    c1 = unnamed_cell("test_unnamed_cell")
    c2 = unnamed_cell("test_unnamed_cell")
    assert c1 is c2


def test_wrong_dict(
    kcl: kf.KCLayout,
) -> None:
    with pytest.raises(kf.exceptions.CellNameError):

        @kcl.cell
        def wrong_dict_cell(a: dict[Any, Any]) -> kf.KCell:
            return kcl.kcell()

        wrong_dict_cell({(1, 0): 555, (2, 0): 10})


def test_nested_dict_list(
    kcl: kf.KCLayout,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    @kcl.cell
    def nested_list_dict(
        arg1: dict[str, list[dict[str, str | int] | int] | int],
    ) -> kf.KCell:
        return kcl.kcell()

    dl: dict[str, list[dict[str, str | int] | int] | int] = {
        "a": 5,
        "b": [5, {"c": "d", "e": 6}],
    }
    c = nested_list_dict(dl)
    assert dl == c.settings["arg1"]
    assert dl is not c.settings["arg1"]
    gds_regression(c)


def test_no_snap(
    layers: Layers,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()

    c.create_port(
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=c.kcl.find_layer(layers.WG),
    )

    p = c.ports[0]

    assert p.dcplx_trans.disp != c.kcl.to_um(p.trans.disp)
    gds_regression(c)


def test_namecollision(
    layers: Layers,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    bc = kf.factories.circular.bend_circular_factory(kcl=kcl)
    b1 = bc(width=1, radius=10.5, layer=layers.WG)
    b2 = bc(width=1, radius=10.5000005, layer=layers.WG)

    assert b1.name != b2.name
    gds_regression(b1)


def test_nested_dic(
    kcl: kf.KCLayout,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    @kcl.cell
    def recursive_dict_cell(d: dict[str, dict[str, str] | str]) -> kf.KCell:
        return kcl.kcell()

    c = recursive_dict_cell({"test": {"test2": "test3"}, "test4": "test5"})
    gds_regression(c)


def test_ports_cell(
    layers: Layers,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()
    c.create_port(
        name="o1",
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=c.kcl.find_layer(layers.WG),
    )
    assert c["o1"]
    assert "o1" in c.ports
    gds_regression(c)


def test_ports_instance(
    layers: Layers,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()
    c.create_port(
        name="o1",
        width=c.kcl.to_dbu(1),
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=c.kcl.find_layer(layers.WG),
    )
    c2 = kcl.kcell()
    ref = c2 << c
    assert c["o1"]
    assert "o1" in c.ports
    assert ref["o1"]
    assert "o1" in ref.ports
    gds_regression(c2)


def test_getter(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
    straight_factory: Callable[..., kf.KCell],
) -> None:
    c = kcl.kcell()
    c << straight_factory(width=1, length=10)
    assert c.y == 0
    assert c.dy == 0


def test_array(
    straight: kf.KCell,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()
    wg_array = c.create_inst(
        straight, a=kf.kdb.Vector(15_000, 0), b=kf.kdb.Vector(0, 3_000), na=3, nb=5
    )
    for b in range(5):
        for a in range(3):
            wg_array["o1", a, b]
            wg_array["o1", a, b]
    gds_regression(c)


def test_array_indexerror(
    straight: kf.KCell,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()
    wg_array = c.create_inst(
        straight, a=kf.kdb.Vector(15_000, 0), b=kf.kdb.Vector(0, 3_000), na=3, nb=5
    )
    regex = kf.config.logfilter.regex
    kf.config.logfilter.regex = r"^An error has been caught in function '__getitem__'"
    with pytest.raises(IndexError):
        wg_array["o1", 3, 5]
        wg_array["o1", 3, 5]
    kf.config.logfilter.regex = regex
    gds_regression(c)


def test_invalid_array(
    straight: kf.KCell,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()
    wg = c.create_inst(straight)
    regex = kf.config.logfilter.regex
    kf.config.logfilter.regex = r"^An error has been caught in function '__getitem__'"
    with pytest.raises(KeyError):
        for b in range(1):
            for a in range(1):
                wg["o1", a, b]
                wg["o1", a, b]
    kf.config.logfilter.regex = regex
    gds_regression(c)


def test_cell_decorator_error(
    kcl: kf.KCLayout,
) -> None:
    kcl2 = kf.KCLayout("decorator_test")

    @kcl.cell
    def wrong_cell() -> kf.KCell:
        return kcl2.kcell("wrong_test")

    regex = kf.config.logfilter.regex
    kf.config.logfilter.regex = (
        r"^An error has been caught in function 'wrapper_autocell'"
    )
    with pytest.raises(
        ValueError,
    ):
        wrong_cell()
    kf.config.logfilter.regex = regex


def test_info(
    kcl: kf.KCLayout,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    @kcl.cell(info={"test": 42})
    def test_info_cell(test: int) -> kf.KCell:
        return kcl.kcell()

    c = test_info_cell(42)
    assert c.info["test"] == 42
    gds_regression(c)


def test_flatten(
    kcl: kf.KCLayout,
    layers: Layers,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    c = kcl.kcell()
    _ = c << kf.factories.straight.straight_dbu_factory(kcl)(
        width=2000, length=10000, layer=layers.WG
    )
    assert len(c.insts) == 1, "c.insts should have 1 inst after adding a cell"
    c.flatten()
    assert len(c.insts) == 0, "c.insts should have 0 insts after flatten()"
    gds_regression(c)


def test_size_info(
    kcl: kf.KCLayout,
    layers: Layers,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    c = kcl.kcell()
    ref = c << kf.factories.straight.straight_dbu_factory(kcl)(
        width=2000, length=10000, layer=layers.WG
    )
    assert ref.size_info.ne[0] == 10000
    assert ref.dsize_info.ne[0] == 10
    gds_regression(c)


def test_overwrite(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    kcl = kf.KCLayout("CELL_OVERWRITE")

    @kcl.cell
    def test_overwrite_cell() -> kf.KCell:
        return kcl.kcell()

    c1 = test_overwrite_cell()

    @kcl.cell(overwrite_existing=True)  # type: ignore[no-redef]
    def test_overwrite_cell() -> kf.KCell:
        return kcl.kcell()

    c2 = test_overwrite_cell()

    assert c2 is not c1
    assert c1.destroyed()
    gds_regression(c2)


def test_layout_cache() -> None:
    kcl_write = kf.KCLayout("TEST_LAYOUT_CACHE_WRITE")
    kcl_read = kf.KCLayout("TEST_LAYOUT_CACHE_READ")

    @kcl_write.cell(basename="straight")
    def write_straight() -> kf.KCell:
        c = kcl_write.kcell()
        c.shapes(kcl_write.layer(1, 0)).insert(kf.kdb.Box(10_000, 1000))
        return c

    s_write = write_straight()
    with NamedTemporaryFile(suffix=".gds.gz") as tf:
        kcl_write.write(tf.name)
        kcl_read.read(tf.name)

    @kcl_read.cell(basename="straight", layout_cache=True)
    def read_straight() -> kf.KCell:
        c = kcl_read.kcell()
        c.shapes(kcl_read.layer(1, 0)).insert(kf.kdb.Box(5000, 1000))
        return c

    s_read = read_straight()
    assert s_write.bbox() == s_read.bbox()


def test_check_ports(
    layers: Layers,
) -> None:
    kcl = kf.KCLayout("CHECK_PORTS", infos=Layers)
    kcl.layers = kcl.layerenum_from_dict(layers=layers)

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


def test_ports_in_cells(
    kcl: kf.KCLayout,
    layers: Layers,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    kcell = kcl.kcell(name="test")
    dkcell = kcell.to_dtype()

    port = kf.Port(
        name="test",
        center=(0, 0),
        angle=0,
        cross_section=CrossSection(
            kcl,
            base=kcl.get_symmetrical_cross_section(
                CrossSectionSpec(layer=layers.WG, width=2000)
            ),
        ),
    )
    new_port = kcell.add_port(port=port, name="o1")

    assert new_port in kcell.ports
    assert new_port in dkcell.ports
    gds_regression(dkcell)


def test_kcell_attributes(
    kcl: kf.KCLayout,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    c = kcl.kcell("test_kcell_attributes")
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

    gds_regression(c)


def test_lock(
    straight: kf.KCell,
    bend90: kf.KCell,
    layers: Layers,
) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # shape insert
        with pytest.raises(RuntimeError):
            straight.shapes(kf.kdb.LayerInfo(1, 0)).insert(kf.kdb.Box(500))
        # instance insert
        with pytest.raises(RuntimeError):
            straight << bend90
        # transform
        with pytest.raises(RuntimeError):
            straight.transform(kf.kdb.Trans.R90)
        # create_vinst
        with pytest.raises(LockedError):
            straight.create_vinst(bend90)
        # create_port
        with pytest.raises(LockedError):
            straight.create_port(
                trans=kf.kdb.Trans.R0, width=1000, layer_info=layers.WG
            )
        # name setter
        with pytest.raises(LockedError):
            straight.name = "new name"


def test_kdb_getattr(
    straight: kf.KCell,
) -> None:
    straight.cell_index()

    with warnings.catch_warnings(), pytest.raises(AttributeError):
        straight.abcde  # noqa: B018


def test_cell_in_threads(
    kcl: kf.KCLayout,
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    taper_factory = kf.factories.taper.taper_factory(kcl)

    def taper() -> kf.KCell:
        return taper_factory(
            width1=5000,
            width2=1000,
            length=10000,
            layer=layers.WG,
            enclosure=wg_enc,
        )

    threads: list[threading.Thread] = []

    for _ in range(4):
        thread = threading.Thread(target=taper)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    t = taper()

    assert (
        len([c for c in kcl.tkcells.values() if c.kdb_cell.name == t.kdb_cell.name])
        == 1
    )

    gds_regression(t)


def test_to_dtype(
    kcl: kf.KCLayout,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    kcell = kcl.kcell()
    kcell.shapes(0).insert(kf.kdb.Box(0, 0, 1000, 1000))
    dkcell = kcell.to_dtype()
    assert dkcell.bbox() == kf.kdb.DBox(0, 0, 1, 1)
    gds_regression(dkcell)


def test_to_itype(kcl: kf.KCLayout) -> None:
    dkcell = kcl.dkcell()
    dkcell.shapes(0).insert(kf.kdb.DBox(0, 0, 1, 1))
    itype = dkcell.to_itype()
    assert itype.bbox() == kf.kdb.Box(0, 0, 1000, 1000)


def test_cell_default_fallback(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    kcl = kf.KCLayout("cell_default_fallback", default_cell_output_type=kf.DKCell)

    @kcl.cell
    def my_cell():  # type: ignore[no-untyped-def]  # noqa: ANN202
        return kcl.kcell()

    assert isinstance(my_cell(), kf.DKCell)
    kcl.default_cell_output_type = kf.KCell

    def my_cell():  # type: ignore[no-untyped-def,no-redef]  # noqa: ANN202
        return kcl.kcell()

    kf.layout.kcls.pop("cell_default_fallback")

    assert isinstance(my_cell(), kf.KCell)
    gds_regression(my_cell())


def test_transform(
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    c = kf.KCell()
    c2 = kf.KCell()

    inst = c << c2
    t_ = kf.kdb.Trans.M90
    inst.transform(t_)

    t = kf.kdb.Trans(x=50_000, y=10_000)

    c.transform(inst.instance, t)

    assert inst.trans == t * t_
    c.delete()
    c2.delete()


def test_factory_name(
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    cell = kf.factories.straight.straight_dbu_factory(kcl)(
        width=10, length=10, layer=layers.WG
    )
    assert cell.factory_name == "straight"


def test_prune(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def test2() -> kf.KCell:
        return kcl.kcell()

    @kcl.cell
    def test1() -> kf.KCell:
        c = kcl.kcell()
        c << test2()
        return c

    test_cell = test1()
    assert len(kcl.factories["test1"]) == 1
    assert len(kcl.factories["test2"]) == 1
    kcl.factories["test2"].prune()
    assert test_cell._destroyed()
    assert len(kcl.factories["test1"]) == 0
    assert len(kcl.factories["test2"]) == 0


def test_return_none(
    kcl: kf.KCLayout,
) -> None:
    def test_no_return() -> kf.KCell:  # type: ignore[return]
        kcl.kcell()

    def test_no_return_vk() -> kf.VKCell:  # type: ignore[return]
        kcl.vkcell()

    with pytest.raises(TypeError):
        kcl.cell()(test_no_return)()
    with pytest.raises(TypeError):
        kcl.cell()(functools.partial(test_no_return))()
    with pytest.raises(TypeError):
        kcl.vcell(test_no_return_vk)()
    with pytest.raises(TypeError):
        kcl.vcell(functools.partial(test_no_return_vk))()


def test_return_wrong_type(
    kcl: kf.KCLayout,
) -> None:
    def test_vk() -> kf.VKCell:
        return kcl.vkcell()

    def test_kc() -> kf.KCell:
        return kcl.kcell()

    with pytest.raises(TypeError):
        kcl.cell()(test_vk)()  # type: ignore[type-var]
    with pytest.raises(TypeError):
        kcl.vcell(test_kc)()  # type: ignore[type-var]

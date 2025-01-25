import klayout.db as kdb
import pytest

import kfactory as kf


@kf.cell
def unnamed_dkcell(name: str = "a") -> kf.DKCell:
    c = kf.kcl.dkcell(name)
    return c


def test_unnamed_dkcell() -> None:
    c1 = unnamed_dkcell("test_unnamed_dkcell")
    c2 = unnamed_dkcell("test_unnamed_dkcell")
    assert c1 is c2


@kf.cell
def nested_list_dict_dkcell(
    arg1: dict[str, list[dict[str, str | int] | int] | int],
) -> kf.DKCell:
    c = kf.kcl.dkcell("test_nested_list_dict_dkcell")
    return c


def test_nested_dict_list_dkcell() -> None:
    dl: dict[str, list[dict[str, str | int] | int] | int] = {
        "a": 5,
        "b": [5, {"c": "d", "e": 6}],
    }
    c = nested_list_dict_dkcell(dl)
    assert dl == c.settings["arg1"]
    assert dl is not c.settings["arg1"]


def test_dkcell_ports() -> None:
    c = kf.kcl.dkcell("test_dkcell_ports")
    assert isinstance(c.ports, kf.DPorts)
    assert list(c.ports) == []
    p = c.create_port(width=1, layer=1, center=(0, 0), angle=90)
    assert p in c.ports
    assert c.ports == [p]


def test_dkcell_locked() -> None:
    c = kf.kcl.dkcell("test_dkcell_locked")
    assert c.locked is False
    c._base_kcell.locked = True
    assert c.locked is True
    with pytest.raises(kf.kcell.LockedError):
        c.ports = []

    with pytest.raises(kf.kcell.LockedError):
        c.create_port(width=1, layer=1, center=(0, 0), angle=90)


def test_dkcell_attributes() -> None:
    c = kf.kcl.dkcell("test_dkcell_attributes")
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


if __name__ == "__main__":
    test_dkcell_attributes()
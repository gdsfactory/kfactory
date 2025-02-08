"""Tests for read and write of metadata."""

from tempfile import NamedTemporaryFile

import pytest
from conftest import Layers

import kfactory as kf


@kf.cell  # type: ignore[misc, unused-ignore]
def sample(
    s: str = "a", i: int = 3, f: float = 2.0, t: tuple[int, ...] = (1,)
) -> kf.KCell:
    with NamedTemporaryFile("a", suffix=".oas") as temp_file:
        c = kf.KCell()
        c.info["s"] = s
        c.info["i"] = i
        c.info["f"] = f
        c.info["t"] = t
        c.info["d"] = {
            "a": 1,
            "b": 2,
            "c": {
                "dbox": kf.kdb.DBox(5),
                "polygon": kf.kdb.Polygon(
                    pts=[
                        kf.kdb.Point(0, 0),
                        kf.kdb.Point(500, 0),
                        kf.kdb.Point(250, 250),
                    ]
                ),
            },
        }
        c.info["e"] = None
        c.write(temp_file.name)

        kcl2 = kf.KCLayout("TEST_META_SAMPLE")
        kcl2.read(temp_file.name)
        assert kcl2[c.name].info["d"]["c"]["dbox"] == c.info["d"]["c"]["dbox"]
        assert kcl2[c.name].info["d"]["c"]["polygon"] == c.info["d"]["c"]["polygon"]
        assert kcl2[c.name].info["e"] is None
        return c


def test_settings_and_info() -> None:
    c = sample()
    assert c.info["s"] == "a"
    assert c.info["i"] == 3
    assert c.info["f"] == 2.0
    assert c.info["t"] == (1,)
    assert c.settings["s"] == "a"
    assert c.settings["i"] == 3
    assert c.settings["f"] == 2.0
    assert c.settings["t"] == (1,)

    assert "s" in c.info
    assert "s" in c.settings

    c = sample(s="b", i=4, f=3.0, t=(2, 3))
    assert c.info["s"] == "b"
    assert c.info["i"] == 4
    assert c.info["f"] == 3.0
    assert c.info["t"] == (2, 3)
    assert c.settings["s"] == "b"
    assert c.settings["i"] == 4
    assert c.settings["f"] == 3.0
    assert c.settings["t"] == (2, 3)

    c.info["None"] = None


def test_metainfo_set(straight: kf.KCell) -> None:
    """Test autogenerated port metadata."""
    ports = straight.ports.copy()

    straight.base.kdb_cell.locked = False
    straight.set_meta_data()

    straight.ports = kf.Ports(kcl=straight.kcl)

    straight.get_meta_data()

    for i, port in enumerate(ports):
        meta_port = straight.ports[i]

        assert port.name == meta_port.name
        assert port.width == meta_port.width
        assert port.trans == meta_port.trans
        assert port.dcplx_trans == meta_port.dcplx_trans
        assert port.port_type == meta_port.port_type

    straight.delete()


def test_metainfo_read(layers: Layers, straight: kf.KCell) -> None:
    """Test whether we can read written metadata to ports."""
    with NamedTemporaryFile("a", suffix=".oas") as t:
        save = kf.save_layout_options()
        save.write_context_info = True
        straight.kcl.write(t.name)

        kcl = kf.KCLayout("TEST_META", infos=Layers)
        kcl.read(t.name)

        wg_read = kcl[straight.name]
        wg_read.get_meta_data()
        for i, port in enumerate(straight.ports):
            read_port = wg_read.ports[i]

            assert port.name == read_port.name
            assert port.trans == read_port.trans
            assert port.dcplx_trans == read_port.dcplx_trans
            assert port.port_type == read_port.port_type
            assert port.width == read_port.width
        assert wg_read.settings_units["length"] == "dbu"


def test_metainfo_read_cell(straight: kf.KCell) -> None:
    """Test whether we can read written metadata to a cell and its ports."""
    with NamedTemporaryFile("a", suffix=".oas") as t:
        save = kf.save_layout_options()
        save.write_context_info = True
        save.select_cell(straight.cell_index())
        straight.write(t.name, save_options=save)

        kcl = kf.KCLayout("TEST_META", infos=Layers)
        kcell = kcl.kcell(straight.name)
        kf.config.logfilter.regex = (
            r"KLayout <=0.28.15 \(last update 2024-02-02\) "
            "cannot read LayoutMetaInfo on 'Cell.read'. kfactory uses these extensively"
            " for ports, info, and settings. Therefore proceed at your own risk."
        )
        for cs in straight.kcl.cross_sections.cross_sections.values():
            kcl.get_symmetrical_cross_section(cs)
        kcell.read(t.name)
        kf.config.logfilter.regex = ""

        # TODO: wait for KLayout update https://github.com/KLayout/klayout/issues/1609

        # for i, port in enumerate(straight.ports):
        #     read_port = kcell.ports[i]

        #     assert port.name == read_port.name
        #     assert port.trans == read_port.trans
        #     assert port.dcplx_trans == read_port.dcplx_trans
        #     assert port.port_type == read_port.port_type
        #     assert port.width == read_port.width


def test_nometainfo_read(straight: kf.KCell) -> None:
    """Test whether we can turn of metadata writing."""
    with NamedTemporaryFile("a", suffix=".oas") as t:
        # save = kf.save_layout_options()
        # save.write_context_info = True
        straight.kcl.write(t.name, kf.save_layout_options(write_context_info=False))

        kcl = kf.KCLayout("TEST_META")
        kcl.read(t.name)

        wg_read = kcl[straight.name]
        wg_read.get_meta_data()

        assert wg_read.settings.model_dump() == {}
        assert len(wg_read.ports) == 0
        assert len(straight.ports) == 2
        assert straight.settings.model_dump() == {
            "length": 1000,
            "width": 500,
            "enclosure": "WGSTD",
            "layer": Layers().WG,
        }
        assert straight.function_name == "straight"
        assert straight.basename is None


def test_info_dump(kcl: kf.KCLayout) -> None:
    c = kcl.kcell()
    c.info = kf.Info(a="A")
    c.settings = kf.KCellSettings(a="A", c="C")
    c.info.b = "B"  # type: ignore[attr-defined, unused-ignore]
    c.info["d"] = {"a": 1, "b": 2}

    assert c.info == c.info.model_copy()
    assert c.settings == c.settings.model_copy()

    with NamedTemporaryFile("a", suffix=".oas") as t:
        # save = kf.save_layout_options()
        # save.write_context_info = True
        c.kcl.write(t.name)
        kcl = kf.KCLayout("TEST_META2")
        kcl.read(t.name)
        wg_read = kcl[c.name]
        wg_read.get_meta_data()
        assert wg_read.info == c.info
        assert wg_read.info["d"] == {"a": 1, "b": 2}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

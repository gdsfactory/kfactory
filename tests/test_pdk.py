import kfactory as kf

import pytest

from functools import partial
from tempfile import NamedTemporaryFile
from pathlib import Path
from conftest import Layers


def test_pdk(LAYER: Layers) -> None:
    pdk = kf.KCLayout("PDK")

    # class LAYER(kf.kcell.LayerEnum):
    #     kcl = kf.constant(pdk)
    #     WG = (1, 0)
    #     WGEX = (1, 1)
    class LAYERS(kf.LayerInfos):
        WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
        WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)

    pdk.infos = LAYER
    for layer in LAYER.model_dump().values():
        assert getattr(pdk.layers, layer.name).layer == layer.layer


def test_clear(LAYER: Layers) -> None:
    kcl = kf.KCLayout("CLEAR")
    kcl.layer(500, 0)
    kcl.infos = kf.LayerInfos(**{"WG": kf.kdb.LayerInfo(1, 0)})
    # kcl.layers = kcl.layerenum_from_dict(layers=LAYER)
    # kcl.layers = kcl.layerenum_from_dict(
    #     layers=kf.LayerInfos(WG=kf.kdb.LayerInfo(1, 0))
    # )
    assert kcl.layers.WG == 1
    kcl.clear(keep_layers=True)
    assert kcl.layers.WG == 0


def test_kcell_delete(LAYER: Layers) -> None:
    _kcl = kf.KCLayout("DELETE", infos=Layers)

    _kcl.layers = _kcl.layerenum_from_dict(layers=LAYER)

    s = partial(
        kf.factories.straight.straight_dbu_factory(_kcl),
        width=1000,
        length=10_000,
        layer=LAYER.WG,
    )

    s1 = s()
    _kcl.delete_cell(s1)
    assert s1._destroyed() is True

    s1 = s()
    assert s1._destroyed() is False


def test_multi_pdk(LAYER: Layers) -> None:
    base_pdk = kf.KCLayout("BASE", infos=Layers)

    doe_pdk1 = kf.KCLayout(name="DOE1", infos=Layers)
    doe_pdk2 = kf.KCLayout(name="DOE2", infos=Layers)
    assembly_pdk = kf.KCLayout(name="ASSEMBLY", infos=Layers)

    wg = kf.factories.straight.straight_dbu_factory(base_pdk)
    bend90_pdk1 = kf.factories.euler.bend_euler_factory(doe_pdk1)
    bend90_pdk2 = kf.factories.euler.bend_euler_factory(doe_pdk2)

    doe1 = doe_pdk1.kcell("DOE1")
    doe1_wg = doe1 << wg(width=1000, length=10_000, layer=LAYER.WG)
    doe_b1 = doe1 << bend90_pdk1(width=1, radius=10, layer=LAYER.WG)
    doe_b1.connect("o1", doe1_wg, "o2")

    doe1.add_port(doe1_wg.ports["o1"], name="o1")
    doe1.add_port(doe_b1.ports["o2"], name="o2")

    doe2 = doe_pdk2.kcell("DOE2")
    enc2 = kf.LayerEnclosure(
        name="enc2",
        sections=[(LAYER.WGCLAD, 0, 2000)],
        main_layer=LAYER.WG,
    )
    doe2_wg = doe2 << wg(width=1000, length=10_000, layer=LAYER.WG)
    doe_b2 = doe2 << bend90_pdk2(width=1, radius=10, layer=LAYER.WG)
    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3 = doe2 << bend90_pdk2(width=1, radius=10, layer=LAYER.WG, enclosure=enc2)

    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3.connect("o1", doe_b2, "o2")

    doe2.add_port(doe2_wg.ports["o1"], name="o1")
    doe2.add_port(doe_b3.ports["o2"], name="o2")

    assembly = assembly_pdk.kcell("TOP")
    d1 = assembly << doe1
    d2 = assembly << doe2
    d2.connect("o1", d1, "o2")


def test_multi_pdk_convert(LAYER: Layers) -> None:
    base_pdk = kf.KCLayout("BASE", infos=Layers)

    doe_pdk1 = kf.KCLayout(name="DOE1", infos=Layers)
    doe_pdk2 = kf.KCLayout(name="DOE2", infos=Layers)
    assembly_pdk = kf.KCLayout(name="ASSEMBLY", infos=Layers)

    wg = kf.factories.straight.straight_dbu_factory(base_pdk)
    bend90_pdk1 = kf.factories.euler.bend_euler_factory(doe_pdk1)
    bend90_pdk2 = kf.factories.euler.bend_euler_factory(doe_pdk2)

    doe1 = doe_pdk1.kcell("DOE1")
    doe1_wg = doe1 << wg(width=1000, length=10_000, layer=LAYER.WG)
    doe_b1 = doe1 << bend90_pdk1(width=1, radius=10, layer=LAYER.WG)
    doe_b1.connect("o1", doe1_wg, "o2")

    doe1.add_port(doe1_wg.ports["o1"], name="o1")
    doe1.add_port(doe_b1.ports["o2"], name="o2")

    doe2 = doe_pdk2.kcell("DOE2")
    enc2 = kf.LayerEnclosure(
        name="enc2",
        sections=[(LAYER.WGCLAD, 0, 2000)],
        main_layer=LAYER.WG,
    )
    doe2_wg = doe2 << wg(width=1000, length=10_000, layer=LAYER.WG)
    doe_b2 = doe2 << bend90_pdk2(width=1, radius=10, layer=LAYER.WG)
    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3 = doe2 << bend90_pdk2(width=1, radius=10, layer=LAYER.WG, enclosure=enc2)

    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3.connect("o1", doe_b2, "o2")

    doe2.add_port(doe2_wg.ports["o1"], name="o1")
    doe2.add_port(doe_b3.ports["o2"], name="o2")

    assembly = assembly_pdk.kcell("TOP")
    d1 = assembly << doe1
    d2 = assembly << doe2
    d2.connect("o1", d1, "o2")

    p = Path("ASSEMBLY.oas")
    assembly.write(p, convert_external_cells=True)
    p.unlink()


def test_multi_pdk_read_write(LAYER: Layers) -> None:
    base_pdk = kf.KCLayout("BASE", infos=Layers)

    doe_pdk1_write = kf.KCLayout(name="DOE1_WRITE", infos=Layers)
    doe_pdk2_write = kf.KCLayout(name="DOE2_WRITE", infos=Layers)
    assembly_pdk = kf.KCLayout(name="ASSEMBLY", infos=Layers)

    wg = kf.factories.straight.straight_dbu_factory(base_pdk)
    bend90_pdk1 = kf.factories.euler.bend_euler_factory(doe_pdk1_write)
    bend90_pdk2 = kf.factories.euler.bend_euler_factory(doe_pdk2_write)

    doe1 = doe_pdk1_write.kcell("DOE1")
    doe1_wg = doe1 << wg(width=1000, length=10_000, layer=LAYER.WG)
    doe_b1 = doe1 << bend90_pdk1(width=1, radius=10, layer=LAYER.WG)
    doe_b1.connect("o1", doe1_wg, "o2")

    doe1.add_port(doe1_wg.ports["o1"], name="o1")
    doe1.add_port(doe_b1.ports["o2"], name="o2")

    doe2 = doe_pdk2_write.kcell("DOE2")
    enc2 = kf.LayerEnclosure(
        name="enc2",
        sections=[(LAYER.WGCLAD, 0, 2000)],
        main_layer=LAYER.WG,
    )
    doe2_wg = doe2 << wg(width=1000, length=10_000, layer=LAYER.WG)
    doe_b2 = doe2 << bend90_pdk2(width=1, radius=10, layer=LAYER.WG)
    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3 = doe2 << bend90_pdk2(width=1, radius=10, layer=LAYER.WG, enclosure=enc2)

    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3.connect("o1", doe_b2, "o2")

    doe2.add_port(doe2_wg.ports["o1"], name="o1")
    doe2.add_port(doe_b3.ports["o2"], name="o2")

    doe_pdk1_read = kf.KCLayout("DOE1_READ", infos=Layers)
    doe_pdk2_read = kf.KCLayout("DOE2_READ", infos=Layers)

    with NamedTemporaryFile(suffix=".gds") as tf:
        doe_pdk1_write.write(tf.name)
        doe_pdk1_read.read(tf.name)
    with NamedTemporaryFile(suffix=".gds") as tf:
        doe_pdk2_write.write(tf.name)
        doe_pdk2_read.read(tf.name)

    assembly = assembly_pdk.kcell("TOP")
    d1 = assembly << doe_pdk1_read[doe1.name]
    d2 = assembly << doe_pdk2_read[doe2.name]
    d2.connect("o1", d1, "o2")


def test_merge_read_shapes(LAYER: Layers) -> None:
    with pytest.raises(kf.kcell.MergeError):
        kcl_1 = kf.KCLayout("MERGE_BASE", infos=Layers)
        s_base = kf.factories.straight.straight_dbu_factory(kcl_1)(
            width=1000, length=10_000, layer=LAYER.WG
        )
        s_copy = s_base.dup()
        s_copy.name = "Straight"

        kcl_2 = kf.KCLayout("MERGE_READ", infos=Layers)
        kcl_2.layers = kcl_2.layerenum_from_dict(layers=LAYER)
        s_base = kf.factories.straight.straight_dbu_factory(kcl_2)(
            width=1100, length=10_000, layer=LAYER.WG
        )
        s_copy = s_base.dup()
        s_copy.name = "Straight"

        kcl_2.write("MERGE_READ.oas")
        kf.config.logfilter.regex = "(?:Found poly)|(?:MetaInfo 'kfactory:)"
        kcl_1.read("MERGE_READ.oas")
        kf.config.logfilter.regex = None
    Path("MERGE_READ.oas").unlink(missing_ok=True)


def test_merge_read_instances(LAYER: Layers) -> None:
    with pytest.raises(kf.kcell.MergeError):
        kcl_1 = kf.KCLayout("MERGE_BASE", infos=Layers)
        kcl_1.layers = kcl_1.layerenum_from_dict(layers=LAYER)

        enc1 = kf.LayerEnclosure(sections=[(LAYER.WG, 0, 200)], name="CLAD")
        s_base = kf.factories.straight.straight_dbu_factory(kcl_1)(
            width=1000, length=10_000, layer=LAYER.WGEXCLUDE, enclosure=enc1
        )
        s_copy = kcl_1.kcell("Straight")
        s_copy << s_base

        kcl_2 = kf.KCLayout("MERGE_READ", infos=Layers)
        kcl_2.layers = kcl_2.layerenum_from_dict(layers=LAYER)
        enc2 = kf.LayerEnclosure(sections=[(LAYER.WG, 0, 200)], name="CLAD")
        s_base = kf.factories.straight.straight_dbu_factory(kcl_2)(
            width=1000, length=10_000, layer=LAYER.WGEXCLUDE, enclosure=enc2
        )
        s_copy = kcl_2.kcell("Straight")
        copy = s_copy << s_base
        copy.movey(-500)

        kcl_2.write("MERGE_READ.oas")
        kf.config.logfilter.regex = "Found instance"
        kcl_1.read("MERGE_READ.oas")
        kf.config.logfilter.regex = None
    Path("MERGE_READ.oas").unlink(missing_ok=True)


def test_merge_properties() -> None:
    with pytest.raises(kf.kcell.MergeError):
        kcl_1 = kf.KCLayout("MERGE_BASE", infos=Layers)
        c = kcl_1.kcell("properties_cell")
        c.info["test_prop"] = "kcl_1"

        kcl_2 = kf.KCLayout("MERGE_READ", infos=Layers)
        c = kcl_2.kcell("properties_cell")
        c.info["test_prop"] = "kcl_2"

        kcl_2.write("MERGE_READ.oas")
        kf.config.logfilter.regex = (
            "MetaInfo 'kfactory:info:test_prop' exists in cells which are to be merged "
            "in Layout MERGE_BASE. But their values differ: 'MERGE_BASE': 'kcl_1', "
            "'MERGE_READ': 'kcl_2'"
        )
        kcl_1.read("MERGE_READ.oas")
        kf.config.logfilter.regex = None
    Path("MERGE_READ.oas").unlink(missing_ok=True)


def test_pdk_cell_infosettings(straight: kf.KCell, LAYER: Layers) -> None:
    kcl = kf.KCLayout("INFOSETTINGS", infos=Layers)
    c = kcl.kcell()
    _wg = c << straight
    _wg.cell
    assert _wg.cell.settings == straight.settings
    assert _wg.cell.info == straight.info

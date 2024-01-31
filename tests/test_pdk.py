import kfactory as kf

import pytest

from functools import partial
from tempfile import NamedTemporaryFile
from pathlib import Path


def test_pdk() -> None:
    pdk = kf.KCLayout("PDK")

    class LAYER(kf.LayerEnum):
        kcl = kf.constant(pdk)
        WG = (1, 0)
        WGEX = (1, 1)

    pdk.layers = LAYER
    for name, layer in LAYER.__members__.items():
        assert getattr(pdk.layers, name) == layer


def test_clear() -> None:
    kcl = kf.KCLayout("CLEAR")
    layer = kcl.layer(500, 0)
    kcl.layers = kf.kcell.layerenum_from_dict(kcl=kcl, layers={"WG": (1, 0)})
    assert kcl.layers.WG == 1
    kcl.clear(keep_layers=True)
    assert kcl.layers.WG == 0


def test_kcell_delete() -> None:
    _kcl = kf.KCLayout("DELETE")

    class LAYER(kf.LayerEnum):
        kcl = kf.constant(_kcl)
        WG = (1, 0)

    s = partial(kf.cells.dbu.Straight(_kcl), width=1000, length=10_000, layer=LAYER.WG)

    s1 = s()
    _kcl.delete_cell(s1)
    assert s1._destroyed() == True

    s1 = s()
    assert s1._destroyed() == False


def test_multi_pdk() -> None:
    base_pdk = kf.KCLayout("BASE")

    base_pdk.layers = base_pdk.layerenum_from_dict(
        name="LAYER", layers=dict(WG=(1, 0), WGCLAD=(111, 0))
    )

    doe_pdk1 = kf.KCLayout(name="DOE1", base_kcl=base_pdk)
    doe_pdk2 = kf.KCLayout(name="DOE2", base_kcl=base_pdk)
    assembly_pdk = kf.KCLayout(name="ASSEMBLY", base_kcl=base_pdk)

    wg = kf.cells.dbu.Straight(base_pdk)
    bend90_pdk1 = kf.cells.euler.BendEuler(doe_pdk1)
    bend90_pdk2 = kf.cells.euler.BendEuler(doe_pdk2)

    doe1 = doe_pdk1.kcell("DOE1")
    doe1_wg = doe1 << wg(width=1000, length=10_000, layer=base_pdk.layers.WG)
    doe_b1 = doe1 << bend90_pdk1(width=1, radius=10, layer=doe_pdk1.layers.WG)
    doe_b1.connect("o1", doe1_wg, "o2")

    doe1.add_port(doe1_wg.ports["o1"], name="o1")
    doe1.add_port(doe_b1.ports["o2"], name="o2")

    doe2 = doe_pdk2.kcell("DOE2")
    enc2 = kf.LayerEnclosure(
        name="enc2",
        sections=[(doe_pdk2.layers.WGCLAD, 0, 2000)],
        main_layer=doe_pdk2.layers.WG,
    )
    doe2_wg = doe2 << wg(width=1000, length=10_000, layer=base_pdk.layers.WG)
    doe_b2 = doe2 << bend90_pdk2(width=1, radius=10, layer=doe_pdk2.layers.WG)
    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3 = doe2 << bend90_pdk2(
        width=1, radius=10, layer=doe_pdk2.layers.WG, enclosure=enc2
    )

    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3.connect("o1", doe_b2, "o2")

    doe2.add_port(doe2_wg.ports["o1"], name="o1")
    doe2.add_port(doe_b3.ports["o2"], name="o2")

    assembly = assembly_pdk.kcell("TOP")
    d1 = assembly << doe1
    d2 = assembly << doe2
    d2.connect("o1", d1, "o2")

    assembly.show()


def test_multi_pdk_convert() -> None:
    base_pdk = kf.KCLayout("BASE")

    base_pdk.layers = base_pdk.layerenum_from_dict(
        name="LAYER", layers=dict(WG=(1, 0), WGCLAD=(111, 0))
    )

    doe_pdk1 = kf.KCLayout(name="DOE1", base_kcl=base_pdk)
    doe_pdk2 = kf.KCLayout(name="DOE2", base_kcl=base_pdk)
    assembly_pdk = kf.KCLayout(name="ASSEMBLY", base_kcl=base_pdk)

    wg = kf.cells.dbu.Straight(base_pdk)
    bend90_pdk1 = kf.cells.euler.BendEuler(doe_pdk1)
    bend90_pdk2 = kf.cells.euler.BendEuler(doe_pdk2)

    doe1 = doe_pdk1.kcell("DOE1")
    doe1_wg = doe1 << wg(width=1000, length=10_000, layer=base_pdk.layers.WG)
    doe_b1 = doe1 << bend90_pdk1(width=1, radius=10, layer=doe_pdk1.layers.WG)
    doe_b1.connect("o1", doe1_wg, "o2")

    doe1.add_port(doe1_wg.ports["o1"], name="o1")
    doe1.add_port(doe_b1.ports["o2"], name="o2")

    doe2 = doe_pdk2.kcell("DOE2")
    enc2 = kf.LayerEnclosure(
        name="enc2",
        sections=[(doe_pdk2.layers.WGCLAD, 0, 2000)],
        main_layer=doe_pdk2.layers.WG,
    )
    doe2_wg = doe2 << wg(width=1000, length=10_000, layer=base_pdk.layers.WG)
    doe_b2 = doe2 << bend90_pdk2(width=1, radius=10, layer=doe_pdk2.layers.WG)
    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3 = doe2 << bend90_pdk2(
        width=1, radius=10, layer=doe_pdk2.layers.WG, enclosure=enc2
    )

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
    kf.show(p)
    p.unlink()


def test_multi_pdk_read_write() -> None:
    base_pdk = kf.KCLayout("BASE")

    base_pdk.layers = base_pdk.layerenum_from_dict(
        name="LAYER", layers=dict(WG=(1, 0), WGCLAD=(111, 0))
    )

    doe_pdk1_write = kf.KCLayout(name="DOE1_WRITE", base_kcl=base_pdk)
    doe_pdk2_write = kf.KCLayout(name="DOE2_WRITE", base_kcl=base_pdk)
    assembly_pdk = kf.KCLayout(name="ASSEMBLY", base_kcl=base_pdk)

    wg = kf.cells.dbu.Straight(base_pdk)
    bend90_pdk1 = kf.cells.euler.BendEuler(doe_pdk1_write)
    bend90_pdk2 = kf.cells.euler.BendEuler(doe_pdk2_write)

    doe1 = doe_pdk1_write.kcell("DOE1")
    doe1_wg = doe1 << wg(width=1000, length=10_000, layer=base_pdk.layers.WG)
    doe_b1 = doe1 << bend90_pdk1(width=1, radius=10, layer=doe_pdk1_write.layers.WG)
    doe_b1.connect("o1", doe1_wg, "o2")

    doe1.add_port(doe1_wg.ports["o1"], name="o1")
    doe1.add_port(doe_b1.ports["o2"], name="o2")

    doe2 = doe_pdk2_write.kcell("DOE2")
    enc2 = kf.LayerEnclosure(
        name="enc2",
        sections=[(doe_pdk2_write.layers.WGCLAD, 0, 2000)],
        main_layer=doe_pdk2_write.layers.WG,
    )
    doe2_wg = doe2 << wg(width=1000, length=10_000, layer=base_pdk.layers.WG)
    doe_b2 = doe2 << bend90_pdk2(width=1, radius=10, layer=doe_pdk2_write.layers.WG)
    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3 = doe2 << bend90_pdk2(
        width=1, radius=10, layer=doe_pdk2_write.layers.WG, enclosure=enc2
    )

    doe_b2.connect("o1", doe2_wg, "o2")
    doe_b3.connect("o1", doe_b2, "o2")

    doe2.add_port(doe2_wg.ports["o1"], name="o1")
    doe2.add_port(doe_b3.ports["o2"], name="o2")

    doe_pdk1_read = kf.KCLayout("DOE1_READ")
    doe_pdk2_read = kf.KCLayout("DOE2_READ")

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

    assembly.show()


def test_merge_read_shapes() -> None:
    with pytest.raises(kf.kcell.MergeError):
        kcl_1 = kf.KCLayout("MERGE_BASE")
        s_base = kf.cells.dbu.Straight(kcl_1)(
            width=1000, length=10_000, layer=kcl_1.layer(1, 0)
        )
        s_copy = s_base.dup()
        s_copy.name = "Straight"

        kcl_2 = kf.KCLayout("MERGE_READ")
        s_base = kf.cells.dbu.Straight(kcl_2)(
            width=1100, length=10_000, layer=kcl_2.layer(1, 0)
        )
        s_copy = s_base.dup()
        s_copy.name = "Straight"

        kcl_2.write("MERGE_READ.oas")
        kf.config.logfilter.regex = "(?:Found poly)|(?:MetaInfo 'kfactory:)"
        kcl_1.read("MERGE_READ.oas")
        kf.config.logfilter.regex = None
    Path("MERGE_READ.oas").unlink(missing_ok=True)


def test_merge_read_instances() -> None:
    with pytest.raises(kf.kcell.MergeError):
        kcl_1 = kf.KCLayout("MERGE_BASE")
        enc1 = kf.LayerEnclosure(sections=[(kcl_1.layer(2, 0), 0, 200)], name="CLAD")
        s_base = kf.cells.dbu.Straight(kcl_1)(
            width=1000, length=10_000, layer=kcl_1.layer(1, 0), enclosure=enc1
        )
        s_copy = kcl_1.kcell("Straight")
        s_copy << s_base

        kcl_2 = kf.KCLayout("MERGE_READ")
        enc2 = kf.LayerEnclosure(sections=[(kcl_2.layer(2, 0), 0, 200)], name="CLAD")
        s_base = kf.cells.dbu.Straight(kcl_2)(
            width=1000, length=10_000, layer=kcl_2.layer(1, 0), enclosure=enc2
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
        kcl_1 = kf.KCLayout("MERGE_BASE")
        c = kcl_1.kcell("properties_cell")
        c.info["test_prop"] = "kcl_1"

        kcl_2 = kf.KCLayout("MERGE_READ")
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

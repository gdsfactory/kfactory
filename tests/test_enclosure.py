from pathlib import Path

import pytest

import kfactory as kf
from tests.conftest import Layers


@kf.cell
def mmi_enc(layer: kf.kdb.LayerInfo, enclosure: kf.LayerEnclosure) -> kf.KCell:
    c = kf.KCell()
    li = c.kcl.find_layer(layer)
    c.shapes(li).insert(kf.kdb.Box(-10000, -6000, 10000, 6000))

    taper = kf.kdb.Polygon(
        [
            kf.kdb.Point(0, -500),
            kf.kdb.Point(0, 500),
            kf.kdb.Point(2000, 250),
            kf.kdb.Point(2000, -250),
        ]
    )

    for t in [
        kf.kdb.Trans(0, False, 10000, -4000),
        kf.kdb.Trans(0, False, 10000, 4000),
        kf.kdb.Trans(2, False, -10000, -4000),
        kf.kdb.Trans(2, False, -10000, 4000),
    ]:
        c.shapes(li).insert(taper.transformed(t))

    enclosure.apply_minkowski_enc(c, layer)

    return c


def test_enclosure(layers: Layers) -> None:
    kf.LayerEnclosure([(layers.WG, 500, -250)])


def test_enc(layers: Layers, wg_enc: kf.LayerEnclosure) -> None:
    mmi_enc(layers.WG, wg_enc)


def test_neg_enc(layers: Layers) -> None:
    enc = kf.LayerEnclosure([(layers.WGCLAD, -1500, 1000)])

    mmi_enc(layers.WG, enc)


def test_layer_multi_enc(layers: Layers) -> None:
    enc = kf.LayerEnclosure(
        [
            (layers.WGCLAD, -5000, -5400),
            (layers.WGCLAD, -4000, -3900),
            (layers.WGCLAD, -100, 100),
            (layers.WGCLAD, -500, -400),
        ]
    )
    mmi_enc(layers.WG, enc)


def test_bbox_enc(layers: Layers) -> None:
    enc = kf.LayerEnclosure(
        [
            (layers.WGCLAD, -5000, -5400),
            (layers.WGCLAD, -4000, -3900),
            (layers.WGCLAD, -100, 100),
            (layers.WGCLAD, -500, -400),
        ],
        main_layer=layers.WG,
    )
    c = kf.KCell(name="BBOX_ENC")
    enc.apply_bbox(c, ref=layers.WG)


def test_layer_merge_enc(layers: Layers) -> None:
    enc = kf.LayerEnclosure(
        [
            (layers.WGCLAD, -5000, -3000),
            (layers.WGCLAD, -4000, -2000),
            (layers.WGCLAD, -2000, 1000),
        ]
    )
    mmi_enc(layers.WG, enc)


def test_um_enclosure(layers: Layers) -> None:
    kcl = kf.KCLayout("TEST_UM_ENCLOSURE")
    enc = kf.LayerEnclosure(
        [
            (layers.WGCLAD, -5000, -3000),
            (layers.WGCLAD, -4000, -2000),
            (layers.WGCLAD, -2000, 1000),
        ],
        kcl=kcl,
    )

    enc_um = kf.LayerEnclosure(
        dsections=[
            (layers.WGCLAD, -5, -3),
            (layers.WGCLAD, -4, -2),
            (layers.WGCLAD, -2, 1),
        ],
        kcl=kcl,
    )

    assert enc == enc_um


def test_um_enclosure_nodbu(layers: Layers) -> None:
    """When defining um sections, kcl must be defined."""
    with pytest.raises(AssertionError):
        kf.LayerEnclosure(
            dsections=[
                (layers.WGCLAD, -5, -3),
                (layers.WGCLAD, -4, -2),
                (layers.WGCLAD, -2, 1),
            ]
        )


def test_bbox_sections_gds_roundtrip(
    kcl: kf.KCLayout, layers: Layers, tmp_path: Path
) -> None:
    """``bbox_sections`` survive a GDS metadata round-trip.

    Regression: the enclosure serializer used to emit only
    ``name``/``sections``/``main_layer``, so bbox sections never reached the file.
    """
    enc = kcl.get_enclosure(
        kf.LayerEnclosure(
            sections=[(layers.WGCLAD, 3000)],
            main_layer=layers.WG,
            bbox_sections=[(layers.FILL1, 2000)],
            name="enc_bbox",
        )
    )
    xs = kcl.get_symmetrical_cross_section(
        kf.SymmetricalCrossSection(width=500, enclosure=enc, name="xs_bbox")
    )
    c = kcl.kcell("bbox_sections_top")
    c.shapes(kcl.find_layer(layers.WG)).insert(kf.kdb.Box(0, 0, 1000, 500))

    path = tmp_path / "bbox_sections.gds"
    kcl.write(path)
    kcl_r = kf.KCLayout("BBOX_SECTIONS_R", infos=Layers)
    kcl_r.read(path)

    restored_enc = kcl_r.get_enclosure("enc_bbox")
    assert restored_enc.bbox_sections == {layers.FILL1: 2000}
    assert restored_enc == enc

    restored_xs = kcl_r.get_symmetrical_cross_section("xs_bbox")
    assert restored_xs.bbox_sections == {layers.FILL1: 2000}
    assert restored_xs == xs


def test_bbox_sections_dtype_roundtrip(kcl: kf.KCLayout, layers: Layers) -> None:
    """``bbox_sections`` survive the dbu -> um -> dbu conversion.

    Regression: `DLayerEnclosure` had no `bbox_sections` field, so `to_dtype`
    silently dropped them.
    """
    enc = kf.LayerEnclosure(
        sections=[(layers.WGCLAD, 3000)],
        main_layer=layers.WG,
        bbox_sections=[(layers.FILL1, 2000), (layers.FILL2, -500)],
        name="enc_dtype_bbox",
    )

    denc = enc.to_dtype(kcl)
    assert denc.bbox_sections == [(layers.FILL1, 2.0), (layers.FILL2, -0.5)]
    assert denc.to_itype(kcl) == enc


def test_bbox_sections_dbbox_sections_equivalent(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    """``dbbox_sections`` is the um based equivalent of ``bbox_sections``."""
    enc = kf.LayerEnclosure(
        sections=[(layers.WGCLAD, 3000)],
        main_layer=layers.WG,
        bbox_sections=[(layers.FILL1, 2000)],
        kcl=kcl,
    )
    enc_um = kf.LayerEnclosure(
        sections=[(layers.WGCLAD, 3000)],
        main_layer=layers.WG,
        dbbox_sections=[(layers.FILL1, 2.0)],
        kcl=kcl,
    )

    assert enc == enc_um


def test_dbbox_sections_nodbu(layers: Layers) -> None:
    """When defining um bbox sections, kcl must be defined."""
    with pytest.raises(AssertionError):
        kf.LayerEnclosure(main_layer=layers.WG, dbbox_sections=[(layers.FILL1, 2.0)])


def test_bbox_sections_spec_roundtrip(kcl: kf.KCLayout, layers: Layers) -> None:
    """A dumped enclosure fed back through ``get_enclosure`` keeps its bbox sections.

    Regression: `LayerEnclosureSpec` had no `bbox_sections` key and the dict
    branches of `get_enclosure` dropped it.
    """
    enc = kf.LayerEnclosure(
        sections=[(layers.WGCLAD, 3000)],
        main_layer=layers.WG,
        bbox_sections=[(layers.FILL1, 2000)],
        name="enc_spec_bbox",
    )

    restored = kcl.get_enclosure(enc.model_dump())
    assert restored.bbox_sections == {layers.FILL1: 2000}
    assert restored == enc


def test_bbox_sections_spec_um(kcl: kf.KCLayout, layers: Layers) -> None:
    """A um based spec can define bbox sections via ``dbbox_sections``."""
    spec: kf.enclosure.LayerEnclosureSpec = {
        "main_layer": layers.WG,
        "dsections": [(layers.WGCLAD, 3.0)],
        "dbbox_sections": [(layers.FILL1, 2.0)],
        "name": "enc_spec_um_bbox",
    }

    enc = kcl.get_enclosure(spec)
    assert enc.bbox_sections == {layers.FILL1: 2000}


def test_kcell_layer_enclosures_spec_bbox_sections(layers: Layers) -> None:
    """``KCellLayerEnclosures`` specs keep bbox sections, and reject um specs."""
    collection = kf.enclosure.KCellLayerEnclosures(enclosures=[])

    enc = collection.get_enclosure(
        {
            "main_layer": layers.WG,
            "sections": [(layers.WGCLAD, 3000)],
            "bbox_sections": [(layers.FILL1, 2000)],
        }
    )
    assert enc.bbox_sections == {layers.FILL1: 2000}
    assert collection.enclosures == [enc]

    with pytest.raises(ValueError, match="cannot be converted without"):
        collection.get_enclosure(
            {
                "main_layer": layers.WG,
                "dbbox_sections": [(layers.FILL1, 2.0)],
            }
        )


def test_create_layer_enclosure_bbox_sections(kcl: kf.KCLayout, layers: Layers) -> None:
    """``KCLayout.create_layer_enclosure`` can express bbox sections."""
    enc = kcl.create_layer_enclosure(
        sections=[(layers.WGCLAD, 3000)],
        main_layer=layers.WG,
        name="enc_created_bbox",
        bbox_sections=[(layers.FILL1, 2000)],
    )
    assert enc.bbox_sections == {layers.FILL1: 2000}
    assert kcl.layer_enclosures["enc_created_bbox"] is enc

    enc_um = kcl.create_layer_enclosure(
        dsections=[(layers.WGCLAD, 3.0)],
        main_layer=layers.WG,
        name="enc_created_bbox_um",
        dbbox_sections=[(layers.FILL1, 2.0)],
    )
    assert enc_um.bbox_sections == {layers.FILL1: 2000}


def test_bbox_sections_eq_and_hash_agree(layers: Layers) -> None:
    """Enclosures differing only in ``bbox_sections`` are unequal and hash apart."""
    without_bbox = kf.LayerEnclosure(
        sections=[(layers.WGCLAD, 3000)], main_layer=layers.WG, name="enc_hash"
    )
    with_bbox = kf.LayerEnclosure(
        sections=[(layers.WGCLAD, 3000)],
        main_layer=layers.WG,
        bbox_sections=[(layers.FILL1, 2000)],
        name="enc_hash",
    )

    assert without_bbox != with_bbox
    assert hash(without_bbox) != hash(with_bbox)


def test_pdkenclosure(layers: Layers, straight_blank: kf.KCell) -> None:
    c = kf.KCell(name="wg_slab")

    wg_box = kf.kdb.Box(10000, 500)
    c.shapes(c.kcl.find_layer(layers.WG)).insert(wg_box)
    c.shapes(c.kcl.find_layer(layers.WGCLAD)).insert(wg_box.enlarged(0, 2500))
    c.create_port(
        name="o1",
        trans=kf.kdb.Trans(0, False, wg_box.right, 0),
        width=wg_box.height(),
        layer=c.kcl.find_layer(layers.WG),
    )
    c.create_port(
        name="o2",
        trans=kf.kdb.Trans(2, False, wg_box.left, 0),
        width=wg_box.height(),
        layer=c.kcl.find_layer(layers.WG),
    )

    enc1 = kf.LayerEnclosure(
        sections=[
            (layers.WGEX, 1000),
        ],
        name="WGEX",
        main_layer=layers.WG,
    )

    enc2 = kf.LayerEnclosure(
        name="CLADEX",
        main_layer=layers.WGCLAD,
        sections=[(layers.WGEX, 1000), (layers.WGCLADEX, 2000)],
    )

    pdkenc = kf.KCellEnclosure(enclosures=[enc1, enc2])

    pdkenc.apply_minkowski_tiled(c, carve_out_ports=True)

    port_wg_ex = kf.kdb.Region()
    box = kf.kdb.Polygon(
        kf.kdb.Box(
            0,
            -wg_box.height() // 2 - 1000,
            wg_box.height() // 2 + 1000,
            wg_box.height() // 2 + 1000,
        )
    )
    for port in c.ports:
        port_wg_ex.insert(box.transformed(port.trans))

    port_wg_ex.merge()

    assert (
        kf.kdb.Region(c.shapes(c.kcl.find_layer(layers.WGEX))) & port_wg_ex
    ).is_empty()
    assert (
        (kf.kdb.Region(c.shapes(c.kcl.find_layer(layers.WGCLADEX))) & port_wg_ex)
        - port_wg_ex
    ).is_empty()


def test_extrude_path_cross_section_symmetric_matches_legacy(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    """A symmetric cross section extrudes identically to the legacy width path."""
    enc = kcl.get_enclosure(
        kf.LayerEnclosure(
            sections=[(layers.WGCLAD, 0, 2000)], main_layer=layers.WG, name="enc_eq"
        )
    )
    xs = kcl.get_symmetrical_cross_section(
        kf.SymmetricalCrossSection(width=1000, enclosure=enc, name="wg_eq")
    )
    path = [kf.kdb.DPoint(0, 0), kf.kdb.DPoint(10, 0), kf.kdb.DPoint(10, 10)]

    c_cs = kcl.kcell("cs_extrude")
    kf.enclosure.extrude_path_cross_section(c_cs, path, xs)
    c_legacy = kcl.kcell("legacy_extrude")
    kf.enclosure.extrude_path(c_legacy, layers.WG, path, kcl.to_um(1000), enc)

    for layer in (layers.WG, layers.WGCLAD):
        li = kcl.layer(layer)
        xor = kf.kdb.Region(c_cs.shapes(li)) ^ kf.kdb.Region(c_legacy.shapes(li))
        assert xor.is_empty()


def test_extrude_path_cross_section_asymmetric(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    """An asymmetric cross section extrudes one signed band per strip, per layer."""
    acs = kcl.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layers.WG,
            section_min=-200,
            section_max=300,
            sections=(
                kf.CrossSectionLayer(
                    layer=layers.WGCLAD, section_min=-100, section_max=900
                ),
            ),
            name="asym_extrude",
        )
    )
    c = kcl.kcell("asym_extrude_cell")
    length = 10.0
    kf.enclosure.extrude_path_cross_section(
        c, [kf.kdb.DPoint(0, 0), kf.kdb.DPoint(length, 0)], acs
    )
    length_dbu = kcl.to_dbu(length)

    # main strip on WG keeps its signed offsets [-200, 300]
    assert kf.kdb.Region(c.shapes(kcl.layer(layers.WG))).bbox() == kf.kdb.Box(
        0, -200, length_dbu, 300
    )
    # aux strip on WGCLAD keeps its signed offsets [-100, 900]
    assert kf.kdb.Region(c.shapes(kcl.layer(layers.WGCLAD))).bbox() == kf.kdb.Box(
        0, -100, length_dbu, 900
    )

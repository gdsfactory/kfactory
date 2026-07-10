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


def test_extrude_path_points_long_path_matches_explicit_end_angle() -> None:
    path = [kf.kdb.DPoint(float(i), 0.0) for i in range(63)] + [
        kf.kdb.DPoint(63.0, 1.0),
        kf.kdb.DPoint(64.0, 2.0),
    ]
    width = 2.0
    end_angle = 45.0

    implicit_top, implicit_bot = kf.enclosure.extrude_path_points(path, width)
    explicit_top, explicit_bot = kf.enclosure.extrude_path_points(
        path, width, end_angle=end_angle
    )

    assert implicit_top[-1] == explicit_top[-1]
    assert implicit_bot[-1] == explicit_bot[-1]

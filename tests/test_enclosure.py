import kfactory as kf
import pytest


@kf.cell
def mmi_enc(layer: kf.kcell.LayerEnum, enclosure: kf.LayerEnclosure) -> kf.KCell:
    c = kf.KCell()
    c.shapes(layer).insert(kf.kdb.Box(-10000, -6000, 10000, 6000))

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
        c.shapes(layer).insert(taper.transformed(t))

    enclosure.apply_minkowski_enc(c, layer)

    return c


def test_enclosure(LAYER: kf.LayerEnum) -> None:
    enc = kf.LayerEnclosure([(LAYER.WG, 500, -250)])


def test_enc(LAYER: kf.LayerEnum, wg_enc: kf.LayerEnclosure) -> None:
    enc = wg_enc

    c = mmi_enc(LAYER.WG, wg_enc)
    c.show()


def test_neg_enc(LAYER: kf.LayerEnum) -> None:
    enc = kf.LayerEnclosure([(LAYER.WGCLAD, -1500, 1000)])

    c = mmi_enc(LAYER.WG, enc)
    c.show()


def test_layer_multi_enc(LAYER: kf.LayerEnum) -> None:
    enc = kf.LayerEnclosure(
        [
            (LAYER.WGCLAD, -5000, -5400),
            (LAYER.WGCLAD, -4000, -3900),
            (LAYER.WGCLAD, -100, 100),
            (LAYER.WGCLAD, -500, -400),
        ]
    )
    c = mmi_enc(LAYER.WG, enc)
    c.show()


def test_layer_merge_enc(LAYER: kf.LayerEnum) -> None:
    enc = kf.LayerEnclosure(
        [
            (LAYER.WGCLAD, -5000, -3000),
            (LAYER.WGCLAD, -4000, -2000),
            (LAYER.WGCLAD, -2000, 1000),
        ]
    )
    c = mmi_enc(LAYER.WG, enc)
    c.show()


def test_um_enclosure(LAYER: kf.LayerEnum) -> None:
    enc = kf.LayerEnclosure(
        [
            (LAYER.WGCLAD, -5000, -3000),
            (LAYER.WGCLAD, -4000, -2000),
            (LAYER.WGCLAD, -2000, 1000),
        ],
        kcl=kf.kcl,
    )

    enc_um = kf.LayerEnclosure(
        dsections=[
            (LAYER.WGCLAD, -5, -3),
            (LAYER.WGCLAD, -4, -2),
            (LAYER.WGCLAD, -2, 1),
        ],
        kcl=kf.kcl,
    )

    assert enc == enc_um


def test_um_enclosure_nodbu(LAYER: kf.LayerEnum) -> None:
    """When defining um sections, kcl must be defined."""
    with pytest.raises(AssertionError) as ae_info:  # noqa: F481
        kf.LayerEnclosure(
            dsections=[
                (LAYER.WGCLAD, -5, -3),
                (LAYER.WGCLAD, -4, -2),
                (LAYER.WGCLAD, -2, 1),
            ]
        )


def test_pdkenclosure(LAYER: kf.LayerEnum, straight_blank: kf.KCell) -> None:
    c = kf.KCell("wg_slab")

    wg_box = kf.kdb.Box(10000, 500)
    c.shapes(LAYER.WG).insert(wg_box)
    c.shapes(LAYER.WGCLAD).insert(wg_box.enlarged(0, 2500))
    c.create_port(
        trans=kf.kdb.Trans(0, False, wg_box.right, 0),
        width=wg_box.height(),
        layer=LAYER.WG,
    )
    c.create_port(
        trans=kf.kdb.Trans(2, False, wg_box.left, 0),
        width=wg_box.height(),
        layer=LAYER.WG,
    )

    enc1 = kf.LayerEnclosure(
        sections=[
            (LAYER.WGEXCLUDE, 1000),
        ],
        name="WGEX",
        main_layer=LAYER.WG,
    )

    enc2 = kf.LayerEnclosure(
        name="CLADEX",
        main_layer=LAYER.WGCLAD,
        sections=[(LAYER.WGEXCLUDE, 1000), (LAYER.WGCLADEXCLUDE, 2000)],
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

    assert (kf.kdb.Region(c.shapes(LAYER.WGEXCLUDE)) & port_wg_ex).is_empty()
    assert (
        (kf.kdb.Region(c.shapes(LAYER.WGCLADEXCLUDE)) & port_wg_ex) - port_wg_ex
    ).is_empty()

    c.show()

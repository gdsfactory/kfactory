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
        trans=kf.kdb.Trans(0, False, wg_box.right, 0),
        width=wg_box.height(),
        layer=c.kcl.find_layer(layers.WG),
    )
    c.create_port(
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

    c.show()

    assert (
        kf.kdb.Region(c.shapes(c.kcl.find_layer(layers.WGEX))) & port_wg_ex
    ).is_empty()
    assert (
        (kf.kdb.Region(c.shapes(c.kcl.find_layer(layers.WGCLADEX))) & port_wg_ex)
        - port_wg_ex
    ).is_empty()

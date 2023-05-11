import kfactory as kf
import pytest


@kf.cell
def mmi_enc(layer: kf.kcell.LayerEnum, enclosure: kf.utils.Enclosure):
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


def test_enclosure(LAYER):
    enc = kf.utils.Enclosure([(LAYER.WG, 500, -250)])


def test_enc(LAYER, wg_enc):
    enc = wg_enc

    mmi_enc(LAYER.WG, wg_enc)


def test_neg_enc(LAYER):
    enc = kf.utils.Enclosure([(LAYER.WGCLAD, -1500, 1000)])

    mmi_enc(LAYER.WG, enc)


def test_layer_multi_enc(LAYER):
    enc = kf.utils.Enclosure(
        [
            (LAYER.WGCLAD, -5000, -5400),
            (LAYER.WGCLAD, -4000, -3900),
            (LAYER.WGCLAD, -100, 100),
            (LAYER.WGCLAD, -500, -400),
        ]
    )
    mmi_enc(LAYER.WG, enc)


def test_layer_merge_enc(LAYER):
    enc = kf.utils.Enclosure(
        [
            (LAYER.WGCLAD, -5000, -3000),
            (LAYER.WGCLAD, -4000, -2000),
            (LAYER.WGCLAD, -2000, 1000),
        ]
    )
    mmi_enc(LAYER.WG, enc)


def test_um_enclosure(LAYER):
    enc = kf.utils.Enclosure(
        [
            (LAYER.WGCLAD, -5000, -3000),
            (LAYER.WGCLAD, -4000, -2000),
            (LAYER.WGCLAD, -2000, 1000),
        ]
    )

    enc_um = kf.utils.Enclosure(
        dsections=[
            (LAYER.WGCLAD, -5, -3),
            (LAYER.WGCLAD, -4, -2),
            (LAYER.WGCLAD, -2, 1),
        ],
        dbu=0.001,
    )

    assert enc == enc_um


def test_um_enclosure_nodbu(LAYER):
    with pytest.raises(AssertionError) as ae_info:
        kf.utils.Enclosure(
            dsections=[
                (LAYER.WGCLAD, -5, -3),
                (LAYER.WGCLAD, -4, -2),
                (LAYER.WGCLAD, -2, 1),
            ]
        )

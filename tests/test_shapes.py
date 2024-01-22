import kfactory as kf


def test_shapes(LAYER: kf.LayerEnum) -> None:
    kc = kf.KCell()

    kc.shapes(LAYER.WG).insert(kf.kdb.Text())

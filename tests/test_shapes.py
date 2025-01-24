from conftest import Layers

import kfactory as kf


def test_shapes(LAYER: Layers) -> None:
    kc = kf.KCell()

    kc.shapes(kc.kcl.find_layer(LAYER.WG)).insert(kf.kdb.Text())

from conftest import Layers

import kfactory as kf


def test_shapes(layers: Layers) -> None:
    kc = kf.KCell()

    kc.shapes(kc.kcl.find_layer(layers.WG)).insert(kf.kdb.Text())

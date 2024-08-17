import kfactory as kf
from conftest import Layers


def test_shapes(LAYER: Layers) -> None:
    kc = kf.KCell()

    kc.shapes(kc.kcl.find_layer(LAYER.WG)).insert(kf.kdb.Text())

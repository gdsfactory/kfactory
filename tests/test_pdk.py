import kfactory as kf

import pytest


def test_pdk() -> None:
    pdk = kf.KCLayout("PDK")

    class LAYER(kf.LayerEnum):
        kcl = kf.constant(pdk)
        WG = (1, 0)
        WGEX = (1, 1)

    pdk.layers = LAYER

    assert pdk.layers == LAYER
    "here"

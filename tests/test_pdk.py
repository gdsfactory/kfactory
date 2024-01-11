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


def test_clear() -> None:
    kcl = kf.KCLayout("CLEAR")
    layer = kcl.layer(500, 0)

    kcl.layers = kf.kcell.layerenum_from_dict(kcl=kcl, layers={"WG": (1, 0)})
    assert kcl.layers.WG == 1
    kcl.clear(keep_layers=True)
    assert kcl.layers.WG == 0

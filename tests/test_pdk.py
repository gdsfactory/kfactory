import kfactory as kf

import pytest


# def test_get_cell(pdk: kf.pdk.Pdk):
#     pdk.cell_factories["straight"](width=1000, length=10000)
#     pdk.cell_factories.straight(width=1000, length=10000)


# def test_get_enclosure(pdk: kf.pdk.Pdk):
#     pdk.layer_enclosures["wg"]
#     pdk.layer_enclosures.wg


# def test_cell_factory(pdk: kf.pdk.Pdk):
#     assert isinstance(pdk.cell_factories.taper(2, 1, 10, 0), kf.KCell)


# def test_get_layer(pdk: kf.pdk.Pdk, LAYER: kf.LayerEnum):
#     assert pdk.layers(pdk.kcl.layer(1, 0)) == LAYER.WG
#     assert pdk.layers(0) == LAYER.WG
#     assert pdk.layers["WG"] == LAYER.WG

#     with pytest.raises(ValueError):
#         pdk.layers((1, 0))


def test_pdk() -> None:
    pdk = kf.KCLayout("PDK")

    class LAYER(kf.LayerEnum):
        kcl = kf.constant(pdk)
        WG = (1, 0)
        WGEX = (1, 1)

    pdk.layers = LAYER

    assert pdk.layers == LAYER
    "here"

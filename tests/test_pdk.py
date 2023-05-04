import kfactory as kf

import pytest


def test_get_cell(pdk: kf.pdk.Pdk):
    pdk.get_cell("waveguide", width=1000, length=10000)


def test_get_enclosure(pdk: kf.pdk.Pdk):
    pdk.get_enclosure("wg")


def test_cell_factory(pdk: kf.pdk.Pdk):
    assert isinstance(pdk.cell_factories.taper(2, 1, 10, 0), kf.KCell)


def test_get_layer(pdk: kf.pdk.Pdk, LAYER: kf.LayerEnum):
    assert pdk.get_layer((1, 0)) == LAYER.WG
    assert pdk.get_layer(0) == LAYER.WG
    assert pdk.get_layer("WG") == LAYER.WG

    with pytest.raises(ValueError):
        pdk.get_layer((1, 0, 0))

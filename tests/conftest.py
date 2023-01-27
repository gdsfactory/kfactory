import pytest
from kfactory.tech import LayerEnum
import kfactory as kf
from functools import partial


class LAYER_CLASS(LayerEnum):
    WG = (1, 0)
    WGCLAD = (111, 0)


@pytest.fixture
def LAYER():
    return LAYER_CLASS


@pytest.fixture
def wg_enc(LAYER):
    return kf.utils.Enclosure([(2000, LAYER.WGCLAD)])


@pytest.fixture
def waveguide_factory(LAYER, wg_enc):
    return partial(kf.pcells.dbu.waveguide, layer=LAYER.WG, enclosure=wg_enc)


@pytest.fixture
def bend90(LAYER, wg_enc):
    return kf.pcells.euler.bend_euler(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, theta=90
    )


@pytest.fixture
def bend180(LAYER, wg_enc):
    return kf.pcells.euler.bend_euler(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, theta=180
    )


# @pytest.fixture
# def wg():
#     return LAYER.WG

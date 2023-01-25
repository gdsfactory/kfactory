import pytest
from kfactory.tech import LayerEnum
import kfactory as kf


class LAYER_CLASS(LayerEnum):
    WG = (1, 0)
    WGCLAD = (111, 0)


@pytest.fixture
def LAYER():
    return LAYER_CLASS


@pytest.fixture
def wg_enc(LAYER):
    return kf.utils.Enclosure([(2000, LAYER.WGCLAD)])


# @pytest.fixture
# def wg():
#     return LAYER.WG

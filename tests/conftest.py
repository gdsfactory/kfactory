import pytest
from kfactory.tech import LayerEnum
import kfactory as kf


# @pytest.fixture
class LAYER(LayerEnum):
    WG = (1, 0)
    WGCLAD = (111, 0)


# @pytest.fixture
# def wg():
#     return LAYER.WG

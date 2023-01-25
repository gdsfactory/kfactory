import kfactory as kf
from kfactory.utils.enclosure import extrude_profile
import numpy as np


@kf.autocell
def taper_dyn(
    length: float, width: float, layer: kf.tech.LayerEnum, enclosure: kf.utils.Enclosure
) -> kf.KCell:
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]
    _width = lambda x: width + width * np.sin(x * np.pi / 2)

    extrude_profile(c, layer, path, _width, enclosure)

    return c


@kf.autocell
def taper_static(
    length: float, width: float, layer: kf.tech.LayerEnum, enclosure: kf.utils.Enclosure
) -> kf.KCell:
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]

    _width = [width + np.sin(x * np.pi / 2) for x in [_x / 20 for _x in range(21)]]
    extrude_profile(c, layer, path, _width, enclosure)

    return c


def test_dynamic_sine_taper(LAYER, wg_enc):
    taper_dyn(10, 1, LAYER.WG, wg_enc)


def test_static_sine_taper(LAYER, wg_enc):
    taper_static(10, 1, LAYER.WG, wg_enc)

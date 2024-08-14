import kfactory as kf
from kfactory.enclosure import extrude_path, extrude_path_dynamic
import numpy as np
from conftest import Layers


@kf.cell
def taper_dyn(
    length: float, width: float, layer: kf.kdb.LayerInfo, enclosure: kf.LayerEnclosure
) -> kf.KCell:
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]
    _width = lambda x: width + width * np.sin(x * np.pi / 2)

    extrude_path_dynamic(c, layer, path, _width, enclosure)

    return c


@kf.cell
def taper_static(
    length: float, width: float, layer: kf.kdb.LayerInfo, enclosure: kf.LayerEnclosure
) -> kf.KCell:
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]

    _width = [width + np.sin(x * np.pi / 2) for x in [_x / 20 for _x in range(21)]]
    extrude_path_dynamic(c, layer, path, _width, enclosure)

    return c


def test_dynamic_sine_taper(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> None:
    taper_dyn(10, 1, LAYER.WG, wg_enc)


def test_static_sine_taper(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> None:
    taper_static(10, 1, LAYER.WG, wg_enc)


def test_enc_extrude_dyn(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> None:
    width = 10
    layer = LAYER.WG
    enclosure = wg_enc
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]
    _width = lambda x: width + width * np.sin(x * np.pi / 2)

    enclosure.extrude_path_dynamic(c, path, layer, _width)


def test_enc_extrude_static(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> None:
    width = 10
    layer = LAYER.WG
    enclosure = wg_enc
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]
    _width = [width + np.sin(x * np.pi / 2) for x in [_x / 20 for _x in range(21)]]

    enclosure.extrude_path_dynamic(c, path, layer, _width)

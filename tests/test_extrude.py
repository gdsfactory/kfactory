import numpy as np

import kfactory as kf
from kfactory.enclosure import extrude_path_dynamic
from tests.conftest import Layers


@kf.cell
def taper_dyn(
    length: float,
    width: float,
    layer: kf.kdb.LayerInfo,
    enclosure: kf.LayerEnclosure,
) -> kf.KCell:
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]

    def _width(x: float) -> float:
        return float(width + width * np.sin(x * np.pi / 2))

    extrude_path_dynamic(c, layer, path, _width, enclosure)

    return c


@kf.cell
def taper_static(
    length: float,
    width: float,
    layer: kf.kdb.LayerInfo,
    enclosure: kf.LayerEnclosure,
) -> kf.KCell:
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]

    _width = [width + np.sin(x * np.pi / 2) for x in [_x / 20 for _x in range(21)]]
    extrude_path_dynamic(c, layer, path, _width, enclosure)

    return c


def test_dynamic_sine_taper(layers: Layers, wg_enc: kf.LayerEnclosure) -> None:
    taper_dyn(10, 1, layers.WG, wg_enc)


def test_static_sine_taper(layers: Layers, wg_enc: kf.LayerEnclosure) -> None:
    taper_static(10, 1, layers.WG, wg_enc)


def test_enc_extrude_dyn(layers: Layers, wg_enc: kf.LayerEnclosure) -> None:
    width = 10
    layer = layers.WG
    enclosure = wg_enc
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]

    def _width(x: float) -> float:
        return float(width + width * np.sin(x * np.pi / 2))

    enclosure.extrude_path_dynamic(c, path, layer, _width)


def test_enc_extrude_static(layers: Layers, wg_enc: kf.LayerEnclosure) -> None:
    width = 10
    layer = layers.WG
    enclosure = wg_enc
    c = kf.KCell()

    path = [kf.kdb.DPoint(x, 0) for x in range(21)]
    _width = [width + np.sin(x * np.pi / 2) for x in [_x / 20 for _x in range(21)]]

    enclosure.extrude_path_dynamic(c, path, layer, _width)

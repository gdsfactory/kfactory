import kfactory as kf
import pytest
import warnings
from random import randint

from typing import Callable


@kf.autocell
def simple_cplx_cell(layer: kf.LayerEnum) -> kf.KCell:
    c = kf.CplxKCell()

    hh = 2.5

    dct = kf.kdb.DCplxTrans(1, 30, False, 2.5, 2.5)
    dbox = kf.kdb.DPolygon(kf.kdb.DBox(0, -hh, 10, hh)).transformed(dct)

    p1 = kf.DCplxPort(
        width=hh * 2,
        layer=layer,
        name="o1",
        trans=dct * kf.kdb.DCplxTrans.R180,
    )
    p2 = kf.DCplxPort(
        width=hh * 2,
        layer=layer,
        name="o2",
        trans=dct * kf.kdb.DCplxTrans(kf.kdb.DVector(10, 0)),
    )

    c.add_port(p1)
    c.add_port(p2)

    c.shapes(layer).insert(dbox)

    c.draw_ports()
    return c


def test_cell(LAYER: kf.LayerEnum):
    c = simple_cplx_cell(LAYER.WG)


def test_connected_cell(LAYER: kf.LayerEnum):
    c = kf.CplxKCell()
    layer = LAYER.WG
    sckc1 = c << simple_cplx_cell(layer)
    sckc2 = c << simple_cplx_cell(layer)
    sckc2.connect("o1", sckc1, "o1")

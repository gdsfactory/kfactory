import kfactory as kf
from conftest import Layers


@kf.cell
def simple_cplx_cell(layer: kf.kdb.LayerInfo) -> kf.KCell:
    c = kf.KCell()

    hh = 2.5

    dct = kf.kdb.DCplxTrans(1, 30, False, 2.5, 2.5)
    dbox = kf.kdb.DPolygon(kf.kdb.DBox(0, -hh, 10, hh)).transformed(dct)

    li = c.kcl.find_layer(layer)

    p1 = kf.Port(
        dwidth=hh * 2,
        layer=li,
        name="o1",
        dcplx_trans=dct * kf.kdb.DCplxTrans.R180,
    )
    p2 = kf.Port(
        dwidth=hh * 2,
        layer=li,
        name="o2",
        dcplx_trans=dct * kf.kdb.DCplxTrans(kf.kdb.DVector(10, 0)),
    )

    c.add_port(p1)
    c.add_port(p2)

    c.shapes(li).insert(dbox)

    c.draw_ports()
    return c


def test_cell(LAYER: Layers) -> None:
    simple_cplx_cell(LAYER.WG)


def test_connected_cell(LAYER: Layers) -> None:
    c = kf.KCell()
    layer = LAYER.WG
    sckc1 = c << simple_cplx_cell(layer)
    sckc2 = c << simple_cplx_cell(layer)
    sckc2.connect("o1", sckc1, "o1")

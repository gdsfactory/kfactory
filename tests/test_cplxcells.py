import kfactory as kf
from tests.conftest import Layers


@kf.cell
def simple_cplx_cell(layer: kf.kdb.LayerInfo) -> kf.KCell:
    c = kf.KCell()

    hh = 2.5

    dct = kf.kdb.DCplxTrans(1, 30, False, 2.5, 2.5)
    dbox = kf.kdb.DPolygon(kf.kdb.DBox(0, -hh, 10, hh)).transformed(dct)

    li = c.kcl.find_layer(layer)

    p1 = kf.Port(
        width=c.kcl.to_dbu(hh * 2),
        layer=li,
        name="o1",
        dcplx_trans=dct * kf.kdb.DCplxTrans.R180,
    )
    p2 = kf.Port(
        width=c.kcl.to_dbu(hh * 2),
        layer=li,
        name="o2",
        dcplx_trans=dct * kf.kdb.DCplxTrans(kf.kdb.DVector(10, 0)),
    )

    c.add_port(port=p1)
    c.add_port(port=p2)

    c.shapes(li).insert(dbox)

    c.draw_ports()
    return c


def test_cell(layers: Layers) -> None:
    simple_cplx_cell(layers.WG)


def test_connected_cell(layers: Layers) -> None:
    c = kf.KCell()
    layer = layers.WG
    sckc1 = c << simple_cplx_cell(layer)
    sckc2 = c << simple_cplx_cell(layer)
    sckc2.connect("o1", sckc1, "o1")

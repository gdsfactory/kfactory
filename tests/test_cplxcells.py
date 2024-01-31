import kfactory as kf


@kf.cell
def simple_cplx_cell(layer: kf.LayerEnum) -> kf.KCell:
    c = kf.KCell()

    hh = 2.5

    dct = kf.kdb.DCplxTrans(1, 30, False, 2.5, 2.5)
    dbox = kf.kdb.DPolygon(kf.kdb.DBox(0, -hh, 10, hh)).transformed(dct)

    p1 = kf.Port(
        dwidth=hh * 2,
        layer=layer,
        name="o1",
        dcplx_trans=dct * kf.kdb.DCplxTrans.R180,
    )
    p2 = kf.Port(
        dwidth=hh * 2,
        layer=layer,
        name="o2",
        dcplx_trans=dct * kf.kdb.DCplxTrans(kf.kdb.DVector(10, 0)),
    )

    c.add_port(p1)
    c.add_port(p2)

    c.shapes(layer).insert(dbox)

    c.draw_ports()
    return c


def test_cell(LAYER: kf.LayerEnum) -> None:
    c = simple_cplx_cell(LAYER.WG)
    c.show()


def test_connected_cell(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()
    layer = LAYER.WG
    sckc1 = c << simple_cplx_cell(layer)
    sckc2 = c << simple_cplx_cell(layer)
    sckc2.connect("o1", sckc1, "o1")
    c.show()

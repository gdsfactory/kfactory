import kfactory as kf
from collections.abc import Callable


def test_enclosure_name(straight_factory: Callable[..., kf.KCell]) -> None:
    wg = straight_factory(width=1000, length=10000)
    assert wg.name == "Straight_W1000_L10000_LWG_EWGSTD"
    wg.show()


def test_circular_snapping(LAYER: kf.LayerEnum) -> None:
    b = kf.cells.circular.bend_circular(width=1, radius=10, layer=LAYER.WG, angle=90)
    assert b.ports["o2"].dcplx_trans.disp == b.ports["o2"].trans.disp.to_dtype(
        b.kcl.dbu
    )


def test_euler_snapping(LAYER: kf.LayerEnum) -> None:
    b = kf.cells.euler.bend_euler(width=1, radius=10, layer=LAYER.WG, angle=90)
    assert b.ports["o2"].dcplx_trans.disp == b.ports["o2"].trans.disp.to_dtype(
        b.kcl.dbu
    )


def test_no_snap(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()

    c.create_port(
        dwidth=1,
        dcplx_trans=kf.kdb.DCplxTrans(1, 90, False, 0.0005, 0),
        layer=LAYER.WG,
    )

    p = c.ports[0]

    assert p.dcplx_trans.disp != p.trans.disp.to_dtype(c.kcl.dbu)


def test_namecollision(LAYER: kf.LayerEnum) -> None:
    b1 = kf.cells.circular.bend_circular(width=1, radius=10.5, layer=LAYER.WG)
    b2 = kf.cells.circular.bend_circular(width=1, radius=10.5000005, layer=LAYER.WG)

    assert b1.name != b2.name

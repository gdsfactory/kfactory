import kfactory as kf
import pytest


@pytest.mark.parametrize(
    "center",
    [
        None,
        kf.kdb.Point(0, 0),
        kf.kdb.Point(500, 0),
        kf.kdb.Point(500, 500),
        kf.kdb.Point(1000, 1000),
    ],
)
def test_rotation(
    center: kf.kdb.Point | None, straight: kf.KCell, LAYER: kf.LayerEnum
) -> None:
    c = kf.KCell()

    wg1 = c << straight
    wg2 = c << straight

    wg2.rotate(2, center=center)

    if center:
        c.shapes(LAYER.WGCLAD).insert(
            kf.kdb.Box(10).transformed(kf.kdb.Trans(center.to_v()))
        )

    c.add_ports(wg1.ports)
    c.add_ports(wg2.ports)

    c.show()


@pytest.mark.parametrize(
    "center",
    [
        None,
        kf.kdb.DPoint(0, 0),
        kf.kdb.DPoint(0.5, 0),
        kf.kdb.DPoint(0.5, 0.5),
        kf.kdb.DPoint(1, 1),
    ],
)
def test_drotation(
    center: kf.kdb.DPoint | None, straight: kf.KCell, LAYER: kf.LayerEnum
) -> None:
    c = kf.KCell()

    wg1 = c << straight
    wg2 = c << straight

    wg2.d.rotate(30, center=center)

    if center:
        c.shapes(LAYER.WGCLAD).insert(
            kf.kdb.DBox(0.01).transformed(kf.kdb.DCplxTrans(center.to_v()))
        )

    c.add_ports(wg1.ports)
    c.add_ports(wg2.ports)

    c.show()

import kfactory as kf
from kfactory.routing.steps import Straight


def test_to_dbu() -> None:
    kcl = kf.KCLayout("TEST_TO_DBU")
    assert kcl.to_dbu(1.0) == int(1.0 / kcl.dbu)

    d_point = kf.kdb.DPoint(1.0, 2.0)
    point = kcl.to_dbu(d_point)
    assert point == kf.kdb.Point(int(1.0 / kcl.dbu), int(2.0 / kcl.dbu))

    d_vector = kf.kdb.DVector(1.0, 2.0)
    vector = kcl.to_dbu(d_vector)
    assert vector == kf.kdb.Vector(int(1.0 / kcl.dbu), int(2.0 / kcl.dbu))

    d_box = kf.kdb.DBox(1.0, 2.0, 3.0, 4.0)
    box = kcl.to_dbu(d_box)
    assert box == kf.kdb.Box(
        int(1.0 / kcl.dbu), int(2.0 / kcl.dbu), int(3.0 / kcl.dbu), int(4.0 / kcl.dbu)
    )

    d_polygon = kf.kdb.DPolygon([kf.kdb.DPoint(1.0, 2.0), kf.kdb.DPoint(3.0, 4.0)])
    polygon = kcl.to_dbu(d_polygon)
    assert polygon == kf.kdb.Polygon(
        [
            kf.kdb.Point(int(1.0 / kcl.dbu), int(2.0 / kcl.dbu)),
            kf.kdb.Point(int(3.0 / kcl.dbu), int(4.0 / kcl.dbu)),
        ]
    )

    d_path = kf.kdb.DPath([kf.kdb.DPoint(1.0, 2.0), kf.kdb.DPoint(3.0, 4.0)], 0.5)
    path = kcl.to_dbu(d_path)
    assert path == kf.kdb.Path(
        [
            kf.kdb.Point(int(1.0 / kcl.dbu), int(2.0 / kcl.dbu)),
            kf.kdb.Point(int(3.0 / kcl.dbu), int(4.0 / kcl.dbu)),
        ],
        int(0.5 / kcl.dbu),
    )

    d_text = kf.kdb.DText("test", kf.kdb.DTrans(1.0, 2.0))
    text = kcl.to_dbu(d_text)
    assert text == kf.kdb.Text(
        "test", kf.kdb.Trans(int(1.0 / kcl.dbu), int(2.0 / kcl.dbu))
    )

    sequence = [1.0, 2.0, 3.0]
    sequence_dbu = kcl.to_dbu(sequence)
    assert sequence_dbu == [int(1.0 / kcl.dbu), int(2.0 / kcl.dbu), int(3.0 / kcl.dbu)]

    assert kcl.to_dbu(None) is None

    custom_obj = "custom"
    assert kcl.to_dbu(custom_obj) == custom_obj

    straight = Straight(dist=1000)
    assert kcl.to_dbu(straight) == straight


def test_to_um() -> None:
    kcl = kf.KCLayout("TEST_TO_UM")
    assert kcl.to_um(1) == 1 * kcl.dbu

    point = kf.kdb.Point(1, 2)
    d_point = kcl.to_um(point)
    assert d_point == kf.kdb.DPoint(1 * kcl.dbu, 2 * kcl.dbu)

    vector = kf.kdb.Vector(1, 2)
    d_vector = kcl.to_um(vector)
    assert d_vector == kf.kdb.DVector(1 * kcl.dbu, 2 * kcl.dbu)

    box = kf.kdb.Box(1, 2, 3, 4)
    d_box = kcl.to_um(box)
    assert d_box == kf.kdb.DBox(1 * kcl.dbu, 2 * kcl.dbu, 3 * kcl.dbu, 4 * kcl.dbu)

    polygon = kf.kdb.Polygon(
        [
            kf.kdb.Point(0, 0),
            kf.kdb.Point(1, 0),
            kf.kdb.Point(1, 1),
            kf.kdb.Point(0, 1),
        ]
    )
    d_polygon = kcl.to_um(polygon)
    assert d_polygon == kf.kdb.DPolygon(
        [
            kcl.to_um(kf.kdb.Point(0, 0)),
            kcl.to_um(kf.kdb.Point(1, 0)),
            kcl.to_um(kf.kdb.Point(1, 1)),
            kcl.to_um(kf.kdb.Point(0, 1)),
        ]
    )

    path = kf.kdb.Path([kf.kdb.Point(1, 2), kf.kdb.Point(3, 4)], 1)
    d_path = kcl.to_um(path)
    assert d_path == kf.kdb.DPath(
        [
            kf.kdb.DPoint(1 * kcl.dbu, 2 * kcl.dbu),
            kf.kdb.DPoint(3 * kcl.dbu, 4 * kcl.dbu),
        ],
        1 * kcl.dbu,
    )

    text = kf.kdb.Text("test", kf.kdb.Trans(1, 2))
    d_text = kcl.to_um(text)
    assert d_text == kf.kdb.DText("test", kf.kdb.DTrans(1 * kcl.dbu, 2 * kcl.dbu))

    sequence = [1, 2, 3]
    sequence_um = kcl.to_um(sequence)
    assert sequence_um == [1 * kcl.dbu, 2 * kcl.dbu, 3 * kcl.dbu]

    assert kcl.to_um(None) is None

    custom_obj = "custom"
    assert kcl.to_um(custom_obj) == custom_obj

    straight = Straight(dist=1000)
    assert kcl.to_um(straight) == straight


if __name__ == "__main__":
    test_to_dbu()
    test_to_um()

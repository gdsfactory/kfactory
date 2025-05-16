import pytest

import kfactory as kf
from tests.conftest import Layers


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
    center: kf.kdb.Point | None, straight: kf.KCell, layers: Layers
) -> None:
    c = kf.KCell()

    wg1 = c << straight
    wg2 = c << straight
    if center:
        wg2.rotate(2, center=(center.x, center.y))
    else:
        wg2.rotate(2)

    if center:
        c.shapes(c.kcl.find_layer(layers.WGCLAD)).insert(
            kf.kdb.Box(10).transformed(kf.kdb.Trans(center.to_v()))
        )

    c.add_ports(wg1.ports)
    c.add_ports(wg2.ports)


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
    center: kf.kdb.DPoint | None, straight: kf.KCell, layers: Layers
) -> None:
    c = kf.KCell()

    wg1 = c << straight
    wg2 = c << straight

    if center:
        wg2.drotate(30, center=(center.x, center.y))
    else:
        wg2.drotate(30)

    if center:
        c.shapes(c.kcl.find_layer(layers.WGCLAD)).insert(
            kf.kdb.DBox(0.01).transformed(kf.kdb.DCplxTrans(center.to_v()))
        )

    c.add_ports(wg1.ports)
    c.add_ports(wg2.ports)


@pytest.mark.parametrize(
    ("from_name", "use_mirror", "apply_mirror", "expected_transformation"),
    [
        (True, True, True, kf.kdb.Trans(1, False, 11_000, -10_000)),
        (True, True, False, kf.kdb.Trans(1, False, 11_000, -10_000)),
        (True, False, True, kf.kdb.Trans(3, True, 11_000, 10_000)),
        (True, False, False, kf.kdb.Trans(1, False, 11_000, -10_000)),
        (False, True, True, kf.kdb.Trans(1, False, 11_000, -10_000)),
        (False, True, False, kf.kdb.Trans(1, False, 11_000, -10_000)),
        (False, False, True, kf.kdb.Trans(3, True, 11_000, 10_000)),
        (False, False, False, kf.kdb.Trans(1, False, 11_000, -10_000)),
    ],
)
def test_connection_flags(
    straight: kf.KCell,
    bend90: kf.KCell,
    from_name: bool,
    use_mirror: bool,
    apply_mirror: bool,
    expected_transformation: kf.kdb.Trans,
) -> None:
    """Tests all the (relevant) connection flags."""
    c = kf.KCell(name=f"{from_name=}_{use_mirror=}_{apply_mirror=}")
    i1 = c << straight
    i2 = c << bend90

    if apply_mirror:
        i2.mirror((0, 1), (0, 0))

    port = "o2" if from_name else i2.ports["o2"]

    i2.connect(port, i1, "o2", use_mirror=use_mirror)

    assert i2.trans == expected_transformation

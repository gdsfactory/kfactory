import kfactory as kf
import pytest
import warnings
from random import randint


def test_connect_straight(bend90, waveguide_factory, LAYER):
    c = kf.KCell()
    c.create_port(
        name="o1",
        trans=kf.kdb.Trans.R0,
        layer=LAYER.WG,
        width=1000,
        port_type="optical",
    )
    c.create_port(
        name="o2",
        trans=kf.kdb.Trans(2, False, 10000, 0),
        layer=LAYER.WG,
        width=1000,
        port_type="optical",
    )
    kf.routing.optical.connect(
        c,
        c.ports["o1"],
        c.ports["o2"],
        straight_factory=waveguide_factory,
        bend90_cell=bend90,
    )


def test_connect_straight(bend90, waveguide_factory, LAYER, optical_port):
    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(2, False, 10000, 0)
    kf.routing.optical.connect(
        c,
        p1,
        p2,
        straight_factory=waveguide_factory,
        bend90_cell=bend90,
    )


@pytest.mark.parametrize(
    "x,y,angle2",
    [
        (20000, 20000, 2),
        (10000, 10000, 3),
        (randint(10001, 20000), randint(10001, 20000), 3),
    ],
)
def test_connect_bend90(bend90, waveguide_factory, LAYER, optical_port, x, y, angle2):
    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(angle2, False, x, y)
    kf.routing.optical.connect(
        c,
        p1,
        p2,
        straight_factory=waveguide_factory,
        bend90_cell=bend90,
    )


@pytest.mark.parametrize(
    "x,y,angle2",
    [
        (40000, 40000, 2),
        (10000, 10000, 3),
    ],
)
def test_connect_bend90_euler(
    bend90_euler, waveguide_factory, LAYER, optical_port, x, y, angle2
):
    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(angle2, False, x, y)
    kf.routing.optical.connect(
        c,
        p1,
        p2,
        straight_factory=waveguide_factory,
        bend90_cell=bend90_euler,
    )

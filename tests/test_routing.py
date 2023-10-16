import kfactory as kf
import pytest
from random import randint

from collections.abc import Callable


@pytest.mark.parametrize(
    "x",
    [
        5000,
        0,
    ],
)
def test_route_straight(
    x: int,
    bend90: kf.KCell,
    straight_factory: Callable[..., kf.KCell],
    LAYER: kf.LayerEnum,
    optical_port: kf.Port,
) -> None:
    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(2, False, x, 0)
    kf.routing.optical.route(
        c,
        p1,
        p2,
        straight_factory=straight_factory,
        bend90_cell=bend90,
    )


@pytest.mark.parametrize(
    "x,y,angle2",
    [
        (20000, 20000, 2),
        (10000, 10000, 3),
        (randint(10001, 20000), randint(10001, 20000), 3),
        (5000, 10000, 3),  # the mean one where points will collide for radius 10000
        (30000, 5000, 3),
        (500, 500, 3),
        (-500, 30000, 3),
        (500, 30000, 3),
        (-10000, 30000, 3),
        (0, 0, 2),
    ],
)
def test_route_bend90(
    bend90: kf.KCell,
    straight_factory: Callable[..., kf.KCell],
    LAYER: kf.LayerEnum,
    optical_port: kf.Port,
    x: int,
    y: int,
    angle2: int,
) -> None:
    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(angle2, False, x, y)
    b90r = abs(bend90.ports._ports[0].x - bend90.ports._ports[1].x)
    if abs(x) < b90r or abs(y) < b90r:
        kf.config.logfilter.regex = f"Potential collision in routing due to small distance between the port in relation to bend radius x={x}/{b90r}, y={y}/{b90r}"
    kf.routing.optical.route(
        c,
        p1,
        p2,
        straight_factory=straight_factory,
        bend90_cell=bend90,
    )

    kf.config.logfilter.regex = None


@pytest.mark.parametrize(
    "x,y,angle2",
    [
        (40000, 40000, 2),
        (20000, 20000, 3),
        (10000, 10000, 3),
    ],
)
def test_route_bend90_euler(
    bend90_euler: kf.KCell,
    straight_factory: Callable[..., kf.KCell],
    LAYER: kf.LayerEnum,
    optical_port: kf.Port,
    x: int,
    y: int,
    angle2: int,
) -> None:
    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(angle2, False, x, y)
    b90r = abs(bend90_euler.ports._ports[0].x - bend90_euler.ports._ports[1].x)
    if abs(x) < b90r or abs(y) < b90r:
        kf.config.logfilter.regex = f"Potential collision in routing due to small distance between the port in relation to bend radius x={x}/{b90r}, y={y}/{b90r}"
    kf.routing.optical.route(
        c,
        p1,
        p2,
        straight_factory=straight_factory,
        bend90_cell=bend90_euler,
    )
    kf.config.logfilter.regex = None


def test_route_bundle(
    LAYER: kf.LayerEnum,
    optical_port: kf.Port,
    bend90_euler: kf.KCell,
) -> None:
    c = kf.KCell()

    # p1 = optical_port.copy()
    # p2 = optical_port.copy()

    p_start = [
        optical_port.copy(kf.kdb.Trans(1, False, i * 10_000, 0)) for i in range(5)
    ]
    p_end = [
        optical_port.copy(kf.kdb.Trans(1, False, i * 10_000 + 1000_000, 0))
        for i in range(5)
    ]

    radius = abs(bend90_euler.ports["o1"].x - bend90_euler["o2"].x)

    pts = kf.routing.manhattan.route_bundle_manhattan(
        p_start,
        p_end,
        bend90_radius=radius,
        spacings=[0],
        start_straights=[0],
        end_straights=[0],
    )
    print(f"{pts=}")

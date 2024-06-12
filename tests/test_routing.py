import kfactory as kf
import pytest
from random import randint
from functools import partial

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
    straight_factory_dbu: Callable[..., kf.KCell],
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
        straight_factory=straight_factory_dbu,
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
    straight_factory_dbu: Callable[..., kf.KCell],
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
        kf.config.logfilter.regex = "route is too small, potential collisions:"
    kf.routing.optical.route(
        c,
        p1,
        p2,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90,
    )

    kf.config.logfilter.regex = None


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
        (500000, 50000, 2),
    ],
)
def test_route_bend90_invert(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
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
        kf.config.logfilter.regex = "route is too small, potential collisions:"
    kf.routing.optical.route(
        c,
        p1,
        p2,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90,
        route_kwargs={"invert": True},
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
    straight_factory_dbu: Callable[..., kf.KCell],
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
        kf.config.logfilter.regex = "route is too small, potential collisions:"
    kf.routing.optical.route(
        c,
        p1,
        p2,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_euler,
    )
    kf.config.logfilter.regex = None


def test_route_bundle(
    LAYER: kf.LayerEnum,
    optical_port: kf.Port,
    bend90_euler: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
) -> None:
    c = kf.KCell()

    p_start = [
        optical_port.copy(
            kf.kdb.Trans(
                1,
                False,
                i * 200_000 - 50_000,
                (4 - i) * 6_000 if i < 5 else (i - 5) * 6_000,
            )
        )
        for i in range(10)
    ]
    p_end = [
        optical_port.copy(
            kf.kdb.Trans(3, False, i * 200_000 + i**2 * 19_000 + 1_000_000, 500_000)
        )
        for i in range(10)
    ]

    c.shapes(kf.kcl.layer(10, 0)).insert(kf.kdb.Box(-50_000, 0, 1_750_000, -100_000))
    c.shapes(kf.kcl.layer(10, 0)).insert(
        kf.kdb.Box(1_000_000, 500_000, p_end[-1].x, 600_000)
    )

    routes = kf.routing.optical.route_bundle(
        c,
        p_start,
        p_end,
        5_000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_euler,
    )

    for route in routes:
        c.add_port(route.start_port)
        c.add_port(route.end_port)

    c.auto_rename_ports()


def test_route_length(
    bend90_euler: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    LAYER: kf.LayerEnum,
    optical_port: kf.Port,
    taper: kf.KCell,
) -> None:
    x, y, angle2 = (70000, 70000, 2)

    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(angle2, False, x, y)
    b90r = abs(bend90_euler.ports._ports[0].x - bend90_euler.ports._ports[1].x)
    if abs(x) < b90r or abs(y) < b90r:
        kf.config.logfilter.regex = "route is too small, potential collisions:"
    route = kf.routing.optical.route(
        c,
        p1,
        p2,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_euler,
        taper_cell=taper,
        min_straight_taper=0,
    )
    kf.config.logfilter.regex = None

    assert route.length == 65196
    assert route.length_straights == 25196
    assert route.length_backbone == 140000
    assert route.n_bend90 == 2


@pytest.mark.parametrize(
    "start_bbox,start_angle,n_angles",
    [
        (start_bbox, start_angle, n_angles)
        for start_bbox in (False, True)
        for start_angle in (-2, -1, 0, 1, 2)
        for n_angles in [1, 4]
        # for n_angles in [2]
    ],
)
def test_smart_routing(
    bend90: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    start_bbox: bool,
    start_angle: int,
    n_angles: int,
) -> None:
    c = kf.KCell(f"test_smart_routing_{start_bbox=}_{start_angle=}_{n_angles=}")

    i = 0

    base_t = kf.kdb.Trans.R0

    _port = partial(c.create_port, width=500, layer=kf.kcl.layer(1, 0))

    start_ports: list[kf.Port] = []
    end_ports: list[kf.Port] = []
    start_boxes: list[kf.kdb.Box] = []
    end_boxes: list[kf.kdb.Box] = []
    start_bboxes: list[kf.kdb.Box] = []
    end_bboxes: list[kf.kdb.Box] = []

    for a in range(4):
        t = base_t * kf.kdb.Trans(a * 1_000_000, 0)
        start_box = t * kf.kdb.Box(350_000) if start_bbox else kf.kdb.Box()
        end_box = kf.kdb.Box()
        for i in range(n_angles):
            angle = a - 2 - start_angle + i
            for j in range(10):
                ps = _port(
                    name=f"start_{a=}_{i=}_{j=}",
                    trans=t
                    * kf.kdb.Trans(angle, False, 0, 0)
                    * kf.kdb.Trans(100_000, j * 10_000 - 50_000),
                )
                pe = _port(
                    name=f"end_{a=}_{i=}_{j=}",
                    trans=t
                    * kf.kdb.Trans(a, False, 0, 0)
                    * kf.kdb.Trans(-400_000, -(i * 10 + j) * 20_000 + 600_000),
                )
                start_ports.append(ps)
                end_ports.append(pe)
                start_box += ps.trans.disp.to_p()
                end_box += pe.trans.disp.to_p()

        start_boxes.append(start_box)
        end_boxes.append(end_box)
    for box in start_boxes + end_boxes:
        c.shapes(kf.kcl.layer(10, 0)).insert(box)

    for box in start_bboxes:
        c.shapes(kf.kcl.layer(11, 0)).insert(box)
    for box in end_bboxes:
        c.shapes(kf.kcl.layer(12, 0)).insert(box)

    kf.routing.optical.route_bundle(
        c,
        start_ports=start_ports,
        # start_ports=list(reversed(ps)),
        end_ports=end_ports,
        bend90_cell=bend90,
        separation=2000,
        straight_factory=straight_factory_dbu,
        # bboxes=[c.bbox(kf.kcl.layer(5, 0)), c.bbox(kf.kcl.layer(6, 0))],  # + bboxes,
        bboxes=start_boxes + end_boxes + start_bboxes + end_bboxes,
        # sort_ports=True,
        bbox_routing="minimal",
    )

    c.show()


# breakpoint()

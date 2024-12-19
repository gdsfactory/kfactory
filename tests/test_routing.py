import kfactory as kf
import pytest
from random import randint
from functools import partial
from conftest import Layers

from collections.abc import Callable
from typing import Literal


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
    LAYER: Layers,
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
    LAYER: Layers,
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
    LAYER: Layers,
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
    LAYER: Layers,
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
    LAYER: Layers,
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
            kf.kdb.Trans(3, False, i * 200_000 + i**2 * 19_000 + 500_000, 300_000)
        )
        for i in range(10)
    ]

    c.shapes(kf.kcl.find_layer(10, 0)).insert(
        kf.kdb.Box(-50_000, 0, 1_750_000, -100_000)
    )
    c.shapes(kf.kcl.find_layer(10, 0)).insert(
        kf.kdb.Box(1_000_000, 500_000, p_end[-1].x, 600_000)
    )

    routes = kf.routing.optical.route_bundle(
        c,
        p_start,
        p_end,
        5_000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_euler,
        on_collision=None,
    )

    for route in routes:
        c.add_port(route.start_port)
        c.add_port(route.end_port)

    c.auto_rename_ports()


def test_route_length(
    bend90_euler: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    LAYER: Layers,
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
    )
    kf.config.logfilter.regex = None

    assert route.length == 65196
    assert route.length_straights == 25196
    assert route.length_backbone == 140000
    assert route.n_bend90 == 2


@pytest.mark.parametrize(
    "indirect,sort_ports,start_bbox,start_angle,m2,m1,z,p1,p2",
    [
        (indirect, sort_ports, start_bbox, start_angle, m2, m1, z, p1, p2)
        for indirect in (True, False)
        for sort_ports in (False, True)
        for start_bbox in (False, True)
        for start_angle in (-2, -1, 0, 1, 2)
        for m2 in (True, False)
        for m1 in (True, False)
        for z in (True, False)
        for p1 in (True, False)
        for p2 in (True, False)
    ],
)
def test_smart_routing(
    bend90_small: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    start_bbox: bool,
    sort_ports: bool,
    indirect: bool,
    start_angle: int,
    m2: bool,
    m1: bool,
    z: bool,
    p1: bool,
    p2: bool,
) -> None:
    """Tests all possible smart routing configs."""
    c = kf.KCell(
        f"test_smart_routing_{sort_ports=}_{start_bbox=}_{start_angle=}"
        f"{m2=}_{m1=}_{z=}_{p1=}_{p2=}"
    )
    c.name = c.name.replace("=", "")

    i = 0

    base_t = kf.kdb.Trans.R0

    _port = partial(c.create_port, width=500, layer=kf.kcl.find_layer(1, 0))

    start_ports: list[kf.Port] = []
    end_ports: list[kf.Port] = []
    start_boxes: list[kf.kdb.Box] = []
    end_boxes: list[kf.kdb.Box] = []
    start_bboxes: list[kf.kdb.Box] = []
    end_bboxes: list[kf.kdb.Box] = []

    angles: list[int] = []
    if m2 and (m1 or z):
        angles.append(-2)
    if m1:
        angles.append(-1)
    if z:
        angles.append(0)
    if p1:
        angles.append(1)
    if p2 and (p1 or z):
        angles.append(2)

    for a in range(4):
        t = base_t * kf.kdb.Trans(a // 2 * 3_000_000, a % 2 * 3_000_000)
        start_box = t * kf.kdb.Box(350_000) if start_bbox else kf.kdb.Box()
        end_box = kf.kdb.Box()
        n = 0
        te = (
            kf.kdb.Trans(2, False, -400_000, 400_000)
            if indirect
            else kf.kdb.Trans(-400_000, 0)
        )
        for i in angles:
            angle = a + start_angle + i
            if i == 2:
                for j in range(5):
                    ps = _port(
                        name=f"start_{a=}_{i=}_{j=}",
                        trans=t
                        * kf.kdb.Trans(angle, False, 0, 0)
                        * kf.kdb.Trans(100_000, (1 - j) * 15_000 - 50_000),
                    )
                    pe = _port(
                        name=f"end_{a=}_{i=}_{j=}",
                        trans=t
                        * kf.kdb.Trans(a, False, 0, 0)
                        * te
                        * kf.kdb.Trans(0, (-n - 4 + j * 2) * 40_000 + 600_000),
                    )
                    start_ports.append(ps)
                    end_ports.append(pe)
                    start_box += ps.trans.disp.to_p()
                    end_box += pe.trans.disp.to_p()
                    n += 1
            elif i == -2:
                for j in range(5):
                    ps = _port(
                        name=f"start_{a=}_{i=}_{j=}",
                        trans=t
                        * kf.kdb.Trans(angle, False, 0, 0)
                        * kf.kdb.Trans(100_000, j * 15_000 + 50_000),
                    )
                    pe = _port(
                        name=f"end_{a=}_{i=}_{j=}",
                        trans=t
                        * kf.kdb.Trans(a, False, 0, 0)
                        * te
                        * kf.kdb.Trans(0, -n * 40_000 + 600_000),
                    )
                    start_ports.append(ps)
                    end_ports.append(pe)
                    start_box += ps.trans.disp.to_p()
                    end_box += pe.trans.disp.to_p()
                    n += 1
            else:
                for j in range(10):
                    ps = _port(
                        name=f"start_{a=}_{i=}_{j=}",
                        trans=t
                        * kf.kdb.Trans(angle, False, 0, 0)
                        * kf.kdb.Trans(100_000, j * 15_000 - 50_000),
                    )
                    pe = _port(
                        name=f"end_{a=}_{i=}_{j=}",
                        trans=t
                        * kf.kdb.Trans(a, False, 0, 0)
                        * te
                        * kf.kdb.Trans(0, -n * 40_000 + 600_000),
                    )
                    start_ports.append(ps)
                    end_ports.append(pe)
                    start_box += ps.trans.disp.to_p()
                    end_box += pe.trans.disp.to_p()
                    n += 1

        start_boxes.append(start_box)
        end_boxes.append(end_box)
    for box in start_boxes + end_boxes:
        c.shapes(kf.kcl.find_layer(10, 0)).insert(box)

    for box in start_bboxes:
        c.shapes(kf.kcl.find_layer(11, 0)).insert(box)
    for box in end_bboxes:
        c.shapes(kf.kcl.find_layer(12, 0)).insert(box)

    match (m1, p1):
        case (True, False):
            rf = partial(
                kf.routing.electrical.route_bundle,
                c,
                start_ports=start_ports,
                end_ports=end_ports,
                separation=4000,
                bboxes=start_boxes + end_boxes + start_bboxes + end_bboxes,
                sort_ports=sort_ports,
                bbox_routing="full",
                on_collision="error",
            )
        case (False, True):
            rf = partial(
                kf.routing.electrical.route_bundle_dual_rails,
                c,
                start_ports=start_ports,
                end_ports=end_ports,
                separation=4000,
                bboxes=start_boxes + end_boxes + start_bboxes + end_bboxes,
                sort_ports=sort_ports,
                bbox_routing="full",
                on_collision="error",
                separation_rails=100,
            )
        case _:
            rf = partial(
                kf.routing.optical.route_bundle,
                c,
                start_ports=start_ports,
                end_ports=end_ports,
                separation=4000,
                bboxes=start_boxes + end_boxes + start_bboxes + end_bboxes,
                sort_ports=sort_ports,
                bbox_routing="full",
                on_collision="error",
                bend90_cell=bend90_small,
                straight_factory=straight_factory_dbu,
            )

    # (indirect, sort_ports, start_bbox, start_angle, m2, m1, z, p1, p2)
    match (indirect, sort_ports, start_bbox, start_angle, m2, m1, z, p1, p2):
        case (
            (True, False, False, -1, True, False, False, True, False)
            | (True, False, False, -1, False, False, False, True, False)
            | (True, False, False, 0, False, False, True, False, False)
            | (True, False, False, 1, False, True, False, False, True)
            | (True, False, False, 1, False, True, False, False, False)
            | (True, True, False, -1, True, False, False, True, False)
            | (True, True, False, -1, False, False, False, True, False)
            | (True, True, False, 0, False, False, True, False, False)
            | (True, True, False, 1, False, True, False, False, True)
            | (True, True, False, 1, False, True, False, False, False)
        ):
            with pytest.raises(RuntimeError):  # , match="Routing Collision"):i
                rf()
        case _:
            rf()


def test_custom_router(
    LAYER: Layers,
) -> None:
    c = kf.kcl.kcell("CustomRouter")
    bend90 = kf.cells.circular.bend_circular(width=1, radius=10, layer=LAYER.WG)
    b90r = kf.routing.generic.get_radius(bend90.ports)
    sf = partial(kf.cells.straight.straight_dbu, layer=LAYER.WG)

    start_ports = [
        kf.Port(
            name="in{i}",
            width=1000,
            layer_info=LAYER.WG,
            trans=kf.kdb.Trans(1, False, -850_000 + i * 200_000, 0),
            kcl=c.kcl,
        )
        for i in range(10)
    ]
    end_ports = [
        kf.Port(
            name="in{i}",
            width=1000,
            layer_info=LAYER.WG,
            trans=kf.kdb.Trans(3, False, -400_000 + i * 100_000, 200_000),
            kcl=c.kcl,
        )
        for i in range(10)
    ]

    kf.routing.generic.route_bundle(
        c=c,
        start_ports=start_ports,
        end_ports=end_ports,
        ends=50_000,
        starts=50_000,
        routing_function=kf.routing.manhattan.route_smart,
        routing_kwargs={
            "bend90_radius": b90r,
            "separation": 4000,
        },
        placer_function=kf.routing.optical.place90,
        placer_kwargs={"bend90_cell": bend90, "straight_factory": sf},
        router_post_process_function=kf.routing.manhattan.path_length_match_manhattan_route,
        router_post_process_kwargs={
            "bend90_radius": b90r,
            "separation": 5000,
        },
    )


def test_route_smart_waypoints_trans_sort(
    bend90_small: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    LAYER: Layers,
) -> None:
    c = kf.KCell("TEST_SMART_ROUTE_WAYPOINTS_TRANS_SORT")
    _l = 15
    transformations = [kf.kdb.Trans(0, False, 0, i * 50_000) for i in range(_l)] + [
        kf.kdb.Trans(1, False, -15_000 - i * 50_000, 15 * 50_000) for i in range(_l)
    ]
    start_ports = [
        kf.Port(width=500, layer_info=LAYER.WG, kcl=c.kcl, trans=trans)
        for trans in transformations
    ]
    end_ports = [
        kf.Port(
            width=500,
            layer_info=LAYER.WG,
            kcl=c.kcl,
            trans=kf.kdb.Trans(2, False, 500_000, 0) * trans,
        )
        for trans in transformations
    ]
    kf.routing.optical.route_bundle(
        c,
        start_ports,
        end_ports,
        separation=4000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_small,
        waypoints=kf.kdb.Trans(250_000, 0),
        sort_ports=True,
    )


def test_route_smart_waypoints_pts_sort(
    bend90_small: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    LAYER: Layers,
) -> None:
    c = kf.KCell("TEST_SMART_ROUTE_WAYPOINTS_PTS_SORT")
    _l = 15
    transformations = [kf.kdb.Trans(0, False, 0, i * 50_000) for i in range(_l)] + [
        kf.kdb.Trans(1, False, -15_000 - i * 50_000, 15 * 50_000) for i in range(_l)
    ]
    start_ports = [
        kf.Port(width=500, layer_info=LAYER.WG, kcl=c.kcl, trans=trans)
        for trans in transformations
    ]
    end_ports = [
        kf.Port(
            width=500,
            layer_info=LAYER.WG,
            kcl=c.kcl,
            trans=kf.kdb.Trans(2, False, 500_000, 0) * trans,
        )
        for trans in transformations
    ]
    kf.routing.optical.route_bundle(
        c,
        start_ports,
        end_ports,
        separation=4000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_small,
        waypoints=[kf.kdb.Point(250_000, 0), kf.kdb.Point(250_000, 100_000)],
        sort_ports=True,
    )


def test_route_smart_waypoints_trans(
    bend90_small: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    LAYER: Layers,
) -> None:
    c = kf.KCell("TEST_SMART_ROUTE_WAYPOINTS_TRANS")
    _l = 15
    transformations = [kf.kdb.Trans(0, False, 0, i * 50_000) for i in range(_l)] + [
        kf.kdb.Trans(1, False, -15_000 - i * 50_000, 15 * 50_000) for i in range(_l)
    ]
    start_ports = [
        kf.Port(width=500, layer_info=LAYER.WG, kcl=c.kcl, trans=trans)
        for trans in transformations
    ]
    start_ports.reverse()
    end_ports = [
        kf.Port(
            width=500,
            layer_info=LAYER.WG,
            kcl=c.kcl,
            trans=kf.kdb.Trans(2, False, 500_000, 0) * trans,
        )
        for trans in transformations
    ]
    kf.routing.optical.route_bundle(
        c,
        start_ports,
        end_ports,
        separation=4000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_small,
        waypoints=kf.kdb.Trans(250_000, 0),
    )


def test_route_smart_waypoints_pts(
    bend90_small: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    LAYER: Layers,
) -> None:
    c = kf.KCell("TEST_SMART_ROUTE_WAYPOINTS_PTS")
    _l = 15
    transformations = [kf.kdb.Trans(0, False, 0, i * 50_000) for i in range(_l)] + [
        kf.kdb.Trans(1, False, -15_000 - i * 50_000, 15 * 50_000) for i in range(_l)
    ]
    start_ports = [
        kf.Port(width=500, layer_info=LAYER.WG, kcl=c.kcl, trans=trans)
        for trans in transformations
    ]
    start_ports.reverse()
    end_ports = [
        kf.Port(
            width=500,
            layer_info=LAYER.WG,
            kcl=c.kcl,
            trans=kf.kdb.Trans(2, False, 500_000, 0) * trans,
        )
        for trans in transformations
    ]
    kf.routing.optical.route_bundle(
        c,
        start_ports,
        end_ports,
        separation=4000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_small,
        waypoints=[kf.kdb.Point(250_000, 0), kf.kdb.Point(250_000, 100_000)],
    )


def test_route_generic_reorient(
    bend90_small: kf.KCell, straight_factory_dbu: Callable[..., kf.KCell], LAYER: Layers
) -> None:
    c = kf.KCell("test_route_generic_reorient")

    start_ports = [
        c.create_port(
            name=f"bot_{i}",
            trans=kf.kdb.Trans(i, False, i * 30_000, 0),
            layer_info=kf.kdb.LayerInfo(1, 0),
            width=500,
        )
        for i in range(10)
    ]
    end_ports = [
        c.create_port(
            name=f"top_{i}",
            trans=kf.kdb.Trans(1, False, i * 30_000, 500_000),
            layer_info=kf.kdb.LayerInfo(i, 0),
            width=500,
        )
        for i in range(10)
    ]
    # end_ports.reverse()

    c.add_ports(start_ports + end_ports)

    start_angles = [2, 1, 1, 1, 1, 1, 1, 1, 1, 0]
    end_angles = 3

    kf.routing.optical.route_bundle(
        c,
        start_ports=start_ports,
        end_ports=end_ports,
        separation=4000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_small,
        start_angles=start_angles,
        end_angles=end_angles,
    )


def test_placer_error(
    bend90_small: kf.KCell, straight_factory_dbu: Callable[..., kf.KCell], LAYER: Layers
) -> None:
    c = kf.KCell("test_placer_error")

    ps = kf.Port(name="start", width=500, layer_info=LAYER.WG, trans=kf.kdb.Trans.R0)
    pe = kf.Port(
        name="end",
        width=500,
        layer_info=LAYER.WG,
        trans=kf.kdb.Trans(2, False, 200_000, 0),
    )
    ps2 = kf.Port(
        name="start2", width=500, layer_info=LAYER.WG, trans=kf.kdb.Trans(0, 5_000)
    )
    pe2 = kf.Port(
        name="end2",
        width=500,
        layer_info=LAYER.WG,
        trans=kf.kdb.Trans(2, False, 200_000, 5_000),
    )
    ps3 = kf.Port(
        name="start3", width=500, layer_info=LAYER.WG, trans=kf.kdb.Trans(0, 10_000)
    )
    pe3 = kf.Port(
        name="end3",
        width=500,
        layer_info=LAYER.WG,
        trans=kf.kdb.Trans(2, False, 200_000, 10_000),
    )

    with pytest.raises(kf.routing.generic.PlacerError):
        kf.routing.optical.route_bundle(
            c,
            start_ports=[ps3, ps2, ps],
            end_ports=[pe3, pe2, pe],
            waypoints=[
                kf.kdb.Point(50_000, 5_000),
                kf.kdb.Point(55_000, 5_000),
                kf.kdb.Point(55_000, 15_000),
                kf.kdb.Point(60_000, 15_000),
                kf.kdb.Point(60_000, 5_000),
                kf.kdb.Point(65_000, 5_000),
            ],
            separation=5_000,
            straight_factory=straight_factory_dbu,
            bend90_cell=bend90_small,
            on_placer_error="error",
        )

from collections.abc import Callable
from functools import partial
from typing import Any

import numpy as np
import pytest

import kfactory as kf
from tests.conftest import Layers

smart_bundle_routing_params = [
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
]


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
    ("x", "y", "angle2"),
    [
        (20000, 20000, 2),
        (10000, 10000, 3),
        (150532, 12112, 3),
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
    optical_port: kf.Port,
    x: int,
    y: int,
    angle2: int,
) -> None:
    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(angle2, False, x, y)
    b90r = abs(bend90.ports[0].x - bend90.ports[1].x)
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
    ("x", "y", "angle2"),
    [
        (20000, 20000, 2),
        (10000, 10000, 3),
        (15212, 19921, 3),
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
    optical_port: kf.Port,
    x: int,
    y: int,
    angle2: int,
) -> None:
    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(angle2, False, x, y)
    b90r = abs(bend90.ports[0].x - bend90.ports[1].x)
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
    ("x", "y", "angle2"),
    [
        (40000, 40000, 2),
        (20000, 20000, 3),
        (10000, 10000, 3),
    ],
)
def test_route_bend90_euler(
    bend90_euler: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    optical_port: kf.Port,
    x: int,
    y: int,
    angle2: int,
) -> None:
    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(angle2, False, x, y)
    b90r = abs(bend90_euler.ports[0].x - bend90_euler.ports[1].x)
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
    optical_port: kf.Port,
    bend90_euler: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell("TEST_ROUTE_BUNDLE")

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

    c.shapes(kcl.find_layer(10, 0)).insert(kf.kdb.Box(-50_000, 0, 1_750_000, -100_000))
    c.shapes(kcl.find_layer(10, 0)).insert(
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
    route_lengths = [
        814026.004,
        839026.004,
        902026.004,
        1003026.004,
        1142026.004,
        1313026.004,
        1516026.004,
        1757026.004,
        2036026.004,
        2353026.004,
    ]

    for route, length in zip(routes, route_lengths, strict=True):
        c.add_port(port=route.start_port)
        c.add_port(port=route.end_port)
        assert np.isclose(route.length, length)

    c.auto_rename_ports()


def test_route_length_straight(
    optical_port: kf.Port,
    bend90_euler: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
    layers: Layers,
) -> None:
    c = kcl.kcell("TEST_ROUTE_BUNDLE_AREA_LENGTH")
    p1 = kf.Port(name="o1", width=1000, trans=kf.kdb.Trans.R0, layer_info=layers.WG)
    p2 = p1.copy_polar(d=10_000)
    p2.name = "o2"

    routes = kf.routing.optical.route_bundle(
        c,
        [p1],
        [p2],
        5_000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_euler,
        on_collision=None,
    )

    assert [r.length for r in routes] == [10_000]


def test_route_bundle_route_width(
    optical_port: kf.Port,
    bend90_euler_small: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell("TEST_ROUTE_BUNDLE")

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

    c.shapes(kcl.find_layer(10, 0)).insert(kf.kdb.Box(-50_000, 0, 1_750_000, -100_000))
    c.shapes(kcl.find_layer(10, 0)).insert(
        kf.kdb.Box(1_000_000, 500_000, p_end[-1].x, 600_000)
    )

    routes = kf.routing.optical.route_bundle(
        c,
        p_start,
        p_end,
        5_000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_euler_small,
        on_collision=None,
        route_width=100,
    )

    for route in routes:
        c.add_port(port=route.start_port)
        c.add_port(port=route.end_port)

    c.auto_rename_ports()


def test_route_length(
    bend90_euler: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    optical_port: kf.Port,
    taper: kf.KCell,
) -> None:
    x, y, angle2 = (55000, 70000, 2)

    c = kf.KCell()
    p1 = optical_port.copy()
    p2 = optical_port.copy()
    p2.trans = kf.kdb.Trans(angle2, False, x, y)
    b90r = abs(bend90_euler.ports[0].x - bend90_euler.ports[1].x)
    if abs(x) < b90r or abs(y) < b90r:
        kf.config.logfilter.regex = "route is too small, potential collisions:"
    route = kf.routing.optical.route_bundle(
        c=c,
        start_ports=[p1],
        end_ports=[p2],
        separation=5000,
        straight_factory=straight_factory_dbu,
        bend90_cell=bend90_euler,
        taper_cell=taper,
        allow_width_mismatch=True,
    )[0]
    kf.config.logfilter.regex = None
    assert np.isclose(route.length, 135624.004)
    assert route.length_straights == 30196
    assert route.length_backbone == 125000
    assert route.n_bend90 == 2


_test_smart_routing_kcl = kf.KCLayout("TEST_SMART_ROUTING", infos=Layers)


@pytest.mark.parametrize(
    (
        "indirect",
        "sort_ports",
        "start_bbox",
        "start_angle",
        "m2",
        "m1",
        "z",
        "p1",
        "p2",
    ),
    smart_bundle_routing_params,
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
    kcl = _test_smart_routing_kcl
    c = kcl.kcell(
        name=f"test_smart_routing_{start_bbox=}_{sort_ports=}_{indirect=}_{start_angle=}"
        f"{m2=}_{m1=}_{z=}_{p1=}_{p2=}"
    )
    c.name = c.name.replace("=", "")

    i = 0

    base_t = kf.kdb.Trans.R0

    port = partial(c.create_port, width=500, layer=kcl.find_layer(1, 0))

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
                    ps = port(
                        name=f"start_{a=}_{i=}_{j=}",
                        trans=t
                        * kf.kdb.Trans(angle, False, 0, 0)
                        * kf.kdb.Trans(100_000, (1 - j) * 15_000 - 50_000),
                    )
                    pe = port(
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
                    ps = port(
                        name=f"start_{a=}_{i=}_{j=}",
                        trans=t
                        * kf.kdb.Trans(angle, False, 0, 0)
                        * kf.kdb.Trans(100_000, j * 15_000 + 50_000),
                    )
                    pe = port(
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
                    ps = port(
                        name=f"start_{a=}_{i=}_{j=}",
                        trans=t
                        * kf.kdb.Trans(angle, False, 0, 0)
                        * kf.kdb.Trans(100_000, j * 15_000 - 50_000),
                    )
                    pe = port(
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
        c.shapes(kcl.find_layer(10, 0)).insert(box)

    for box in start_bboxes:
        c.shapes(kcl.find_layer(11, 0)).insert(box)
    for box in end_bboxes:
        c.shapes(kcl.find_layer(12, 0)).insert(box)

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
                routes = rf()
                [route.length for route in routes]
        case _:
            rf()


def test_custom_router(
    layers: Layers,
) -> None:
    kcl = kf.KCLayout("TEST_CUSTOM_ROUTER")
    c = kcl.kcell("CustomRouter")
    bend90 = kf.cells.circular.bend_circular(width=1, radius=10, layer=layers.WG)
    b90r = kf.routing.generic.get_radius(list(bend90.ports))
    sf = partial(kf.cells.straight.straight_dbu, layer=layers.WG)

    start_ports = [
        kf.Port(
            name=f"in{i}",
            width=1000,
            layer_info=layers.WG,
            trans=kf.kdb.Trans(1, False, -850_000 + i * 200_000, 0),
            kcl=c.kcl,
        )
        for i in range(10)
    ]
    end_ports = [
        kf.Port(
            name=f"in{i}",
            width=1000,
            layer_info=layers.WG,
            trans=kf.kdb.Trans(3, False, -400_000 + i * 100_000, 200_000),
            kcl=c.kcl,
        )
        for i in range(10)
    ]

    kf.routing.generic.route_bundle(
        c=c,
        start_ports=[p.base for p in start_ports],
        end_ports=[p.base for p in end_ports],
        ends=50_000,
        starts=50_000,
        routing_function=kf.routing.manhattan.route_smart,
        routing_kwargs={
            "bend90_radius": b90r,
            "separation": 4000,
        },
        placer_function=kf.routing.optical.place_manhattan,
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
    layers: Layers,
) -> None:
    c = kf.KCell(name="TEST_SMART_ROUTE_WAYPOINTS_TRANS_SORT")
    l_ = 15
    transformations = [kf.kdb.Trans(0, False, 0, i * 50_000) for i in range(l_)] + [
        kf.kdb.Trans(1, False, -15_000 - i * 50_000, 15 * 50_000) for i in range(l_)
    ]
    start_ports = [
        kf.Port(width=500, layer_info=layers.WG, kcl=c.kcl, trans=trans)
        for trans in transformations
    ]
    end_ports = [
        kf.Port(
            width=500,
            layer_info=layers.WG,
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
    layers: Layers,
) -> None:
    c = kf.KCell(name="TEST_SMART_ROUTE_WAYPOINTS_PTS_SORT")
    l_ = 15
    transformations = [kf.kdb.Trans(0, False, 0, i * 50_000) for i in range(l_)] + [
        kf.kdb.Trans(1, False, -15_000 - i * 50_000, 15 * 50_000) for i in range(l_)
    ]
    start_ports = [
        kf.Port(width=500, layer_info=layers.WG, kcl=c.kcl, trans=trans)
        for trans in transformations
    ]
    end_ports = [
        kf.Port(
            width=500,
            layer_info=layers.WG,
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
    layers: Layers,
) -> None:
    c = kf.KCell(name="TEST_SMART_ROUTE_WAYPOINTS_TRANS")
    l_ = 15
    transformations = [kf.kdb.Trans(0, False, 0, i * 50_000) for i in range(l_)] + [
        kf.kdb.Trans(1, False, -15_000 - i * 50_000, 15 * 50_000) for i in range(l_)
    ]
    start_ports = [
        kf.Port(width=500, layer_info=layers.WG, kcl=c.kcl, trans=trans)
        for trans in transformations
    ]
    start_ports.reverse()
    end_ports = [
        kf.Port(
            width=500,
            layer_info=layers.WG,
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
    layers: Layers,
) -> None:
    c = kf.KCell(name="TEST_SMART_ROUTE_WAYPOINTS_PTS")
    l_ = 15
    transformations = [kf.kdb.Trans(0, False, 0, i * 50_000) for i in range(l_)] + [
        kf.kdb.Trans(1, False, -15_000 - i * 50_000, 15 * 50_000) for i in range(l_)
    ]
    start_ports = [
        kf.Port(width=500, layer_info=layers.WG, kcl=c.kcl, trans=trans)
        for trans in transformations
    ]
    start_ports.reverse()
    end_ports = [
        kf.Port(
            width=500,
            layer_info=layers.WG,
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
    bend90_small: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
) -> None:
    c = kf.KCell(name="test_route_generic_reorient")

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
    bend90_small: kf.KCell,
    straight_factory_dbu: Callable[..., kf.KCell],
    layers: Layers,
) -> None:
    c = kf.KCell(name="test_placer_error")

    ps = kf.Port(name="start", width=500, layer_info=layers.WG, trans=kf.kdb.Trans.R0)
    pe = kf.Port(
        name="end",
        width=500,
        layer_info=layers.WG,
        trans=kf.kdb.Trans(2, False, 200_000, 0),
    )
    ps2 = kf.Port(
        name="start2", width=500, layer_info=layers.WG, trans=kf.kdb.Trans(0, 5_000)
    )
    pe2 = kf.Port(
        name="end2",
        width=500,
        layer_info=layers.WG,
        trans=kf.kdb.Trans(2, False, 200_000, 5_000),
    )
    ps3 = kf.Port(
        name="start3", width=500, layer_info=layers.WG, trans=kf.kdb.Trans(0, 10_000)
    )
    pe3 = kf.Port(
        name="end3",
        width=500,
        layer_info=layers.WG,
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


def test_clean_points() -> None:
    assert [
        kf.kdb.Point(0, 0),
        kf.kdb.Point(100, 0),
        kf.kdb.Point(100, 100),
    ] == kf.routing.manhattan.clean_points(
        [
            kf.kdb.Point(0, 0),
            kf.kdb.Point(10, 0),
            kf.kdb.Point(20, 0),
            kf.kdb.Point(30, 0),
            kf.kdb.Point(100, 0),
            kf.kdb.Point(100, 0),
            kf.kdb.Point(100, 100),
        ]
    )


def test_rf_bundle(layers: Layers) -> None:
    c = kf.KCell()

    layer = Layers()

    kf.kcl.infos = Layers()

    enc = kf.LayerEnclosure(
        sections=[(layer.METAL1EX, 500), (layer.METAL2EX, -200, 2000)],
        name="M1",
        main_layer=layer.METAL1,
    )

    xs_g = kf.kcl.get_icross_section(
        kf.SymmetricalCrossSection(width=40_000, enclosure=enc, name="G")
    )

    xs_s = kf.kcl.get_icross_section(
        kf.SymmetricalCrossSection(width=10_000, enclosure=enc, name="S")
    )

    def bend_circular(radius: int, cross_section: kf.CrossSection) -> kf.KCell:
        c = kf.cells.circular.bend_circular(
            radius=kf.kcl.to_um(radius),
            width=kf.kcl.to_um(cross_section.width),
            layer=cross_section.layer,
            enclosure=cross_section.enclosure,
        )
        c.kdb_cell.locked = False
        for p in c.ports:
            p.port_type = "electrical"
        c.kdb_cell.locked = True
        return c

    def wire(length: int, cross_section: kf.CrossSection) -> kf.KCell:
        c = kf.cells.straight.straight_dbu(
            width=cross_section.width,
            length=length,
            layer=cross_section.layer,
            enclosure=cross_section.enclosure,
        )
        c.kdb_cell.locked = False
        for p in c.ports:
            p.port_type = "electrical"
        c.kdb_cell.locked = True
        return c

    p1_s = kf.Port(
        name="G1",
        cross_section=xs_g,
        trans=kf.kdb.Trans(x=0, y=50_000),
        port_type="electrical",
    )
    p2_s = kf.Port(
        name="S",
        cross_section=xs_s,
        trans=kf.kdb.Trans(x=0, y=0),
        port_type="electrical",
    )
    p3_s = kf.Port(
        name="G2",
        cross_section=xs_g,
        trans=kf.kdb.Trans(x=0, y=-50_000),
        port_type="electrical",
    )

    dy = 1_000_000

    p1_e = kf.Port(
        name="PG1",
        cross_section=xs_g,
        trans=kf.kdb.Trans(rot=0, mirrx=False, x=-500_000, y=dy - 50_000),
        port_type="electrical",
    )
    p2_e = kf.Port(
        name="PS",
        cross_section=xs_s,
        trans=kf.kdb.Trans(rot=0, mirrx=False, x=-500_000, y=dy),
        port_type="electrical",
    )
    p3_e = kf.Port(
        name="PG1",
        cross_section=xs_g,
        trans=kf.kdb.Trans(rot=0, mirrx=False, x=-500_000, y=dy + 50_000),
        port_type="electrical",
    )

    ports = [p1_s, p2_s, p3_s, p1_e, p2_e, p3_e]

    b = kf.kdb.Box()
    for p in ports[:3]:
        b += p.trans.disp.to_p()

    b += kf.kdb.Point(-90_000, y=dy)

    end_ports = [p1_e, p2_e, p3_e]

    kf.routing.electrical.route_bundle_rf(
        c,
        start_ports=[p1_s, p2_s, p3_s],
        end_ports=end_ports,
        wire_factory=wire,
        bend_factory=bend_circular,
        layer=layer.METAL1,
        enclosure=enc,
        minimum_radius=50_000,
        bboxes=[b.enlarged(-1)],
    )

    c.add_ports(ports)
    c.shapes(c.kcl.layer(1, 0)).insert(b)


def test_sbend_routing() -> None:
    layer_infos = Layers()

    c = kf.KCell()
    c.kcl.infos = layer_infos

    ps: list[kf.Port] = []
    pe: list[kf.Port] = []

    enc = c.kcl.get_enclosure(
        kf.LayerEnclosure(
            sections=[(layer_infos.WGEX, 5000)], name="WG", main_layer=layer_infos.WG
        )
    )
    xs = c.kcl.get_icross_section(
        cross_section=kf.SymmetricalCrossSection(width=1000, enclosure=enc)
    )

    for i, ((x1, y1), (x2, y2)) in enumerate(
        [
            ((0, 100_000), (250_000, 90_000)),
            ((-120_000, 200_000), (250_000, 190_000)),
            ((-200_000, 0), (250_000, 200_000)),
            ((-100_000, 0), (250_000, 0)),
        ]
    ):
        ps.append(
            c.create_port(
                trans=kf.kdb.Trans(rot=i, mirrx=False, x=x1, y=y1),
                cross_section=xs,
                name=f"in_{i}",
            )
        )
        pe.append(
            c.create_port(
                trans=kf.kdb.Trans(rot=2, mirrx=False, x=x2, y=y2),
                cross_section=xs,
                name=f"out_{i}",
            )
        )

    def straight_factory(width: int, length: int) -> kf.KCell:
        return kf.cells.straight.straight_dbu(
            width=width, length=length, layer=layer_infos.WG, enclosure=enc
        )

    def sbend_factory(
        c: kf.ProtoTKCell[Any], offset: int, length: int, width: int
    ) -> kf.InstanceGroup:
        c = kf.KCell(base=c.base)
        ig = kf.InstanceGroup()

        sbend = c << kf.cells.euler.bend_s_euler(
            offset=c.kcl.to_um(offset),
            width=c.kcl.to_um(width),
            radius=10,
            layer=layer_infos.WG,
            enclosure=enc,
        )
        ig.insts.append(sbend)

        l_ = length - sbend.ibbox().width()
        ig.add_port(name="o1", port=sbend.ports["o1"])

        if l_ > 0:
            wg = c << straight_factory(width=width, length=l_)
            ig.insts.append(wg)
            wg.connect("o1", sbend.ports["o2"])
            ig.add_port(port=wg.ports["o2"], name="o2")
        else:
            ig.add_port(port=sbend.ports["o2"], name="o2")

        return ig

    kf.routing.optical.route_bundle(
        c=c,
        start_ports=ps,
        end_ports=pe,
        separation=5000,
        straight_factory=straight_factory,
        bend90_cell=kf.cells.euler.bend_euler(
            width=c.kcl.to_um(xs.width), radius=10, layer=layer_infos.WG, enclosure=enc
        ),
        sbend_factory=sbend_factory,
    )

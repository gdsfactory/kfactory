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


def test_route_backbone_bundle(
    LAYER: kf.LayerEnum,
    optical_port: kf.Port,
    bend90_euler: kf.KCell,
    straight_factory: Callable[..., kf.KCell],
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

    # pts = kf.routing.manhattan.route_bundle_manhattan(
    #     p_start,
    #     p_end,
    #     bend90_radius=radius,
    #     spacings=[0],
    #     start_straights=[0],
    #     end_straights=[0],
    # )
    # print(f"{pts=}")

    for pts in kf.routing.manhattan.backbone2bundle(
        [
            kf.kdb.Point(0, 0),
            kf.kdb.Point(0, 500_000),
            kf.kdb.Point(200_000, 500_000),
            kf.kdb.Point(200_000, -100_000),
            kf.kdb.Point(500_000, -100_000),
            kf.kdb.Point(500_000, 200_000),
            kf.kdb.Point(250_000, 200_000),
            kf.kdb.Point(250_000, 0),
        ],
        [1_000] * 6,
        spacing=5_000,
    ):
        print(pts)
        kf.routing.optical.place90(
            c,
            kf.Port(
                width=1_000, layer=LAYER.WG, trans=kf.kdb.Trans(1, False, pts[0].to_v())
            ),
            kf.Port(
                width=1_000,
                layer=LAYER.WG,
                trans=kf.kdb.Trans(1, False, pts[-1].to_v()),
            ),
            pts=pts,
            straight_factory=straight_factory,
            bend90_cell=bend90_euler,
        )
    c.show()


def test_route2bundle(
    LAYER: kf.LayerEnum,
    optical_port: kf.Port,
    bend90_euler: kf.KCell,
    straight_factory: Callable[..., kf.KCell],
) -> None:
    c = kf.KCell()

    # p1 = optical_port.copy()
    # p2 = optical_port.copy()

    p_start = [
        optical_port.copy(kf.kdb.Trans(0, False, 0, i * 200_000)) for i in range(5)
    ]
    p_end = [
        optical_port.copy(kf.kdb.Trans(0, False, 500_000, i * 200_000 + 1000_000))
        for i in range(5)
    ]

    radius = abs(bend90_euler.ports["o1"].x - bend90_euler["o2"].x)

    routes = kf.routing.manhattan.route_ports_to_bundle(
        [(p.trans, p.width) for p in p_start],
        radius,
        c.bbox(),
        5_000,
        bundle_base_point=kf.kdb.Point(375_000, 0),
    )
    for (
        p_s,
        p_e,
    ) in zip(
        p_start,
        p_end,
    ):
        pts = routes[p_s.trans]
        p = kf.Port(
            trans=kf.kdb.Trans(3, False, pts[0].to_v()), layer=LAYER.WG, width=1000
        )
        print(f"{pts=}")
        c.add_port(port=p)
        print(f"{p=}")
        c.add_port(port=p_s)
        print(f"{p_s=}")
        kf.routing.optical.place90(
            c,
            p2=p_s,
            p1=p,
            pts=pts,
            straight_factory=straight_factory,
            bend90_cell=bend90_euler,
        )

    c.show()


# def test_route_side(
#     LAYER: kf.LayerEnum,
#     optical_port: kf.Port,
#     bend90_euler: kf.KCell,
#     straight_factory: Callable[..., kf.KCell],
# ) -> None:
#     c = kf.KCell()

#     # p1 = optical_port.copy()
#     # p2 = optical_port.copy()

#     p_start = [
#         optical_port.copy(kf.kdb.Trans(1, False, i * 10_000, 0)) for i in range(5)
#     ]
#     p_end = [
#         optical_port.copy(kf.kdb.Trans(1, False, i * 10_000 + 1000_000, 0))
#         for i in range(5)
#     ]

#     radius = abs(bend90_euler.ports["o1"].x - bend90_euler["o2"].x)

#     # pts = kf.routing.manhattan.route_bundle_manhattan(
#     #     p_start,
#     #     p_end,
#     #     bend90_radius=radius,
#     #     spacings=[0],
#     #     start_straights=[0],
#     #     end_straights=[0],
#     # )
#     # print(f"{pts=}")

#     # for pts in kf.routing.manhattan.backbone2bundle(
#     #     [
#     #         kf.kdb.Point(0, 0),
#     #         kf.kdb.Point(0, 500_000),
#     #         kf.kdb.Point(200_000, 500_000),
#     #         kf.kdb.Point(200_000, -100_000),
#     #         kf.kdb.Point(500_000, -100_000),
#     #         kf.kdb.Point(500_000, 200_000),
#     #         kf.kdb.Point(250_000, 200_000),
#     #         kf.kdb.Point(250_000, 0),
#     #     ],
#     #     [1_000] * 6,
#     #     spacing=5_000,
#     # ):
#     #     print(pts)
#     #     kf.routing.optical.place90(
#     #         c,
#     #         kf.Port(
#     #             width=1_000, layer=LAYER.WG, trans=kf.kdb.Trans(1, False, pts[0].to_v())
#     #         ),
#     #         kf.Port(
#     #             width=1_000,
#     #             layer=LAYER.WG,
#     #             trans=kf.kdb.Trans(1, False, pts[-1].to_v()),
#     #         ),
#     #         pts=pts,
#     #         straight_factory=straight_factory,
#     #         bend90_cell=bend90_euler,
#     #     )

#     pts_dict = kf.routing.manhattan.route_ports_side(
#         1, [(p.trans, p.width) for p in p_start], [], radius, c.bbox(), 5000
#     )

#     print(f"{pts_dict=}")
#     print(f"{p_end=}")

#     for port_start, port_end in zip(p_start, p_end):
#         kf.routing.optical.place90(
#             c,
#             port_start,
#             port_end,
#             pts_dict[port_start.trans],
#             straight_factory=straight_factory,
#             bend90_cell=bend90_euler,
#         )

#     c.show()

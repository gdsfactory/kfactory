from functools import partial
from random import randint

import numpy as np

import kfactory as kf
from tests.conftest import Layers


def test_all_angle_bundle(layers: Layers) -> None:
    sf = partial(kf.cells.virtual.straight.virtual_straight, layer=layers.WG)
    bf = partial(
        kf.cells.virtual.euler.virtual_bend_euler, layer=layers.WG, radius=10, width=1
    )

    c = kf.KCell(name="test_all_angle_bundle")

    start_ports: list[kf.Port] = []
    end_ports: list[kf.Port] = []
    r = 50
    n = 3
    _l = 9

    for i in range(_l):
        # for i in range(1):
        a = (n - i) * 15
        a_rad = np.deg2rad(a)
        ae = 270 - n + i * 15
        ae_rad = np.deg2rad(ae)
        start_ports.append(
            c.create_port(
                name=f"s{i}",
                dcplx_trans=kf.kdb.DCplxTrans(
                    1, a, False, -500 + r * np.cos(a_rad), -100 + r * np.sin(a_rad)
                ),
                layer=c.kcl.find_layer(layers.WG),
                width=c.kcl.to_dbu(1),
            )
        )
        end_ports.append(
            c.create_port(
                name=f"s{i + _l}",
                dcplx_trans=kf.kdb.DCplxTrans(
                    1, ae, False, 2510 + r * np.cos(ae_rad), 2410 + r * np.sin(ae_rad)
                ),
                layer=c.kcl.find_layer(layers.WG),
                width=c.kcl.to_dbu(1),
            )
        )
    backbone = [
        kf.kdb.DPoint(750, -550),
        kf.kdb.DPoint(1000, 550),
        kf.kdb.DPoint(1000, 1200),
        kf.kdb.DPoint(2800, 1950),
    ]
    kf.routing.aa.optical.route_bundle(
        c,
        start_ports=start_ports,
        end_ports=end_ports,
        backbone=backbone,
        separation=[randint(1, 5) for _ in range(_l)],
        straight_factory=sf,
        bend_factory=bf,
    )

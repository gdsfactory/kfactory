from functools import partial

from random import randint

import kfactory as kf

ps: list[kf.Port] = []
pe: list[kf.Port] = []

c = kf.KCell()

for angle in [1, 2, 3, 0]:
    for xi in range(5):
        ts = (
            kf.kdb.Trans(angle, False, 0, 0)
            * kf.kdb.Trans(100_000, -50_000)
            * kf.kdb.Trans(randint(0, 100), randint(0, 100) + xi * 10_000)
        )
        ps.append(
            c.create_port(
                name="i" + str((angle + 1) * 5 + xi),
                trans=ts,
                width=1000,
                layer=kf.kcl.layout.layer(1, 0),
            )
        )
        # te = kf.kdb.Trans(0, False, -500_000, 200_000 - 50_000 * angle) * kf.kdb.Trans(
        #     randint(0, 100), randint(0, 100) - xi * 10_000
        # )
        # te = kf.kdb.Trans(2, False, 500_000, -000_000 + 50_000 * angle) * kf.kdb.Trans(
        #     randint(0, 100), randint(0, 100) - xi * 10_000
        # )
        te = kf.kdb.Trans(1, False, -200_000 + 50_000 * angle, -200_000) * kf.kdb.Trans(
            randint(0, 100), randint(0, 100) - xi * 10_000
        )
        # te = kf.kdb.Trans(3, False, 500_000 - 50_000 * angle, 500_000) * kf.kdb.Trans(
        #     randint(0, 100), randint(0, 100) - xi * 10_000
        # )
        pe.append(
            c.create_port(
                name="o" + str((angle + 1) * 5 + xi),
                trans=te,
                width=1000,
                layer=kf.kcl.layout.layer(1, 0),
            )
        )
for angle in [-2, -1, 0, 1]:
    for xi in range(5):
        ts = (
            kf.kdb.Trans(angle, False, 2_000_000, 0)
            * kf.kdb.Trans(100_000, -50_000)
            * kf.kdb.Trans(randint(0, 100), randint(0, 100) + xi * 10_000)
        )
        ps.append(
            c.create_port(
                name="i" + str((angle + 1) * 5 + xi),
                trans=ts,
                width=1000,
                layer=kf.kcl.layout.layer(1, 0),
            )
        )
        # te = kf.kdb.Trans(0, False, 1_500_000, 200_000 - 50_000 * angle) * kf.kdb.Trans(
        #     randint(0, 100), randint(0, 100) - xi * 10_000
        # )
        te = kf.kdb.Trans(2, False, 2_500_000, 00_000 + 50_000 * angle) * kf.kdb.Trans(
            randint(0, 100), randint(0, 100) - xi * 10_000
        )
        # te = kf.kdb.Trans(
        #     1, False, 1_500_000 + 50_000 * angle, -200_000
        # ) * kf.kdb.Trans(randint(0, 100), randint(0, 100) - xi * 10_000)
        # te = kf.kdb.Trans(3, False, 500_000 - 50_000 * angle, 500_000) * kf.kdb.Trans(
        #     randint(0, 100), randint(0, 100) - xi * 10_000
        # )
        pe.append(
            c.create_port(
                name="o" + str((angle + 1) * 5 + xi),
                trans=te,
                width=1000,
                layer=kf.kcl.layout.layer(1, 0),
            )
        )


for angle in [0]:
    for xi in range(5):
        ts = (
            kf.kdb.Trans(angle, False, 4_000_000, 0)
            * kf.kdb.Trans(100_000, -50_000)
            * kf.kdb.Trans(randint(0, 100), randint(0, 100) + xi * 10_000)
        )
        ps.append(
            c.create_port(
                name="i" + str((angle + 1) * 5 + xi),
                trans=ts,
                width=1000,
                layer=kf.kcl.layout.layer(1, 0),
            )
        )
        # te = kf.kdb.Trans(0, False, 4_500_000, 200_000 - 50_000 * angle) * kf.kdb.Trans(
        #     randint(0, 100), randint(0, 100) - xi * 10_000
        # )
        # te = kf.kdb.Trans(2, False, 4_500_000, 00_000 + 50_000 * angle) * kf.kdb.Trans(
        #     randint(0, 100), randint(0, 100) - xi * 10_000
        # )
        te = kf.kdb.Trans(
            1, False, 3_500_000 + 50_000 * angle, -200_000
        ) * kf.kdb.Trans(randint(0, 100), randint(0, 100) - xi * 10_000)
        # te = kf.kdb.Trans(3, False, 4_500_000 - 50_000 * angle, 500_000) * kf.kdb.Trans(
        #     randint(0, 100), randint(0, 100) - xi * 10_000
        # )
        pe.append(
            c.create_port(
                name="o" + str((angle + 1) * 5 + xi),
                trans=te,
                width=1000,
                layer=kf.kcl.layout.layer(1, 0),
            )
        )

b = kf.cells.circular.bend_circular(width=1, radius=10, layer=kf.kcl.layer(1, 0))
s = partial(kf.cells.straight.straight_dbu, width=1000, layer=kf.kcl.layer(1, 0))

routes = kf.routing.optical.route_bundle(
    c, start_ports=ps, end_ports=pe, bend90_cell=b, separation=2000, straight_factory=s
)

# routers = kf.routing.manhattan.route_smart(
#     start_ports=ps, end_ports=pe, bend90_radius=10_000, separation=2000
# )

# for p1, p2, router in zip(ps, pe, routers):
#     kf.routing.optical.place90(
#         c, p1=p1, p2=p2, pts=router.start.pts, straight_factory=s, bend90_cell=b
#     )

c.show()

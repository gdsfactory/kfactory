import kfactory as kf
from functools import partial
from kfactory.gpdk import cells


route_sc = partial(
    kf.routing.optical.route,
    straight_factory=cells.straight_sc,
    bend90_cell=cells.bend_euler_sc,
)


if __name__ == "__main__":
    c = kf.KCell()

    sl = c << cells.straight_sc()
    sr = c << cells.straight_sc()
    sr.d.move((50, 50))

    route_sc(
        c, p1=sl.ports["o2"], p2=sr.ports["o1"], straight_factory=cells.straight_sc
    )
    c.show()

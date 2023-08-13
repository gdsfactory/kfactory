"""Cell definitions for generic PDK."""
from functools import partial

import kfactory as kf
from kfactory.gpdk.layers import LAYER

nm = 1e-3


class Tech:
    """Technology parameters."""

    width_sc: float = 500 * nm
    radius_sc: float = 10


TECH = Tech()

straight_sc = partial(
    kf.cells.straight.straight, length=10, width=TECH.width_sc, layer=LAYER.WG
)
straight_dbu_sc = partial(
    kf.cells.straight.straight_dbu, length=10e3, width=int(TECH.width_sc * 1e3), layer=LAYER.WG
)
bend_euler_sc = partial(
    kf.cells.euler.bend_euler,
    width=TECH.width_sc,
    layer=LAYER.WG,
    radius=TECH.radius_sc,
)


if __name__ == "__main__":
    c = straight_sc()
    c = bend_euler_sc()
    c.show()

# This script defines and displays a reusable component for a straight optical waveguide.
# It also includes a secondary "exclusion" layer.
# The function creates a KCell and draws two centered rectangles.
# It then creates and defines two ports, which store the location, orientation and width.
# Also automatically renames ports. E.g. "o1" and "o2".
# It then allows the component to be opened in KLayout, through the kf.show function.

from layers import LAYER

import kfactory as kf


@kf.cell
def straight(width: int, length: int, width_exclude: int) -> kf.KCell:
    """Waveguide: Silicon on 1/0, Silicon exclude on 1/1"""
    c = kf.KCell()
    c.shapes(c.kcl.find_layer(LAYER.SI)).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
    c.shapes(c.kcl.find_layer(LAYER.SIEXCLUDE)).insert(
        kf.kdb.Box(0, -width_exclude // 2, length, width_exclude // 2)
    )

    c.create_port(
        name="1", trans=kf.kdb.Trans(2, False, 0, 0), width=width, layer_info=LAYER.SI
    )
    c.create_port(
        name="2",
        trans=kf.kdb.Trans(0, False, length, 0),
        width=width,
        layer_info=LAYER.SI,
    )

    c.auto_rename_ports()

    return c


if __name__ == "__main__":
    kf.show(straight(2000, 50000, 5000))

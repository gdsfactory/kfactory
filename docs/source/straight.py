# This script defines and displays a reusable component for a straight optical waveguide.
# It also includes a secondary "exclusion" layer.
# The function creates a KCell and draws two centered rectangles.
# It then creates and defines two ports, which store the location, orientation and width.
# Also automatically renames ports. E.g. "o1" and "o2".
# It then allows the component to be opened in KLayout, through the kf.show function.

from layers import LAYER

import kfactory as kf

# LAYER.SI: Refers to the Silicon layer (e.g., GDSII layer 1, datatype 0),
# which forms the physical core of the waveguide where light is confined.
# LAYER.SIEXCLUDE: Refers to an Exclusion layer (e.g., GDSII layer 1, datatype 1).
# This is a metadata layer used for Design Rule Checking (DRC).
# It defines a "keep-out" zone around the waveguide,
# essentially instructing automated tools not to place other silicon structures within this boundary.
# This is done to prevent performance degradation from optical crosstalk.(Two light sources interfering with one another)
# Then, two rectangular shapes are drawn: the core and the wider exclusion zone. They are created with kf.kdb.Box(left, bottom, right, top):
# By using -width // 2 and width // 2 for the bottom and top coordinates, the waveguide is centered vertically on the y=0 axis
# trans=kf.kdb.Trans(2, False, 0, 0): The Trans object defines the port's transformation. The arguments are (rotation, mirror, x, y), this means:
# Input port 1 is rotated by 180 degrees(2), not mirrored(false) and at the default 0 position on the x and y-axis (0, 0)
# Input port 2 is not rotated and not mirrored.
# c.auto_rename_ports(): This utility standardizes port names based on their location (e.g., left port becomes "o1", right becomes "o2")
# if __name__ == "__main__": This creates a condition, it will only function when directly executed.
# The result is then shown via kf.show and has the following physical dimensions:
# width: 2000 dbu = 2.0 µm
# length: 50000 dbu = 50.0 µm
# width_exclude: 5000 dbu = 5.0 µm


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

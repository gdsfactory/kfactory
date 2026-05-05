# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# This script builds a composite cell by taking a circular bend and a straight waveguide, snapping them together end-to-end,
# and then presenting the combined shape as a single new component with its own input and output ports.
# After creating a new instance of a bend and a new instance of a waveguide and placing it into the cell,
# it automatically connects the ports "o1" and "o2"
# Finally a cleanup is done:
# c.auto_rename_ports(): This renames the new ports "1" and "2" to a standard convention, "o1" and "o2" in this instance, based on their position.
# c.draw_ports(): This adds visual markers to the layout, making it easy to see where the ports are.
# kf.show(composite_cell()): When the script is run, this line calls the function to build the cell and then displays the final,
# connected component in the KLayout viewer.

from layers import LAYER, si_enc
from straight import straight

import kfactory as kf


@kf.cell
def composite_cell() -> kf.KCell:
    c = kf.KCell()

    bend = c.create_inst(
        kf.cells.circular.bend_circular(
            1000 * c.kcl.dbu, 20000 * c.kcl.dbu, LAYER.SI, enclosure=si_enc
        )  # the standard kf.cells are in um, so we need to convert it to dbu
    )
    wg = c << straight(1000, 5000, 5000)

    wg.connect("o1", bend, "o2")

    c.add_port(name="1", port=bend.ports["o1"])
    c.add_port(name="2", port=wg.ports["o2"])

    c.auto_rename_ports()

    c.draw_ports()

    return c


if __name__ == "__main__":
    kf.show(composite_cell())

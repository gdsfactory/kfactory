# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: kernel_name
#     language: python
#     name: kernel_name
# ---

from layers import LAYER, si_enc
from straight import straight

import kfactory as kf


@kf.cell
def composite_cell() -> kf.KCell:
    c = kf.KCell()

    bend = c.create_inst(
        kf.cells.circular.bend_circular(
            1000 * c.kcl.dbu, 20000 * c.kcl.dbu, LAYER.SI, enclosure=si_enc
        )  # the standard kf.cells are in um, so we need to convert to dbu
    )
    wg = c << straight(1000, 5000, 5000)

    wg.align("o1", bend, "o2")

    c.add_port(name="1", port=bend.ports["o1"])
    c.add_port(name="2", port=wg.ports["o2"])

    c.auto_rename_ports()

    c.draw_ports()

    return c


if __name__ == "__main__":
    kf.show(composite_cell())

from layers import LAYER, si_enc
from waveguide import waveguide

import kfactory as kf


@kf.cell
def composite_cell() -> kf.Cell:
    c = kf.Cell()

    bend = c.create_inst(
        kf.cells.circular.bend_circular(
            1000 * c.klib.dbu, 20000 * c.klib.dbu, LAYER.SI, enclosure=si_enc
        )  # the standard kf.cells are in um, so we need to convert to dbu
    )
    wg = c << waveguide(1000, 5000, 5000)

    wg.connect("o1", bend, "o2")

    c.add_port(name="1", port=bend.ports["o1"])
    c.add_port(name="2", port=wg.ports["o2"])

    c.autorename_ports()

    c.draw_ports()

    return c


if __name__ == "__main__":
    kf.show(composite_cell())

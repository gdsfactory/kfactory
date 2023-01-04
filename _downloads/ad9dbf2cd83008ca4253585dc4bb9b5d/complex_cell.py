from layers import LAYERS, si_enc
from waveguide import waveguide

import kfactory as kf


@kf.autocell
def composite_cell() -> kf.KCell:
    c = kf.KCell()

    bend = c.create_inst(
        kf.pcells.circular.bend_circular(
            1000, 20000, LAYERS["Silicon"], enclosure=si_enc
        )
    )
    wg = c << waveguide(1000, 5000, 3000)

    wg.connect("W0", bend, "N0")

    c.add_port(name="1", port=bend.ports["W0"])
    c.add_port(name="2", port=wg.ports["E0"])

    c.autorename_ports()

    c.draw_ports()

    return c


if __name__ == "__main__":
    kf.show(composite_cell())

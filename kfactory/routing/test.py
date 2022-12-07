from layers import LAYERS, si_enc

import kfactory as kf


@kf.autocell
def waveguide(width: int, length: int, width_exclude: int) -> kf.KCell:
    """Waveguide: Silicon on 1/0, Silicon exclude on 1/1"""
    c = kf.KCell()
    c.shapes(LAYERS["Silicon"]).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
    c.shapes(LAYERS["Silicon.Exclude"]).insert(
        kf.kdb.Box(0, -width_exclude // 2, length, width_exclude // 2)
    )

    c.create_port(
        name="1",
        trans=kf.kdb.Trans(2, False, 0, 0),
        width=width,
        layer=LAYERS["Silicon"],
    )
    c.create_port(
        name="2",
        trans=kf.kdb.Trans(0, False, length, 0),
        width=width,
        layer=LAYERS["Silicon"],
    )

    c.autorename_ports()

    return c


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
    composite_cell().write("waveguide.gds")
    # kf.show(waveguide(2000, 50000, 5000))
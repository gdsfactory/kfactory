import kfactory as kf
import pytest
from enum import IntEnum


def _l(layer: int, datatype: int):
    return kf.library.layer(layer, datatype)


class LAYER(IntEnum):
    SI = _l(1, 0)
    M1 = _l(2, 0)

    def __str__(self):
        return self.name


@kf.autocell
def waveguide(width: int, length: int, layer: int) -> kf.KCell:
    c = kf.KCell()

    c.shapes(LAYER.SI).insert(kf.kdb.Box(0, -width // 2, length, width // 2))

    c.create_port(
        name="o1", trans=kf.kdb.Trans(2, False, 0, 0), width=width, layer=layer
    )
    c.create_port(
        name="o2", trans=kf.kdb.Trans(0, False, length, 0), width=width, layer=layer
    )
    return c


@pytest.fixture()
def wg():
    return waveguide(1000, 20000, LAYER.SI)


@pytest.fixture()
@kf.autocell
def wg_floating_off_grid():
    c = kf.KCell()
    dbu = c.library.dbu

    p1 = kf.kcell.DPort(
        width=10 + dbu / 2,
        name="o1",
        trans=kf.kdb.DTrans(2, False, dbu / 2, 0),
        layer=LAYER.SI,
    )
    p2 = kf.kcell.DPort(
        width=10 + dbu / 2,
        name="o2",
        trans=kf.kdb.DTrans(0, False, 20 + dbu, 0),
        layer=LAYER.SI,
    )
    c.shapes(LAYER.SI).insert(kf.kdb.DBox(p1.x, -p1.width / 2, p2.x, p1.width / 2))
    c.add_port(p1)
    c.add_port(p2)

    c.draw_ports()
    return c


def test_waveguide():
    waveguide(1000, 20000, LAYER.SI)


def test_settings():
    c = waveguide(1000, 20000, LAYER.SI)

    assert c.settings["length"] == 20000
    assert c.settings["width"] == 1000
    assert c.name == "waveguide_W1000_L20000_LSI"


def test_connect_cplx_port():
    c = kf.KCell()
    wg1 = c << waveguide(1000, 20000, LAYER.SI)
    port = kf.kcell.DCplxPort(
        width=1000,
        layer=LAYER.SI,
        name="cplxp1",
        trans=kf.kdb.DCplxTrans(1, 30, False, 5, 10),
    )
    wg1.connect_cplx("o1", port)


def test_connect_cplx_inst():
    c = kf.KCell()
    wg1 = c << waveguide(1000, 20000, LAYER.SI)
    wg2 = c << waveguide(1000, 20000, LAYER.SI)
    wg1.transform(kf.kdb.DCplxTrans(1, 30, False, 5, 10))
    wg2.connect_cplx("o1", wg1, "o2")

    c.add_port(wg1.ports["o1"])
    c.add_port(wg2.ports["o2"])
    c.flatten()


def test_floating(wg_floating_off_grid):
    c = kf.KCell()

    wg1 = c << wg_floating_off_grid
    wg2 = c << wg_floating_off_grid
    wg2.connect("o2", wg1, "o1")
    # c.flatten()
    kf.show(c)


def test_connect_integer(wg):
    c = kf.KCell()

    wg1 = c << wg
    wg2 = c << wg
    wg2.connect("o1", wg2, "o1")

    assert wg2.ports["o1"].trans == kf.kdb.Trans(0, False, 0, 0)


# if __name__ == "__main__":
#     test_waveguide()

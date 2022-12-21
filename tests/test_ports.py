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

    c.shapes(LAYER.SI).insert(kf.kdb.Box(-width // 2, 0, width // 2, length // 2))

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


def test_waveguide():
    waveguide(1000, 20000, LAYER.SI)


def test_settings():
    c = waveguide(1000, 20000, LAYER.SI)

    assert c.settings["length"] == 20000
    assert c.settings["width"] == 1000
    assert c.name == "waveguide_W1000_L20000_LSI"


def test_connection():
    c = kf.KCell()


def test_connect_integer(wg):
    c = kf.KCell()

    wg1 = c << wg
    wg2 = c << wg
    wg2.connect("o1", wg2, "o1")

    assert wg2.ports["o1"].trans == kf.kdb.Trans(0, False, 0, 0)


if __name__ == "__main__":
    test_waveguide()

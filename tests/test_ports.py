import kfactory as kf
import pytest
import re


@kf.cell
def waveguide(width: int, length: int, layer: int) -> kf.KCell:
    c = kf.KCell()

    c.shapes(layer).insert(kf.kdb.Box(0, -width // 2, length, width // 2))

    c.create_port(
        name="o1", trans=kf.kdb.Trans(2, False, 0, 0), width=width, layer=layer
    )
    c.create_port(
        name="o2", trans=kf.kdb.Trans(0, False, length, 0), width=width, layer=layer
    )
    return c


@pytest.fixture()
def wg(LAYER):
    return waveguide(1000, 20000, LAYER.WG)


@pytest.fixture()
@kf.cell
def wg_floating_off_grid(LAYER):
    with pytest.raises(AssertionError):
        c = kf.KCell()
        dbu = c.kcl.dbu

        p1 = kf.kcell.Port(
            dwidth=10 + dbu / 2,
            name="o1",
            dcplx_trans=kf.kdb.DCplxTrans(1, 180, False, dbu / 2, 0),
            layer=LAYER.WG,
        )
        p2 = kf.kcell.Port(
            dwidth=10 + dbu / 2,
            name="o2",
            dcplx_trans=kf.kdb.DCplxTrans(1, 0, False, 20 + dbu, 0),
            layer=LAYER.WG,
        )
        c.shapes(LAYER.WG).insert(kf.kdb.DBox(p1.x, -p1.width / 2, p2.x, p1.width / 2))

        c.add_port(p1)
        c.add_port(p2)

        kf.config.logfilter.regex = None

    return c


def test_waveguide(LAYER):
    waveguide(1000, 20000, LAYER.WG)


def test_settings(LAYER):
    c = waveguide(1000, 20000, LAYER.WG)

    assert c.settings["length"] == 20000
    assert c.settings["width"] == 1000
    assert c.name == "waveguide_W1000_L20000_LWG"


def test_connect_cplx_port(LAYER):
    c = kf.KCell()
    wg1 = c << waveguide(1000, 20000, LAYER.WG)
    port = kf.kcell.Port(
        dwidth=1,
        layer=LAYER.WG,
        name="cplxp1",
        dcplx_trans=kf.kdb.DCplxTrans(1, 30, False, 5, 10),
    )
    wg1.connect("o1", port)


def test_connect_cplx_inst(LAYER):
    c = kf.KCell()

    wg1 = c << waveguide(1000, 20000, LAYER.WG)
    wg2 = c << waveguide(1000, 20000, LAYER.WG)
    wg1.transform(kf.kdb.DCplxTrans(1, 30, False, 5, 10))
    wg2.connect("o1", wg1, "o2")
    kf.config.logfilter.regex = f"Port ({re.escape(str(wg1.ports['o1']))}|{re.escape(str(wg2.ports['o2']))}) is not an integer based port, converting to integer based"

    c.add_port(wg1.ports["o1"])
    c.add_port(wg2.ports["o2"])

    kf.config.logfilter.regex = None
    c.flatten()


def test_connect_integer(wg):
    c = kf.KCell()

    wg1 = c << wg
    wg2 = c << wg
    wg2.connect("o1", wg1, "o1")

    assert wg2.ports["o1"].trans == kf.kdb.Trans(0, False, 0, 0)

import pytest
import kfactory as kf
from functools import partial

# kf.config.logfilter.level = "ERROR"


class LAYER_CLASS(kf.LayerEnum):
    kcl = kf.constant(kf.kcl)
    WG = (1, 0)
    WGCLAD = (111, 0)
    WGEXCLUDE = (1, 1)
    WGCLADEXCLUDE = (111, 1)


@pytest.fixture
def LAYER():
    return LAYER_CLASS


@pytest.fixture
def wg_enc(LAYER):
    return kf.LayerEnclosure(name="WGSTD", sections=[(LAYER.WGCLAD, 0, 2000)])


@pytest.fixture
def straight_factory(LAYER, wg_enc):
    return partial(kf.cells.dbu.straight, layer=LAYER.WG, enclosure=wg_enc)


@pytest.fixture
def straight(LAYER, wg_enc) -> kf.KCell:
    return kf.cells.straight.straight(
        width=0.5, length=1, layer=LAYER.WG, enclosure=wg_enc
    )


@pytest.fixture
def straight_blank(LAYER):
    return kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)


@pytest.fixture
def bend90(LAYER, wg_enc) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180(LAYER, wg_enc) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def bend90_euler(LAYER, wg_enc) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180_euler(LAYER, wg_enc) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def taper(LAYER, wg_enc) -> kf.KCell:
    c = kf.cells.taper.taper(
        width1=0.5,
        width2=1,
        length=10,
        layer=LAYER.WG,
        enclosure=wg_enc,
    )
    c = c.dup()
    c.name = "taper"
    return c


@pytest.fixture
def optical_port(LAYER):
    return kf.Port(
        name="o1",
        trans=kf.kdb.Trans.R0,
        layer=LAYER.WG,
        width=1000,
        port_type="optical",
    )


@pytest.fixture
def cells(bend90, bend180, bend90_euler, taper, straight) -> list[kf.KCell]:
    return [
        bend90,
        bend180,
        bend90_euler,
        taper,
        straight,
    ]


# @pytest.fixture
# def pdk(LAYER, straight_factory, wg_enc):
#     pdk = kf.pdk.Pdk(
#         layers=LAYER,
#         name="TEST_PDK",
#         cell_factories={
#             "wg": straight_factory,
#             "bend": kf.cells.circular.bend_circular,
#             "bend_euler": kf.cells.euler.bend_euler,
#             "taper": kf.cells.taper.taper,
#             "bezier": kf.cells.bezier.bend_s,
#             "straight": straight_factory,
#         },
#         layer_enclosures={"wg": wg_enc},
#     )
#     # pdk.register_cells(straight=straight_factory)
#     # pdk.register_enclosures(wg=wg_enc)
#     # pdk.activate()
#     return pdk


@pytest.fixture
def pdk() -> kf.KCLayout:
    kcl = kf.KCLayout("Test_PDK")
    return kcl


# @pytest.fixture
# def wg():
#     return LAYER.WG

from functools import partial

import pytest

import kfactory as kf
from collections.abc import Callable

kf.config.logfilter.level = kf.conf.LogLevel.ERROR


class LAYER_CLASS(kf.LayerEnum):
    kcl = kf.constant(kf.kcl)
    WG = (1, 0)
    WGCLAD = (111, 0)
    WGEXCLUDE = (1, 1)
    WGCLADEXCLUDE = (111, 1)


@pytest.fixture
def LAYER() -> type[kf.LayerEnum]:
    return LAYER_CLASS


@pytest.fixture
def wg_enc(LAYER: kf.LayerEnum) -> kf.LayerEnclosure:
    return kf.LayerEnclosure(name="WGSTD", sections=[(LAYER.WGCLAD, 0, 2000)])


@pytest.fixture
def straight_factory(
    LAYER: kf.LayerEnum, wg_enc: kf.LayerEnclosure
) -> Callable[..., kf.KCell]:
    return partial(kf.cells.dbu.straight, layer=LAYER.WG, enclosure=wg_enc)


@pytest.fixture
def straight(LAYER: kf.LayerEnum, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.straight.straight(
        width=0.5, length=1, layer=LAYER.WG, enclosure=wg_enc
    )


@pytest.fixture
def straight_blank(LAYER: kf.LayerEnum) -> kf.KCell:
    return kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)


@pytest.fixture
def bend90(LAYER: kf.LayerEnum, wg_enc: kf.LayerEnum) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180(LAYER: kf.LayerEnum, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def bend90_euler(LAYER: kf.LayerEnum, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180_euler(LAYER: kf.LayerEnum, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def taper(LAYER: kf.LayerEnum, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    if kf.kcl.cell("taper") is not None:
        c = kf.cells.taper.taper(
            width1=0.5,
            width2=1,
            length=10,
            layer=LAYER.WG,
            enclosure=wg_enc,
        )
        c = c.dup()
        c.name = "taper"
    else:
        c = kf.kcl["taper"]
    return c


@pytest.fixture
def optical_port(LAYER: kf.LayerEnum) -> kf.Port:
    return kf.Port(
        name="o1",
        trans=kf.kdb.Trans.R0,
        layer=LAYER.WG,
        width=1000,
        port_type="optical",
    )


@pytest.fixture
def cells(
    bend90: kf.KCell,
    bend180: kf.KCell,
    bend90_euler: kf.KCell,
    taper: kf.KCell,
    straight: kf.KCell,
) -> list[kf.KCell]:
    return [
        bend90,
        bend180,
        bend90_euler,
        taper,
        straight,
    ]


@pytest.fixture
def pdk(LAYER: LAYER_CLASS) -> kf.KCLayout:
    layerstack = kf.LayerStack(
        wg=kf.kcell.LayerLevel(
            layer=LAYER.WG,
            thickness=0.22,
            zmin=0,
            material="si",
            info=kf.kcell.Info(mesh_order=1),
        ),
        clad=kf.kcell.LayerLevel(
            layer=LAYER_CLASS.WGCLAD, thickness=3, zmin=0.22, material="sio2"
        ),
    )
    kcl = kf.KCLayout("Test_PDK", layer_stack=layerstack)
    return kcl

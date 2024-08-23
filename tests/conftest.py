from functools import partial

import pytest

import kfactory as kf
from collections.abc import Callable
from dataclasses import dataclass

# kf.config.logfilter.level = kf.conf.LogLevel.ERROR


# class LAYER_CLASS(kf.LayerEnum):
#     kcl = kf.constant(kf.kcl)
#     WG = (1, 0)
#     WGCLAD = (111, 0)
#     WGEXCLUDE = (1, 1)
#     WGCLADEXCLUDE = (111, 1)


class Layers(kf.kcell.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
    WGEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)
    WGCLADEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 1)
    FILL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
    FILL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
    FILL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10, 0)


# kf.kcl.layers = kf.kcl.set_layers_from_infos(name="LAYER", layers=Layers())
# kf.kcl.layer_infos = Layers()

kf.kcl.infos = Layers()


@pytest.fixture(scope="module")
def LAYER() -> Layers:
    return Layers()


@pytest.fixture
def wg_enc(LAYER: Layers) -> kf.LayerEnclosure:
    return kf.LayerEnclosure(name="WGSTD", sections=[(LAYER.WGCLAD, 0, 2000)])


@pytest.fixture
def straight_factory_dbu(
    LAYER: Layers, wg_enc: kf.LayerEnclosure
) -> Callable[..., kf.KCell]:
    return partial(kf.cells.straight.straight_dbu, layer=LAYER.WG, enclosure=wg_enc)


@pytest.fixture
def straight_factory(
    LAYER: Layers, wg_enc: kf.LayerEnclosure
) -> Callable[..., kf.KCell]:
    return partial(kf.cells.straight.straight, layer=LAYER.WG, enclosure=wg_enc)


@pytest.fixture
def straight(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.straight.straight(
        width=0.5, length=1, layer=LAYER.WG, enclosure=wg_enc
    )


@pytest.fixture
def straight_blank(LAYER: Layers) -> kf.KCell:
    return kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)


@pytest.fixture
def bend90(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=0.5, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend90_small(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=0.5, radius=5, layer=LAYER.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=0.5, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def bend90_euler(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=0.5, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180_euler(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=0.5, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def taper(LAYER: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    if kf.kcl.layout.cell("taper") is None:
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
def optical_port(LAYER: Layers) -> kf.Port:
    return kf.Port(
        name="o1",
        trans=kf.kdb.Trans.R0,
        layer=kf.kcl.find_layer(LAYER.WG),
        width=500,
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
def pdk() -> kf.KCLayout:
    layerstack = kf.LayerStack(
        wg=kf.kcell.LayerLevel(
            layer=Layers().WG,
            thickness=0.22,
            zmin=0,
            material="si",
            info=kf.kcell.Info(mesh_order=1),
        ),
        clad=kf.kcell.LayerLevel(
            layer=Layers().WGCLAD, thickness=3, zmin=0.22, material="sio2"
        ),
    )
    kcl = kf.KCLayout("Test_PDK", infos=Layers, layer_stack=layerstack)
    return kcl


@pytest.fixture
@kf.kcl.cell
def fill_cell() -> kf.KCell:
    fc = kf.KCell()
    fc.shapes(fc.kcl.find_layer(Layers().WGCLAD)).insert(kf.kdb.DBox(20, 40))
    fc.shapes(fc.kcl.find_layer(Layers().WGCLAD)).insert(kf.kdb.DBox(30, 15))
    return fc

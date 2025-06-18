from collections.abc import Callable, Iterator
from functools import partial
from pathlib import Path
from threading import RLock

import pytest

import kfactory as kf


class Layers(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
    WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)
    WGCLADEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 1)
    FILL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
    FILL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
    FILL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10, 0)
    METAL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(20, 0)
    METAL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(22, 0)
    METAL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(24, 0)
    METAL1EX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(20, 1)
    METAL2EX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(22, 1)
    METAL3EX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(24, 1)
    VIA1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(21, 0)
    VIA2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(23, 0)


kf.kcl.infos = Layers()


cell_copy_lock = RLock()


@pytest.fixture(scope="module")
def layers() -> Layers:
    return Layers()


@pytest.fixture
def kcl() -> kf.KCLayout:
    import random
    import string

    random_name = "".join(random.choices(string.ascii_letters, k=10))
    kcl = kf.KCLayout(name=random_name)
    kcl.infos = Layers()
    return kcl


@pytest.fixture
def wg_enc(layers: Layers) -> kf.LayerEnclosure:
    return kf.LayerEnclosure(name="WGSTD", sections=[(layers.WGCLAD, 0, 2000)])


@pytest.fixture
def straight_factory_dbu(
    layers: Layers, wg_enc: kf.LayerEnclosure
) -> Callable[..., kf.KCell]:
    return partial(kf.cells.straight.straight_dbu, layer=layers.WG, enclosure=wg_enc)


@pytest.fixture
def straight_factory(
    layers: Layers, wg_enc: kf.LayerEnclosure
) -> Callable[..., kf.KCell]:
    return partial(kf.cells.straight.straight, layer=layers.WG, enclosure=wg_enc)


@pytest.fixture
def straight(layers: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.straight.straight(
        width=0.5, length=1, layer=layers.WG, enclosure=wg_enc
    )


@pytest.fixture
def straight_blank(layers: Layers) -> kf.KCell:
    return kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)


@pytest.fixture
def bend90(layers: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=0.5, radius=10, layer=layers.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend90_small(layers: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=0.5, radius=5, layer=layers.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180(layers: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=0.5, radius=10, layer=layers.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def bend90_euler(layers: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=0.5, radius=10, layer=layers.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend90_euler_small(layers: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=0.1, radius=10, layer=layers.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180_euler(layers: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=0.5, radius=10, layer=layers.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def taper(layers: Layers, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    return taper_cell(layers=layers.WG, wg_enc=wg_enc)


@kf.kcl.cell(set_name=False)
def taper_cell(layers: kf.kdb.LayerInfo, wg_enc: kf.LayerEnclosure) -> kf.KCell:
    if kf.kcl.layout_cell("taper") is None:
        c = kf.cells.taper.taper(
            width1=0.5,
            width2=1,
            length=10,
            layer=layers,
            enclosure=wg_enc,
        )
        c = c.dup()
        c.name = "taper"
    else:
        c = kf.kcl["taper"]
    return c


@pytest.fixture
def optical_port(layers: Layers) -> kf.Port:
    return kf.Port(
        name="o1",
        trans=kf.kdb.Trans.R0,
        layer=kf.kcl.find_layer(layers.WG),
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
        wg=kf.layer.LayerLevel(
            layer=Layers().WG,
            thickness=0.22,
            zmin=0,
            material="si",
            info=kf.Info(mesh_order=1),
        ),
        clad=kf.layer.LayerLevel(
            layer=Layers().WGCLAD, thickness=3, zmin=0.22, material="sio2"
        ),
    )
    return kf.KCLayout("Test_PDK", infos=Layers, layer_stack=layerstack)


@pytest.fixture
def fill_cell() -> kf.KCell:
    return fill_cell_fixture()


@kf.kcl.cell(basename="fill_cell")
def fill_cell_fixture() -> kf.KCell:
    fc = kf.KCell()
    fc.shapes(fc.kcl.find_layer(Layers().WGCLAD)).insert(kf.kdb.DBox(20, 40))
    fc.shapes(fc.kcl.find_layer(Layers().WGCLAD)).insert(kf.kdb.DBox(30, 15))
    return fc


@pytest.fixture(scope="module", autouse=True)
def unlink_merge_read_oas() -> Iterator[None]:
    yield
    Path("MERGE_READ.oas").unlink(missing_ok=True)

import platform
from collections.abc import Callable, Iterator
from functools import partial
from pathlib import Path
from threading import RLock
from typing import Any, Literal
from warnings import warn

import pytest
from pytest_regressions.file_regression import FileRegressionFixture

import kfactory as kf
import kfactory.cells

pytest_plugins = ["pytest_regressions"]


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

counter = 0
counter_lock = RLock()


@pytest.fixture(scope="session")
def lazy_datadir() -> Path:
    assert kf.config.project_dir is not None
    return kf.config.project_dir / "tests/test_data/generated"


@pytest.fixture(scope="session")
def original_datadir() -> Path:
    assert kf.config.project_dir is not None
    return kf.config.project_dir / "tests/test_data/generated"


@pytest.fixture(scope="module")
def layers() -> Layers:
    return Layers()


@pytest.fixture
def kcl() -> kf.KCLayout:
    with counter_lock:
        global counter  # noqa: PLW0603
        name = str(counter)
        counter += 1
        return kf.KCLayout(name=name, infos=Layers)


@pytest.fixture
def wg_enc(kcl: kf.KCLayout, layers: Layers) -> kf.LayerEnclosure:
    return kcl.get_enclosure(
        kf.LayerEnclosure(name="WGSTD", sections=[(layers.WGCLAD, 0, 2000)])
    )


@pytest.fixture
def straight_factory_dbu(
    layers: Layers, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout
) -> Callable[..., kf.KCell]:
    return partial(
        kf.factories.straight.straight_dbu_factory(kcl=kcl),
        layer=layers.WG,
        enclosure=wg_enc,
    )


@pytest.fixture
def straight_factory(
    straight_factory_dbu: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
) -> Callable[..., kf.KCell]:
    def straight(width: float, length: float, *args: Any, **kwargs: Any) -> kf.KCell:
        return straight_factory_dbu(
            *args, width=kcl.to_dbu(width), length=kcl.to_dbu(length), **kwargs
        )

    return straight


@pytest.fixture
def straight(
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
    straight_factory: Callable[..., kf.KCell],
    kcl: kf.KCLayout,
) -> kf.KCell:
    return straight_factory(width=0.5, length=1, layer=layers.WG, enclosure=wg_enc)


@pytest.fixture
def straight_blank(layers: Layers) -> kf.KCell:
    return kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)


@pytest.fixture
def bend90(layers: Layers, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout) -> kf.KCell:
    return kf.factories.circular.bend_circular_factory(kcl=kcl)(
        width=0.5, radius=10, layer=layers.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend90_small(
    layers: Layers, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout
) -> kf.KCell:
    return kf.factories.circular.bend_circular_factory(kcl=kcl)(
        width=0.5, radius=5, layer=layers.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180(layers: Layers, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout) -> kf.KCell:
    return kf.factories.circular.bend_circular_factory(kcl=kcl)(
        width=0.5, radius=10, layer=layers.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def bend90_euler(
    layers: Layers, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout
) -> kf.KCell:
    return kf.factories.euler.bend_euler_factory(kcl=kcl)(
        width=0.5, radius=10, layer=layers.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend90_euler_small(
    layers: Layers, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout
) -> kf.KCell:
    return kf.factories.euler.bend_euler_factory(kcl=kcl)(
        width=0.1, radius=10, layer=layers.WG, enclosure=wg_enc, angle=90
    )


@pytest.fixture
def bend180_euler(
    layers: Layers, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout
) -> kf.KCell:
    return kf.factories.euler.bend_euler_factory(kcl=kcl)(
        width=0.5, radius=10, layer=layers.WG, enclosure=wg_enc, angle=180
    )


@pytest.fixture
def taper(layers: Layers, wg_enc: kf.LayerEnclosure, kcl: kf.KCLayout) -> kf.KCell:
    taper_f = kf.factories.taper.taper_factory(kcl=kcl)

    return taper_f(
        width1=500, width2=1000, length=10_000, layer=layers.WG, enclosure=wg_enc
    )


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
def fill_cell(kcl: kf.KCLayout) -> kf.KCell:
    @kcl.cell
    def fill_cell() -> kf.KCell:
        fc = kcl.kcell()
        fc.shapes(fc.kcl.find_layer(Layers().WGCLAD)).insert(kf.kdb.DBox(20, 40))
        fc.shapes(fc.kcl.find_layer(Layers().WGCLAD)).insert(kf.kdb.DBox(30, 15))
        return fc

    return fill_cell()


@pytest.fixture(scope="module", autouse=True)
def unlink_merge_read_oas() -> Iterator[None]:
    yield
    Path("MERGE_READ.oas").unlink(missing_ok=True)


@pytest.fixture
def gds_regression(
    file_regression: FileRegressionFixture,
) -> Callable[[kf.ProtoTKCell[Any]], None]:
    saveopts = kf.save_layout_options()
    saveopts.format = "GDS2"

    raises: Literal["error", "warning"] = (
        "error" if platform.system() == "Linux" else "warning"
    )

    def _check(
        c: kf.ProtoTKCell[Any],
        tolerance: int = 0,
    ) -> None:
        c.kcl.layout.clear_meta_info()

        file_regression.check(
            c.write_bytes(saveopts, convert_external_cells=True),
            binary=True,
            extension=".gds",
            check_fn=partial(_layout_xor, tolerance=tolerance, raises=raises),
        )

    return _check


def _layout_xor(
    path_a: Path,
    path_b: Path,
    tolerance: int = 0,
    raises: Literal["error", "warning"] = "error",
) -> None:
    diff = kf.kdb.LayoutDiff()
    ly_a = kf.kdb.Layout()
    ly_a.read(str(path_a))
    ly_b = kf.kdb.Layout()
    ly_b.read(str(path_b))

    flags = kf.kdb.LayoutDiff.Verbose | kf.kdb.LayoutDiff.WithMetaInfo

    if not diff.compare(ly_a, ly_b, flags=flags, tolerance=tolerance):
        match raises:
            case "error":
                raise AttributeError(
                    f"Layouts {str(path_a)!r} and {str(path_b)!r} differ!"
                )
            case "warning":
                warn(
                    f"Layouts {str(path_a)!r} and {str(path_b)!r} differ!", stacklevel=3
                )

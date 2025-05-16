import pathlib
from functools import partial
from typing import Any

import pytest

import kfactory as kf
from kfactory.conf import logger
from tests.conftest import Layers


class GeometryDifferenceError(ValueError):
    """Exception for Geometric differences."""


@pytest.fixture
def cell_params(wg_enc: kf.LayerEnclosure, layers: Layers) -> dict[str, Any]:
    """Returns cell name."""
    return {
        "bend_circular": {
            "width": 1,
            "radius": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "bend_euler": {
            "width": 1,
            "radius": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "bend_s_bezier": {
            "width": 1,
            "height": 10,
            "length": 100,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "bend_s_euler": {
            "width": 1,
            "radius": 30,
            "offset": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "straight": {
            "width": 1000,
            "length": 100_000,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "taper": {
            "width1": 1000,
            "width2": 10_000,
            "length": 50_000,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
    }


@pytest.fixture
def virtual_cell_params(wg_enc: kf.LayerEnclosure, layers: Layers) -> dict[str, Any]:
    """Returns cell name."""
    return {
        "bend_euler": {
            "width": 1,
            "radius": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
            "angle": 30,
        },
        "virtual_bend_circular": {
            "width": 1,
            "radius": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
            "angle": 30,
        },
        "virtual_straight": {
            "width": 0.006,
            "length": 100.0052,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
    }


@pytest.mark.parametrize(
    "cell_name", sorted(set(kf.kcl.factories.keys()) - {"taper_cell"})
)
def test_cells(cell_name: str, cell_params: dict[str, Any]) -> None:
    """Ensure cells have the same geometry as their golden references."""
    gds_ref = pathlib.Path(__file__).parent / "test_data" / "ref"
    cell = kf.kcl.factories[cell_name](**cell_params.get(cell_name, {}))
    ref_file = gds_ref / f"{cell.name}.gds"
    run_cell = cell
    if not ref_file.exists():
        gds_ref.mkdir(parents=True, exist_ok=True)
        run_cell.write(str(ref_file))
        raise FileNotFoundError(f"GDS file not found. Saving it to {ref_file}")
    kcl_ref = kf.KCLayout("TEST", infos=Layers)
    kcl_ref.read(gds_ref / f"{cell.name}.gds", meta_format="v2", register_cells=True)
    ref_cell = kcl_ref[kcl_ref.top_cell().name]

    for layerinfo in kcl_ref.layout.layer_infos():
        layer = kcl_ref.layer(layerinfo)
        region_run = kf.kdb.Region(run_cell.begin_shapes_rec(layer))
        region_ref = kf.kdb.Region(ref_cell.begin_shapes_rec(layer))

        region_diff = region_run - region_ref

        if not region_diff.is_empty():
            layer_tuple = kcl_ref.layout.layer_infos()[layer]
            region_xor = region_ref ^ region_run
            c = kf.KCell(name=f"{cell.name}_diffs")
            c_run = kf.KCell(name=f"{cell.name}_new")
            c_ref = kf.KCell(name=f"{cell.name}_old")
            c_xor = kf.KCell(name=f"{cell.name}_xor")
            c_run.shapes(layer).insert(region_run)
            c_ref.shapes(layer).insert(region_ref)
            c_xor.shapes(layer).insert(region_xor)
            c << c_run
            c << c_ref
            c << c_xor

            kf.logger.critical(f"Differences found in {cell!r} on layer {layer_tuple}")
            val = input("Save current GDS as new reference (Y)? [Y/n]")
            if not val.upper().startswith("N"):
                logger.info(f"replacing file {str(ref_file)!r}")
                run_cell.write(ref_file.name)

            raise GeometryDifferenceError(
                f"Differences found in {cell!r} on layer {layer_tuple}"
            )


@pytest.mark.parametrize(
    "cell_name", sorted(set(kf.kcl.virtual_factories.keys()) - {"taper_cell"})
)
def test_virtual_cells(cell_name: str, virtual_cell_params: dict[str, Any]) -> None:
    """Ensure cells have the same geometry as their golden references."""
    gds_ref = pathlib.Path(__file__).parent / "test_data" / "ref"
    cell = kf.KCell()
    vkcell = kf.kcl.virtual_factories[cell_name](
        **virtual_cell_params.get(cell_name, {})
    )
    assert vkcell.name is not None
    cell.name = vkcell.name
    kf.VInstance(vkcell).insert_into_flat(cell, levels=1)
    ref_file = gds_ref / f"{cell.name}.gds"
    run_cell = cell
    if not ref_file.exists():
        gds_ref.mkdir(parents=True, exist_ok=True)
        run_cell.write(str(ref_file))
        raise FileNotFoundError(f"GDS file not found. Saving it to {ref_file}")
    kcl_ref = kf.KCLayout("TEST", infos=Layers)
    kcl_ref.read(gds_ref / f"{cell.name}.gds", meta_format="v2", register_cells=True)
    ref_cell = kcl_ref[kcl_ref.top_cell().name]

    for layerinfo in kcl_ref.layout.layer_infos():
        layer = kcl_ref.layer(layerinfo)
        region_run = kf.kdb.Region(run_cell.begin_shapes_rec(layer))
        region_ref = kf.kdb.Region(ref_cell.begin_shapes_rec(layer))

        region_diff = region_run - region_ref

        if not region_diff.is_empty():
            layer_tuple = kcl_ref.layout.layer_infos()[layer]
            region_xor = region_ref ^ region_run
            c = kf.KCell(name=f"{cell.name}_diffs")
            c_run = kf.KCell(name=f"{cell.name}_new")
            c_ref = kf.KCell(name=f"{cell.name}_old")
            c_xor = kf.KCell(name=f"{cell.name}_xor")
            c_run.shapes(layer).insert(region_run)
            c_ref.shapes(layer).insert(region_ref)
            c_xor.shapes(layer).insert(region_xor)
            c << c_run
            c << c_ref
            c << c_xor

            kf.logger.critical(f"Differences found in {cell!r} on layer {layer_tuple}")
            val = input("Save current GDS as new reference (Y)? [Y/n]")
            if not val.upper().startswith("N"):
                logger.info(f"replacing file {str(ref_file)!r}")
                run_cell.write(ref_file.name)

            raise GeometryDifferenceError(
                f"Differences found in {cell!r} on layer {layer_tuple}"
            )


def test_additional_info(
    kcl: kf.KCLayout,
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
) -> None:
    test_bend_euler = partial(
        kf.factories.euler.bend_euler_factory(
            kcl=kcl,
            additional_info={"creation_time": "2023-02-12Z23:00:00"},
            overwrite_existing=True,
        ),
        layer=layers.WG,
        radius=10,
    )

    bend = test_bend_euler(width=1)

    assert bend.locked is True
    assert bend.info.creation_time == "2023-02-12Z23:00:00"  # type: ignore[attr-defined, unused-ignore]

    bend.delete()

import pathlib
from functools import partial

import pytest
from conftest import Layers

import kfactory as kf
from kfactory.conf import logger


class GeometryDifferenceError(ValueError):
    """Exception for Geometric differences."""

    ...


wg_enc = kf.LayerEnclosure(name="WGSTD", sections=[(Layers().WGCLAD, 0, 2000)])


def straight(layers: Layers) -> kf.KCell:
    return kf.cells.straight.straight(
        width=0.5, length=1, layer=layers.WG, enclosure=wg_enc
    )


def bend90(layers: Layers) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=1, radius=10, layer=layers.WG, enclosure=wg_enc, angle=90
    )


def bend180(layers: Layers) -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=1, radius=10, layer=layers.WG, enclosure=wg_enc, angle=180
    )


def bend90_euler(layers: Layers) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=1, radius=10, layer=layers.WG, enclosure=wg_enc, angle=90
    )


def bend180_euler(layers: Layers) -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=1, radius=10, layer=layers.WG, enclosure=wg_enc, angle=180
    )


def taper(layers: Layers) -> kf.KCell:
    return kf.cells.taper.taper(
        width1=0.5,
        width2=1,
        length=10,
        layer=layers.WG,
        enclosure=wg_enc,
    )


cells = dict(
    bend90=bend90,
    bend180=bend180,
    bend180_euler=bend180_euler,
    bend90_euler=bend90_euler,
    taper=taper,
    straight=straight,
)

cell_names = list(sorted(set(cells.keys())))


@pytest.fixture(params=cell_names, scope="function")
def cell_name(request: pytest.FixtureRequest) -> str:
    """Returns cell name."""
    return request.param  # type: ignore[no-any-return]


def test_cells(cell_name: str, layers: Layers) -> None:
    """Ensure cells have the same geometry as their golden references."""
    gds_ref = pathlib.Path(__file__).parent / "test_data" / "ref"
    cell = cells[cell_name](layers)
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
    kcl: kf.KCLayout, layers: Layers, wg_enc: kf.LayerEnclosure
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

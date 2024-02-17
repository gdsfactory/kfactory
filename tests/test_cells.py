import pathlib
import pytest

import kfactory as kf

from kfactory.conf import logger


class GeometryDifference(ValueError):
    """Exception for Geometric differences."""

    pass


class LAYER(kf.LayerEnum):  # type: ignore[unused-ignore, misc]
    kcl = kf.constant(kf.kcl)
    WG = (1, 0)
    WGCLAD = (111, 0)


wg_enc = kf.LayerEnclosure(name="WGSTD", sections=[(LAYER.WGCLAD, 0, 2000)])


def straight() -> kf.KCell:
    return kf.cells.straight.straight(
        width=0.5, length=1, layer=LAYER.WG, enclosure=wg_enc
    )


def bend90() -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=90
    )


def bend180() -> kf.KCell:
    return kf.cells.circular.bend_circular(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=180
    )


def bend90_euler() -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=90
    )


def bend180_euler() -> kf.KCell:
    return kf.cells.euler.bend_euler(
        width=1, radius=10, layer=LAYER.WG, enclosure=wg_enc, angle=180
    )


def taper() -> kf.KCell:
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


cells = dict(
    bend90=bend90,
    bend180=bend180,
    bend180_euler=bend180_euler,
    bend90_euler=bend90_euler,
    taper=taper,
    straight=straight,
)

cell_names = set(cells.keys())


@pytest.fixture(params=cell_names, scope="function")
def cell_name(request: pytest.FixtureRequest) -> str:
    """Returns cell name."""
    return request.param  # type: ignore[no-any-return]


def test_cells(cell_name: str) -> None:
    """Ensure cells have the same geometry as their golden references."""
    gds_ref = pathlib.Path(__file__).parent / "test_data" / "ref"
    cell = cells[cell_name]()
    ref_file = gds_ref / f"{cell.name}.gds"
    run_cell = cell
    if not ref_file.exists():
        gds_ref.mkdir(parents=True, exist_ok=True)
        run_cell.write(str(ref_file))
        raise FileNotFoundError(f"GDS file not found. Saving it to {ref_file}")
    kcl_ref = kf.KCLayout("TEST")
    kcl_ref.read(gds_ref / f"{cell.name}.gds")
    ref_cell = kcl_ref[kcl_ref.top_cell().name]

    for layerinfo in kcl_ref.layer_infos():
        layer = kcl_ref.layer(layerinfo)
        region_run = kf.kdb.Region(run_cell.begin_shapes_rec(layer))
        region_ref = kf.kdb.Region(ref_cell.begin_shapes_rec(layer))

        region_diff = region_run - region_ref

        if not region_diff.is_empty():
            layer_tuple = kcl_ref.layer_infos()[layer]
            region_xor = region_ref ^ region_run
            c = kf.KCell(f"{cell.name}_diffs")
            c_run = kf.KCell(f"{cell.name}_new")
            c_ref = kf.KCell(f"{cell.name}_old")
            c_xor = kf.KCell(f"{cell.name}_xor")
            c_run.shapes(layer).insert(region_run)
            c_ref.shapes(layer).insert(region_ref)
            c_xor.shapes(layer).insert(region_xor)
            c << c_run
            c << c_ref
            c << c_xor
            c.show()

            kf.config.logger.critical(
                f"Differences found in {cell!r} on layer {layer_tuple}"
            )
            val = input("Save current GDS as new reference (Y)? [Y/n]")
            if not val.upper().startswith("N"):
                logger.info(f"replacing file {str(ref_file)!r}")
                run_cell.write(ref_file.name)

            raise GeometryDifference(
                f"Differences found in {cell!r} on layer {layer_tuple}"
            )


def test_inheritance(LAYER: kf.LayerEnum, wg_enc: kf.LayerEnclosure) -> None:
    class TestBendEuler(kf.cells.euler.BendEuler):  # type: ignore[unused-ignore, misc]
        def __init__(self) -> None:
            super().__init__(kf.kcl)

        @kf.cell  # type: ignore[misc, unused-ignore]
        def __call__(self, width: float) -> kf.KCell:  # type: ignore[override, unused-ignore]
            c = self._kcell(
                width=width,
                radius=30,
                layer=LAYER.WG,
                enclosure=wg_enc,
                angle=90,
                resolution=150,
            )
            c.info.creation_time = "2023-02-12Z23:00:00"

            return c

    bend = TestBendEuler()(width=1)

    assert bend._locked is True
    assert bend.info.creation_time == "2023-02-12Z23:00:00"  # type: ignore[attr-defined, unused-ignore]

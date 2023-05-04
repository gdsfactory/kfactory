from kfactory import kdb
import kfactory as kf

from inspect import signature
from kfactory.conf import path, logger


class GeometryDifference(ValueError):
    """Exception for Geometric differences."""

    pass


def test_cells(cells, LAYER) -> None:
    """Ensure cells have the same geometry as their golden references."""
    for cell in cells:
        ref_file = path.gds_ref / f"{cell.name}.gds"
        run_cell = cell
        if not ref_file.exists():
            path.gds_ref.mkdir(parents=True, exist_ok=True)
            run_cell.write(str(ref_file))
            raise FileNotFoundError(f"GDS file not found. Saving it to {ref_file}")
        kcl_ref = kf.KCLayout()
        kcl_ref.read(path.gds_ref / f"{cell.name}.gds")
        ref_cell = kcl_ref[kcl_ref.top_cell().name]

        for layer in kcl_ref.layer_infos():
            layer = kcl_ref.layer(layer)
            region_run = kdb.Region(run_cell.begin_shapes_rec(layer))
            region_ref = kdb.Region(ref_cell.begin_shapes_rec(layer))

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

                print(f"Differences found in {cell!r} on layer {layer_tuple}")
                val = input("Save current GDS as new reference (Y)? [Y/n]")
                if not val.upper().startswith("N"):
                    logger.info(f"replacing file {str(ref_file)!r}")
                    run_cell.write(ref_file.name)

                raise GeometryDifference(
                    f"Differences found in {cell!r} on layer {layer_tuple}"
                )

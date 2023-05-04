from kfactory import kdb
import kfactory as kf

from inspect import signature
from kfactory.conf import path, logger


class GeometryDifference(ValueError):
    """Exception for Geometric differences."""

    pass


def test_cells(cells):
    """Ensure cells have the same geometry as their golden references."""
    settings = {
        "width": 1.0,
        "height": 5.0,
        "radius": 30.0,
        "length": 10.0,
        "layer": 0,
        "width1": 1.0,
        "width2": 2.0,
        "offset": 5.0,
        "enclosure": kf.utils.Enclosure(name="WGSTD", sections=[(111, 0, 2000)]),
    }

    cells = kf.pdk.get_cells(cells)
    for cell in cells:
        if cell in ["waveguide_dbu", "taper_dbu"]:
            continue
        ref_file = path.gds_ref / f"{cell}.gds"

        settings_ = {
            k: v for k, v in settings.items() if k in signature(cells[cell]).parameters
        }
        run_cell = cells[cell](**settings_)
        if not ref_file.exists():
            path.gds_ref.mkdir(parents=True, exist_ok=True)
            run_cell.write(str(ref_file))
            continue
        kcl_ref = kf.KCLayout()
        kcl_ref.read(path.gds_ref / f"{cell}.gds")
        ref_cell = kcl_ref[0]

        for layer in kcl_ref.layer_infos():
            layer = kcl_ref.layer(layer)
            region_run = kdb.Region(run_cell.begin_shapes_rec(layer))
            region_ref = kdb.Region(ref_cell.begin_shapes_rec(layer))

            region_diff = region_run - region_ref

            if not region_diff.is_empty():
                layer_tuple = kcl_ref.layer_infos()[layer]
                region_xor = region_ref ^ region_run
                c = kf.KCell(f"{cell}_diffs")
                c_xor = kf.KCell("xor")
                c_xor.shapes(layer).insert(region_xor)
                c << run_cell
                c << ref_cell
                c << c_xor
                c.show()

                print(f"Differences found in {cell!r} on layer {layer_tuple}")
                val = input("Save current GDS as new reference (Y)? [Y/n]")
                if not val.upper().startswith("N"):
                    logger.info(f"replacing file {str(ref_file)!r}")
                    run_cell.write(ref_file)

                raise GeometryDifference(
                    f"Differences found in {cell!r} on layer {layer_tuple}"
                )

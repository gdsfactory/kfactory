from kfactory import kdb
import kfactory as kf

from inspect import signature
from kfactory.conf import path


def test_cells(cells):
    settings = {
        "width": 1.0,
        "height": 5.0,
        "radius": 10.0,
        "length": 10.0,
        "layer": 0,
        "width1": 1.0,
        "width2": 2.0,
        "offset": 5.0,
        "enclosure": kf.utils.Enclosure(name="WGSTD", sections=[(111, 0, 2000)]),
    }

    cells = kf.pdk.get_cells(cells)
    for cell in cells:
        if cell == "waveguide_dbu" or cell == "taper_dbu":
            continue
        gdspath = path.gds_ref / f"{cell}.gds"

        settings_ = {
            k: v for k, v in settings.items() if k in signature(cells[cell]).parameters
        }
        run_cell = cells[cell](**settings_)
        if not gdspath.exists():
            path.gds_ref.mkdir(parents=True, exist_ok=True)
            run_cell.write(str(gdspath))
            continue
        kcl_ref = kf.KCLayout()
        kcl_ref.read(path.gds_ref / f"{cell}.gds")
        ref_cell = kcl_ref[0]

        for layer in kcl_ref.layer_infos():
            layer = kcl_ref.layer(layer)
            region_run = kdb.Region(run_cell.begin_shapes_rec(layer))
            region_ref = kdb.Region(ref_cell.begin_shapes_rec(layer))

            assert not region_run - region_ref

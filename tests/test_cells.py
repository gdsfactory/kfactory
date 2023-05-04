from kfactory import kdb
import kfactory as kf

from inspect import signature
from pathlib import Path


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
        kcl_ref = kf.KCLayout()
        kcl_ref.read(Path(f"./tests/ref_cells/{cell}.gds"))
        ref_cell = kcl_ref[0]
        settings_ = {
            k: v for k, v in settings.items() if k in signature(cells[cell]).parameters
        }
        cell_ = cells[cell](**settings_)

        for layer in kcl_ref.layer_infos():
            layer = kcl_ref.layer(layer)
            region_cell = kdb.Region(cell_.begin_shapes_rec(layer))
            region_ref = kdb.Region(ref_cell.begin_shapes_rec(layer))

            assert not region_cell - region_ref

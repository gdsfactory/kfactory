import kfactory as kf
from conftest import Layers


def test_tiled_fill_space(fill_cell: kf.KCell, LAYER: Layers) -> None:
    c = kf.KCell()
    c.shapes(LAYER.WG).insert(kf.kdb.DPolygon.ellipse(kf.kdb.DBox(5000, 3000), 512))
    c.shapes(LAYER.WGCLAD).insert(
        kf.kdb.DPolygon(
            [kf.kdb.DPoint(0, 0), kf.kdb.DPoint(5000, 0), kf.kdb.DPoint(5000, 3000)]
        )
    )
    kf.utils.fill_tiled(
        c,
        fill_cell,
        [(LAYER.WG, 0)],
        exclude_layers=[
            (LAYER.WGEXCLUDE, 100),
            (LAYER.WGCLAD, 0),
            (LAYER.WGCLADEXCLUDE, 0),
        ],
        x_space=5,
        y_space=5,
    )


def test_tiled_fill_vector(fill_cell: kf.KCell, LAYER: Layers) -> None:
    c = kf.KCell()
    c.shapes(LAYER.WG).insert(kf.kdb.DPolygon.ellipse(kf.kdb.DBox(5000, 3000), 512))
    c.shapes(LAYER.WGCLAD).insert(
        kf.kdb.DPolygon(
            [kf.kdb.DPoint(0, 0), kf.kdb.DPoint(5000, 0), kf.kdb.DPoint(5000, 3000)]
        )
    )

    poly = kf.kdb.DPolygon(
        [
            kf.kdb.DPoint(-2000, 400),
            kf.kdb.DPoint(-1000, 400),
            kf.kdb.DPoint(-1000, -400),
            kf.kdb.DPoint(-2000, -400),
        ]
    )

    poly.insert_hole(kf.kdb.DBox(-1800, -200, -1200, 200))

    c.shapes(LAYER.WGEXCLUDE).insert(poly)
    kf.utils.fill_tiled(
        c,
        fill_cell,
        [(LAYER.WG, 0)],
        exclude_layers=[
            (LAYER.WGEXCLUDE, 100),
            (LAYER.WGCLAD, 0),
            (LAYER.WGCLADEXCLUDE, 0),
        ],
        row_step=kf.kdb.DVector(35, 5),
        col_step=kf.kdb.DVector(-5, 50),
        tile_border=(fill_cell.dbbox().width(), fill_cell.dbbox().height()),
        tile_size=(500, 500),
    )

import kfactory as kf
from tests.conftest import Layers


def test_tiled_fill_space(fill_cell: kf.KCell, layers: Layers) -> None:
    c = kf.KCell()
    c.shapes(layers.WG).insert(kf.kdb.DPolygon.ellipse(kf.kdb.DBox(5000, 3000), 512))
    c.shapes(layers.WGCLAD).insert(
        kf.kdb.DPolygon(
            [
                kf.kdb.DPoint(0, 0),
                kf.kdb.DPoint(5000, 0),
                kf.kdb.DPoint(5000, 3000),
            ]
        )
    )
    kf.utils.fill_tiled(
        c,
        fill_cell,
        [(layers.WG, 0)],
        exclude_layers=[
            (layers.WGEX, 100),
            (layers.WGCLAD, 0),
            (layers.WGCLADEX, 0),
        ],
        x_space=5,
        y_space=5,
    )


def test_tiled_fill_vector(fill_cell: kf.KCell, layers: Layers) -> None:
    c = kf.KCell()
    c.shapes(layers.WG).insert(kf.kdb.DPolygon.ellipse(kf.kdb.DBox(5000, 3000), 512))
    c.shapes(layers.WGCLAD).insert(
        kf.kdb.DPolygon(
            [
                kf.kdb.DPoint(0, 0),
                kf.kdb.DPoint(5000, 0),
                kf.kdb.DPoint(5000, 3000),
            ]
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

    c.shapes(layers.WGEX).insert(poly)
    kf.utils.fill_tiled(
        c,
        fill_cell,
        [(layers.WG, 0)],
        exclude_layers=[
            (layers.WGEX, 100),
            (layers.WGCLAD, 0),
            (layers.WGCLADEX, 0),
        ],
        row_step=kf.kdb.DVector(35, 5),
        col_step=kf.kdb.DVector(-5, 50),
        tile_border=(fill_cell.dbbox().width(), fill_cell.dbbox().height()),
        tile_size=(500, 500),
    )

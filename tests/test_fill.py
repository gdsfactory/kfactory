import kfactory as kf


def test_tiled_fill_space(fill_cell: kf.KCell) -> None:
    c = kf.KCell()
    c.shapes(kf.kcl.layer(1, 0)).insert(
        kf.kdb.DPolygon.ellipse(kf.kdb.DBox(5000, 3000), 512)
    )
    c.shapes(kf.kcl.layer(10, 0)).insert(
        kf.kdb.DPolygon(
            [kf.kdb.DPoint(0, 0), kf.kdb.DPoint(5000, 0), kf.kdb.DPoint(5000, 3000)]
        )
    )
    kf.utils.fill_tiled(
        c,
        fill_cell,
        [(kf.kcl.layer(1, 0), 0)],
        exclude_layers=[
            (kf.kcl.layer(10, 0), 100),
            (kf.kcl.layer(2, 0), 0),
            (kf.kcl.layer(3, 0), 0),
        ],
        x_space=5,
        y_space=5,
    )
    c.show()


def test_tiled_fill_vector(fill_cell: kf.KCell) -> None:
    c = kf.KCell()
    c.shapes(kf.kcl.layer(1, 0)).insert(
        kf.kdb.DPolygon.ellipse(kf.kdb.DBox(5000, 3000), 512)
    )
    c.shapes(kf.kcl.layer(10, 0)).insert(
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

    c.shapes(kf.kcl.layer(10, 0)).insert(poly)
    kf.utils.fill_tiled(
        c,
        fill_cell,
        [(kf.kcl.layer(1, 0), 0)],
        exclude_layers=[
            (kf.kcl.layer(10, 0), 100),
            (kf.kcl.layer(2, 0), 0),
            (kf.kcl.layer(3, 0), 0),
        ],
        row_step=kf.kdb.DVector(35, 5),
        col_step=kf.kdb.DVector(-5, 50),
        tile_border=(fill_cell.dbbox().width(), fill_cell.dbbox().height()),
        tile_size=(500, 500),
    )
    c.show()

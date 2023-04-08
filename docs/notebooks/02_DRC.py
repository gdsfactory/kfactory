# # Fixing DRC Errors
#
#

import kfactory as kf

triangle = kf.KCell("triangle")
triangle_poly = kf.kdb.DPolygon(
    [kf.kdb.DPoint(0, 10), kf.kdb.DPoint(30, 10), kf.kdb.DPoint(30, 0)]
)
triangle.shapes(triangle.layer(1, 0)).insert(triangle_poly)
triangle

box = kf.KCell("Box")
box_rect = kf.kdb.DBox(0, 0, 20, 5)
box.shapes(box.klib.layer(1, 0)).insert(box_rect)
box

c = kf.KCell("fix_accute_angle")
c << triangle
c << box
c

c.shapes(c.klib.layer(2, 0)).insert(
    kf.utils.violations.fix_spacing(
        c, 1000, c.klib.layer(1, 0), metrics=kf.kdb.Metrics.Euclidian
    )
)
c

c = kf.KCell("ToFill")
c.shapes(kf.klib.layer(1, 0)).insert(
    kf.kdb.DPolygon.ellipse(kf.kdb.DBox(5000, 3000), 512)
)
c.shapes(kf.klib.layer(10, 0)).insert(
    kf.kdb.DPolygon(
        [kf.kdb.DPoint(0, 0), kf.kdb.DPoint(5000, 0), kf.kdb.DPoint(5000, 3000)]
    )
)
c

fc = kf.KCell("fill")
fc.shapes(fc.klib.layer(2, 0)).insert(kf.kdb.DBox(20, 40))
fc.shapes(fc.klib.layer(3, 0)).insert(kf.kdb.DBox(30, 15))
fc

import kfactory.utils.geo.fill as fill

# fill.fill_tiled(c, fc, [(kf.klib.layer(1,0), 0)], exclude_layers = [(kf.klib.layer(10,0), 100), (kf.klib.layer(2,0), 0), (kf.klib.layer(3,0),0)], x_space=5, y_space=5)
fill.fill_tiled(
    c,
    fc,
    [(kf.klib.layer(1, 0), 0)],
    exclude_layers=[
        (kf.klib.layer(10, 0), 100),
        (kf.klib.layer(2, 0), 0),
        (kf.klib.layer(3, 0), 0),
    ],
    x_space=5,
    y_space=5,
)

c
